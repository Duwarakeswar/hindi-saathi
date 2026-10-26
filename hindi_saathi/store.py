"""Persistent learner state: vocabulary notebook, spaced repetition, quiz stats, lesson progress.

Everything lives in one small JSON file so the agent remembers the learner between sessions.
"""

from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# Leitner boxes: a word in box N is reviewed again after REVIEW_INTERVALS[N - 1] days.
REVIEW_INTERVALS = [0, 1, 3, 7, 14]
MAX_BOX = len(REVIEW_INTERVALS)

DEFAULT_STATE: dict[str, Any] = {
    "profile": {
        "name": "",
        "level": "beginner",
        "native_language": "English",
        "goals": "Understand and speak everyday Hindi confidently",
    },
    "vocabulary": {},
    "stats": {"quiz_total": 0, "quiz_correct": 0, "streak_days": 0, "last_active": ""},
    "lessons_completed": [],
}


def _today() -> date:
    return date.today()


class LearnerStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}
        state = json.loads(json.dumps(DEFAULT_STATE))
        for key, value in data.items():
            if isinstance(value, dict) and isinstance(state.get(key), dict):
                state[key].update(value)
            else:
                state[key] = value
        return state

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding="utf-8")

    def touch(self) -> None:
        """Update the daily practice streak."""
        stats = self.state["stats"]
        today = _today()
        last = stats.get("last_active")
        if last == today.isoformat():
            return
        if last == (today - timedelta(days=1)).isoformat():
            stats["streak_days"] += 1
        else:
            stats["streak_days"] = 1
        stats["last_active"] = today.isoformat()

    # ---- vocabulary -------------------------------------------------------

    def add_word(
        self,
        hindi: str,
        transliteration: str,
        english: str,
        example: str = "",
        part_of_speech: str = "",
    ) -> dict[str, Any]:
        hindi = hindi.strip()
        with self._lock:
            vocab = self.state["vocabulary"]
            is_new = hindi not in vocab
            entry = vocab.get(hindi) or {
                "box": 1,
                "next_review": _today().isoformat(),
                "times_seen": 0,
                "times_correct": 0,
                "added": _today().isoformat(),
            }
            entry.update(
                {
                    "hindi": hindi,
                    "transliteration": transliteration.strip(),
                    "english": english.strip(),
                    "example": example.strip() or entry.get("example", ""),
                    "part_of_speech": part_of_speech.strip() or entry.get("part_of_speech", ""),
                }
            )
            vocab[hindi] = entry
            self.touch()
            self.save()
        return {"saved": hindi, "new_word": is_new, "total_words": len(vocab)}

    def list_words(self, only_due: bool = False, limit: int = 20) -> list[dict[str, Any]]:
        today = _today().isoformat()
        words = list(self.state["vocabulary"].values())
        if only_due:
            words = [w for w in words if w["next_review"] <= today]
        # Weakest / most overdue first.
        words.sort(key=lambda w: (w["box"], w["next_review"]))
        return words[: max(1, limit)]

    def record_answer(self, hindi: str, correct: bool) -> dict[str, Any]:
        hindi = hindi.strip()
        with self._lock:
            stats = self.state["stats"]
            stats["quiz_total"] += 1
            stats["quiz_correct"] += int(correct)
            entry = self.state["vocabulary"].get(hindi)
            result: dict[str, Any] = {"recorded": True, "correct": correct}
            if entry:
                entry["times_seen"] += 1
                entry["times_correct"] += int(correct)
                entry["box"] = min(entry["box"] + 1, MAX_BOX) if correct else 1
                next_review = _today() + timedelta(days=REVIEW_INTERVALS[entry["box"] - 1])
                entry["next_review"] = next_review.isoformat()
                result.update({"word": hindi, "box": entry["box"], "next_review": entry["next_review"]})
            else:
                result["note"] = "Word is not in the notebook; only overall quiz stats were updated."
            self.touch()
            self.save()
        return result

    # ---- profile & lessons -------------------------------------------------

    def update_profile(self, **fields: str) -> dict[str, Any]:
        with self._lock:
            for key, value in fields.items():
                if value:
                    self.state["profile"][key] = value.strip()
            self.save()
        return self.state["profile"]

    def complete_lesson(self, lesson_id: str) -> list[str]:
        with self._lock:
            done = self.state["lessons_completed"]
            if lesson_id not in done:
                done.append(lesson_id)
            self.touch()
            self.save()
        return done

    def summary(self) -> dict[str, Any]:
        stats = self.state["stats"]
        today = _today().isoformat()
        vocab = self.state["vocabulary"].values()
        total = stats["quiz_total"]
        weak = sorted(
            (w for w in vocab if w["times_seen"] and w["times_correct"] / w["times_seen"] < 0.6),
            key=lambda w: w["times_correct"] / w["times_seen"],
        )
        return {
            "profile": self.state["profile"],
            "words_saved": len(self.state["vocabulary"]),
            "words_due_for_review": sum(1 for w in vocab if w["next_review"] <= today),
            "words_mastered": sum(1 for w in vocab if w["box"] == MAX_BOX),
            "quiz_answers": total,
            "quiz_accuracy_percent": round(100 * stats["quiz_correct"] / total) if total else None,
            "streak_days": stats["streak_days"],
            "lessons_completed": self.state["lessons_completed"],
            "weak_words": [w["hindi"] for w in weak[:5]],
        }
