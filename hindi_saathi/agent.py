"""The Hindi Saathi tutor agent: Sarvam-105B + a function-calling loop over the learner tools."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .prompts import SYSTEM_PROMPT
from .sarvam import SarvamClient, SarvamError
from .store import LearnerStore
from .tools import TOOL_SCHEMAS, make_tool_runner

DEFAULT_DATA_PATH = Path(os.getenv("HINDI_SAATHI_DATA", Path(__file__).resolve().parent.parent / "data" / "learner.json"))
MAX_TOOL_ROUNDS = 6
THINK_TAGS = re.compile(r"<think>.*?</think>", re.DOTALL)
SAVE_CLAIM = re.compile(r"\b(saved|added)\b.{0,60}\b(notebook|words?|vocabulary|for you)\b", re.IGNORECASE | re.DOTALL)
EXTRACT_PROMPT = (
    "The message below is from a Hindi tutor who says they saved some vocabulary words for the learner. "
    'Return JSON only: {"words": [{"hindi": "<Devanagari>", "transliteration": "<romanised>", "english": "<meaning>"}]} '
    "listing exactly the words the tutor says were saved (at most 5). If none, return {\"words\": []}."
)


@dataclass
class TurnResult:
    text: str
    tools_used: list[dict] = field(default_factory=list)


class HindiTutorAgent:
    def __init__(self, sarvam: SarvamClient | None = None, data_path: str | Path = DEFAULT_DATA_PATH):
        self.sarvam = sarvam or SarvamClient()
        self.store = LearnerStore(data_path)
        self.run_tool = make_tool_runner(self.store, self.sarvam)
        self.messages: list[dict] = []

    def reset(self) -> None:
        self.messages = []

    def chat(self, user_text: str) -> TurnResult:
        checkpoint = len(self.messages)
        self.messages.append({"role": "user", "content": user_text})
        tools_used: list[dict] = []
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                choice = self.sarvam.chat([{"role": "system", "content": SYSTEM_PROMPT}, *self.messages], tools=TOOL_SCHEMAS)
                message = choice["message"]
                tool_calls = message.get("tool_calls") or []
                assistant = {"role": "assistant", "content": message.get("content") or ""}
                if tool_calls:
                    assistant["tool_calls"] = tool_calls
                self.messages.append(assistant)

                if not tool_calls:
                    text = THINK_TAGS.sub("", assistant["content"]).strip()
                    if SAVE_CLAIM.search(text) and not any(t["name"] == "save_vocabulary" for t in tools_used):
                        tools_used += self._save_claimed_words(text)
                    return TurnResult(text or "(no reply)", tools_used)

                for call in tool_calls:
                    name = call["function"]["name"]
                    try:
                        args = json.loads(call["function"].get("arguments") or "{}")
                        if not isinstance(args, dict):
                            raise ValueError("arguments must be a JSON object")
                        result = self.run_tool(name, args)
                    except ValueError as err:
                        args, result = {}, json.dumps({"error": f"Invalid JSON arguments: {err}"})
                    tools_used.append({"name": name, "input": args})
                    self.messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
        except SarvamError as err:
            del self.messages[checkpoint:]
            return TurnResult(f"⚠️ {err}")

        return TurnResult("I got a bit stuck there - could you rephrase that?", tools_used)

    def _save_claimed_words(self, reply: str) -> list[dict]:
        """The model sometimes says it saved words without calling the tool; extract and save them for real."""
        try:
            choice = self.sarvam.chat(
                [
                    {"role": "system", "content": EXTRACT_PROMPT},
                    {"role": "user", "content": reply},
                ],
                json_mode=True,
                max_tokens=1500,
            )
            raw = re.sub(r"^```(?:json)?|```$", "", THINK_TAGS.sub("", choice["message"].get("content") or "").strip())
            words = json.loads(raw).get("words", [])
            words = [w for w in words if isinstance(w, dict) and w.get("hindi") and w.get("english")]
        except (SarvamError, ValueError, AttributeError):
            return []
        if not words:
            return []
        for w in words:
            w.setdefault("transliteration", "")
        self.run_tool("save_vocabulary", {"words": words[:5]})
        return [{"name": "save_vocabulary", "input": {"words": words[:5]}}]
