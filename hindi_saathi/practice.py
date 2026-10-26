"""Pronunciation scoring: compare what the learner said (Sarvam speech-to-text) with the target Hindi."""

from __future__ import annotations

import re
from difflib import SequenceMatcher

PUNCT = re.compile(r"[।॥,.!?;:\"'“”‘’()\-]")
# Spellings that sound the same, so speech-to-text may pick either one.
EQUIVALENTS = str.maketrans({"़": None, "ँ": "ं", "ॅ": "े", "ॉ": "ो"})


def normalize(text: str) -> list[str]:
    return PUNCT.sub(" ", text).translate(EQUIVALENTS).lower().split()


def score_pronunciation(target: str, heard: str) -> dict:
    """Return a 0-100 score plus per-word feedback for the target sentence."""
    target_words, heard_words = normalize(target), normalize(heard)
    if not target_words:
        return {"score": 0, "words": []}
    char_score = SequenceMatcher(None, " ".join(target_words), " ".join(heard_words)).ratio()
    matcher = SequenceMatcher(None, target_words, heard_words)
    matched = set()
    for block in matcher.get_matching_blocks():
        matched.update(range(block.a, block.a + block.size))
    words = [{"word": w, "ok": i in matched} for i, w in enumerate(target_words)]
    word_score = len(matched) / len(target_words)
    return {"score": round(100 * (0.5 * char_score + 0.5 * word_score)), "words": words}


def feedback(score: int) -> str:
    if score >= 90:
        return "शानदार! Excellent - that sounded just right. 🎉"
    if score >= 70:
        return "बहुत अच्छे! Very good - just polish the red words. 👍"
    if score >= 40:
        return "अच्छी कोशिश! Good try - listen once more and repeat slowly. 🙂"
    return "कोई बात नहीं! No worries - play the audio at slow speed and try again. 💪"
