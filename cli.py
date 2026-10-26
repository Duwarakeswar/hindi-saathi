"""Terminal chat with Hindi Saathi.  Run:  python cli.py"""

import json
import sys

from dotenv import load_dotenv

load_dotenv()

from hindi_saathi.agent import HindiTutorAgent  # noqa: E402
from hindi_saathi.sarvam import SarvamError  # noqa: E402

HELP = "Commands: /lesson  /quiz  /review  /stats  /reset  /quit"
SHORTCUTS = {
    "/lesson": "Teach me the next lesson in my curriculum.",
    "/quiz": "Give me a short quiz (5 questions, one at a time) at my level.",
    "/review": "Let's review my vocabulary words that are due.",
}


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    try:
        agent = HindiTutorAgent()
    except SarvamError as err:
        sys.exit(str(err))
    print("🪔 Hindi Saathi - नमस्ते! Translate anything or ask me to teach you.")
    print(HELP)
    while True:
        try:
            text = input("\nyou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nफिर मिलेंगे! (See you again!)")
            return
        if not text:
            continue
        if text == "/quit":
            print("फिर मिलेंगे! (See you again!)")
            return
        if text == "/reset":
            agent.reset()
            print("Started a new conversation.")
            continue
        if text == "/stats":
            print(json.dumps(agent.store.summary(), ensure_ascii=False, indent=2))
            continue
        result = agent.chat(SHORTCUTS.get(text, text))
        for tool in result.tools_used:
            print(f"  [tool] {tool['name']} {json.dumps(tool['input'], ensure_ascii=False)}")
        print(f"\nsaathi> {result.text}")


if __name__ == "__main__":
    main()
