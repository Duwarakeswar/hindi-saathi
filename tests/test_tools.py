"""Offline tests for the learner store, agent tools, agent loop and pronunciation scoring (no API key needed).

Run:  python -m unittest -v
"""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from hindi_saathi.agent import HindiTutorAgent
from hindi_saathi.practice import score_pronunciation
from hindi_saathi.store import LearnerStore
from hindi_saathi.tools import TOOL_SCHEMAS, make_tool_runner


class FakeSarvam:
    """Stands in for SarvamClient: first asks for a tool, then answers."""

    def __init__(self):
        self.calls = []

    def chat(self, messages, tools=None, max_tokens=4096):
        self.calls.append(messages)
        if messages[-1]["role"] == "user":
            call = {"id": "call_1", "type": "function", "function": {
                "name": "save_vocabulary",
                "arguments": json.dumps({"words": [{"hindi": "पानी", "transliteration": "paanee", "english": "water"}]}),
            }}
            return {"message": {"role": "assistant", "content": "", "tool_calls": [call]}, "finish_reason": "tool_calls"}
        return {"message": {"role": "assistant", "content": "<think>x</think>पानी (paanee) = water"}, "finish_reason": "stop"}

    def translate(self, text, source="auto", target="hi-IN", mode="formal"):
        return {"translated_text": "नमस्ते", "source_language_code": "en-IN"}

    def romanize(self, hindi):
        return "namaste"


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "learner.json"
        self.store = LearnerStore(self.path)
        self.run = make_tool_runner(self.store, FakeSarvam())

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, tool_name, **kwargs):
        return json.loads(self.run(tool_name, kwargs))

    def test_tool_schemas(self):
        names = [t["function"]["name"] for t in TOOL_SCHEMAS]
        self.assertEqual(len(names), 8)
        for name in names:  # every schema has a handler
            self.assertNotIn("Unknown tool", self.run(name, {}))

    def test_translate_tool(self):
        out = self.call("translate_text", text="hello", target_language="hi-IN")
        self.assertEqual(out["translated_text"], "नमस्ते")
        self.assertEqual(out["hindi_romanised"], "namaste")

    def test_save_and_persist_vocabulary(self):
        out = self.call("save_vocabulary", words=[
            {"hindi": "पानी", "transliteration": "paanee", "english": "water"},
            {"hindi": "घर", "transliteration": "ghar", "english": "house"},
        ])
        self.assertEqual(out, {"saved": ["पानी", "घर"], "total_words": 2})
        self.assertEqual(LearnerStore(self.path).state["vocabulary"]["पानी"]["english"], "water")

    def test_spaced_repetition(self):
        self.call("save_vocabulary", words=[{"hindi": "घर", "transliteration": "ghar", "english": "house"}])
        out = self.call("record_quiz_result", hindi="घर", correct=True)
        self.assertEqual(out["box"], 2)
        self.assertEqual(out["next_review"], (date.today() + timedelta(days=1)).isoformat())
        self.assertEqual(self.call("record_quiz_result", hindi="घर", correct=False)["box"], 1)
        summary = self.call("get_learner_profile")
        self.assertEqual((summary["quiz_answers"], summary["quiz_accuracy_percent"]), (2, 50))

    def test_due_words(self):
        self.call("save_vocabulary", words=[{"hindi": "किताब", "transliteration": "kitaab", "english": "book"}])
        self.assertEqual(self.call("get_vocabulary", only_due_for_review=True)["count"], 1)
        self.call("record_quiz_result", hindi="किताब", correct=True)
        self.assertEqual(self.call("get_vocabulary", only_due_for_review=True)["count"], 0)

    def test_curriculum_progress(self):
        self.assertEqual(self.call("get_curriculum")["next_lesson"], "01-vowels")
        self.call("mark_lesson_complete", lesson_id="01-vowels")
        self.assertEqual(self.call("get_curriculum")["next_lesson"], "02-consonants")
        self.assertIn("error", self.call("mark_lesson_complete", lesson_id="nope"))

    def test_bad_arguments_return_error(self):
        self.assertIn("error", self.call("save_vocabulary", words=[{"hindi": "x"}]))


class AgentLoopTests(unittest.TestCase):
    def test_tool_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeSarvam()
            agent = HindiTutorAgent(fake, Path(tmp) / "l.json")
            result = agent.chat("translate water")
            self.assertEqual(result.text, "पानी (paanee) = water")
            self.assertEqual([t["name"] for t in result.tools_used], ["save_vocabulary"])
            self.assertEqual([m["role"] for m in agent.messages], ["user", "assistant", "tool", "assistant"])
            self.assertEqual(fake.calls[1][-1]["tool_call_id"], "call_1")
            self.assertEqual(agent.store.summary()["words_saved"], 1)


class PronunciationTests(unittest.TestCase):
    def test_perfect_and_partial(self):
        self.assertEqual(score_pronunciation("रेलवे स्टेशन कहाँ है?", "रेलवे स्टेशन कहां है")["score"], 100)
        partial = score_pronunciation("रेलवे स्टेशन कहाँ है?", "स्टेशन है")
        self.assertLess(partial["score"], 80)
        self.assertEqual([w["ok"] for w in partial["words"]], [False, True, False, True])


if __name__ == "__main__":
    unittest.main()
