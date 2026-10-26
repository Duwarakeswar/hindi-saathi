"""Tools the tutor agent can call (OpenAI-style function calling on Sarvam chat completions)."""

from __future__ import annotations

import json
from typing import Any, Callable

from .curriculum import LESSON_IDS, LESSONS
from .sarvam import SarvamClient, SarvamError
from .store import LearnerStore


def _fn(name: str, description: str, properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required or []},
        },
    }


TOOL_SCHEMAS = [
    _fn(
        "translate_text",
        "Translate text between English and Hindi with Sarvam's Mayura translation model. Returns the "
        "translation plus a romanised pronunciation of the Hindi. Use it whenever the learner asks for a translation.",
        {
            "text": {"type": "string", "description": "Text to translate (English, Hindi or Hinglish)."},
            "target_language": {"type": "string", "enum": ["hi-IN", "en-IN"], "description": "hi-IN for Hindi, en-IN for English."},
            "style": {"type": "string", "enum": ["formal", "modern-colloquial"], "description": "formal = standard Hindi (best for learners, default); modern-colloquial = casual Hinglish."},
        },
        ["text", "target_language"],
    ),
    _fn(
        "save_vocabulary",
        "Save one or more Hindi words or short phrases to the learner's vocabulary notebook for spaced-repetition "
        "review, in a single call. Use for genuinely useful new words (about 3 per turn) or when the learner asks.",
        {
            "words": {
                "type": "array",
                "description": "The words to save.",
                "items": {
                    "type": "object",
                    "properties": {
                        "hindi": {"type": "string", "description": "Word or phrase in Devanagari, e.g. पानी."},
                        "transliteration": {"type": "string", "description": "Romanised pronunciation, e.g. paanee."},
                        "english": {"type": "string", "description": "English meaning."},
                        "example_sentence": {"type": "string", "description": "Optional short Hindi example with English gloss."},
                        "part_of_speech": {"type": "string", "description": "Optional, e.g. noun (m), noun (f), verb, phrase."},
                    },
                    "required": ["hindi", "transliteration", "english"],
                },
            }
        },
        ["words"],
    ),
    _fn(
        "get_vocabulary",
        "List words from the learner's notebook, weakest and most overdue first. Use before a review or vocabulary quiz.",
        {
            "only_due_for_review": {"type": "boolean", "description": "Only return words due for review today."},
            "limit": {"type": "integer", "description": "Maximum number of words to return."},
        },
    ),
    _fn(
        "record_quiz_result",
        "Record whether the learner answered a quiz question correctly. Call once after grading each answer; "
        "it reschedules that word's spaced-repetition review and updates accuracy.",
        {
            "hindi": {"type": "string", "description": "The Devanagari word or phrase that was tested."},
            "correct": {"type": "boolean", "description": "True if the answer was right."},
        },
        ["hindi", "correct"],
    ),
    _fn(
        "get_learner_profile",
        "Get the learner's profile and progress: level, goals, words saved and due, quiz accuracy, streak, "
        "completed lessons and weak words. Call at the start of a conversation to personalise teaching.",
        {},
    ),
    _fn(
        "update_learner_profile",
        "Update the learner's profile when they share their name, level, native language or goals.",
        {
            "name": {"type": "string"},
            "level": {"type": "string", "enum": ["beginner", "elementary", "intermediate", "advanced"]},
            "native_language": {"type": "string"},
            "goals": {"type": "string"},
        },
    ),
    _fn(
        "get_curriculum",
        "Get the 12-lesson plan with each lesson's goals, completion status and the next lesson to teach.",
        {},
    ),
    _fn(
        "mark_lesson_complete",
        "Mark a curriculum lesson complete after the learner has worked through it and answered its check questions.",
        {"lesson_id": {"type": "string", "description": "Lesson id from get_curriculum, e.g. 03-greetings."}},
        ["lesson_id"],
    ),
]


def make_tool_runner(store: LearnerStore, sarvam: SarvamClient | None) -> Callable[[str, dict], str]:
    """Return run(name, args) -> JSON string, bound to one learner's store."""

    def translate_text(text: str, target_language: str = "hi-IN", style: str = "formal") -> Any:
        if sarvam is None:
            return {"error": "Translation service unavailable."}
        out = sarvam.translate(text, target=target_language, mode=style)
        hindi = out["translated_text"] if target_language == "hi-IN" else text
        return {**out, "hindi_romanised": sarvam.romanize(hindi)}

    def get_curriculum() -> Any:
        done = set(store.state["lessons_completed"])
        lessons = [{**lesson, "completed": lesson["id"] in done} for lesson in LESSONS]
        return {"lessons": lessons, "next_lesson": next((l["id"] for l in lessons if not l["completed"]), None)}

    def mark_lesson_complete(lesson_id: str) -> Any:
        if lesson_id not in LESSON_IDS:
            return {"error": f"Unknown lesson id {lesson_id!r}", "valid_ids": sorted(LESSON_IDS)}
        return {"lessons_completed": store.complete_lesson(lesson_id)}

    def save_vocabulary(words: list[dict]) -> Any:
        saved = [
            store.add_word(
                w["hindi"], w["transliteration"], w["english"], w.get("example_sentence", ""), w.get("part_of_speech", "")
            )["saved"]
            for w in words
        ]
        return {"saved": saved, "total_words": len(store.state["vocabulary"])}

    handlers: dict[str, Callable[..., Any]] = {
        "translate_text": translate_text,
        "save_vocabulary": save_vocabulary,
        "get_vocabulary": lambda only_due_for_review=False, limit=20: (
            lambda words: {"count": len(words), "words": words}
        )(store.list_words(only_due=bool(only_due_for_review), limit=int(limit))),
        "record_quiz_result": lambda hindi, correct: store.record_answer(hindi, bool(correct)),
        "get_learner_profile": store.summary,
        "update_learner_profile": lambda name="", level="", native_language="", goals="": store.update_profile(
            name=name, level=level, native_language=native_language, goals=goals
        ),
        "get_curriculum": get_curriculum,
        "mark_lesson_complete": mark_lesson_complete,
    }

    def run(name: str, args: dict) -> str:
        handler = handlers.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool {name}"})
        try:
            return json.dumps(handler(**args), ensure_ascii=False)
        except (TypeError, KeyError) as err:
            return json.dumps({"error": f"Bad arguments for {name}: {err}"})
        except SarvamError as err:
            return json.dumps({"error": str(err)})

    return run
