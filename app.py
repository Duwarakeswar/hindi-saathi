"""Streamlit web app for Hindi Saathi.  Run:  streamlit run app.py"""

import re

import streamlit as st
from dotenv import load_dotenv

from hindi_saathi.agent import HindiTutorAgent
from hindi_saathi.curriculum import LESSONS
from hindi_saathi.practice import feedback, score_pronunciation
from hindi_saathi.sarvam import SarvamClient, SarvamError, get_api_key

load_dotenv()

st.set_page_config(page_title="Hindi Saathi", page_icon="🪔", layout="wide")

DEVANAGARI = re.compile(r"[ऀ-ॿ]+(?:[\s,।॥?!]+[ऀ-ॿ]+)*")

QUICK_ACTIONS = {
    "📚 Lesson": "Teach me the next lesson in my curriculum.",
    "🧠 Quiz": "Give me a short quiz (5 questions, one at a time) at my level.",
    "🔄 Review": "Let's review my vocabulary words that are due.",
    "💬 Chat": "Let's have a simple conversation in Hindi. You start, and correct my mistakes.",
    "📈 Progress": "How am I doing? Summarise my progress and suggest what to practise next.",
}

TOOL_LABELS = {
    "translate_text": lambda i: "🔁 Translated with Sarvam Mayura",
    "save_vocabulary": lambda i: "📒 Saved to your notebook: "
    + ", ".join(f"**{w.get('hindi', '')}** ({w.get('english', '')})" for w in i.get("words", [])),
    "record_quiz_result": lambda i: f"{'✅' if i.get('correct') else '❌'} Recorded answer for **{i.get('hindi', '')}**",
    "mark_lesson_complete": lambda i: f"🎓 Lesson **{i.get('lesson_id', '')}** completed",
    "update_learner_profile": lambda i: "👤 Updated your learner profile",
}


def show_error(err: Exception) -> None:
    msg = str(err)
    if "402" in msg:
        msg += " Add credits at dashboard.sarvam.ai."
    st.error(msg)


@st.cache_data(show_spinner=False, max_entries=200)
def tts(api_key: str, text: str, pace: float) -> bytes:
    return SarvamClient(api_key).speak(text, pace=pace)


# ---- setup -------------------------------------------------------------------

api_key = get_api_key()
with st.sidebar:
    st.title("🪔 Hindi Saathi")
    st.caption("Your AI Hindi tutor & translator, powered by Sarvam AI")
    if not api_key:
        api_key = st.text_input("Sarvam API key", type="password", help="Or set SARVAM_API_KEY in .env / Streamlit secrets")

if not api_key:
    st.header("नमस्ते! 🙏")
    st.info("Add your Sarvam API key in the sidebar (or a `.env` file) to start.")
    st.stop()

if st.session_state.get("agent_key") != api_key:
    sarvam = SarvamClient(api_key)
    st.session_state.sarvam = sarvam
    st.session_state.agent = HindiTutorAgent(sarvam)
    st.session_state.agent_key = api_key
    st.session_state.chat = []
sarvam: SarvamClient = st.session_state.sarvam
agent: HindiTutorAgent = st.session_state.agent
store = agent.store

with st.sidebar:
    s = store.summary()
    st.subheader("Your progress")
    c1, c2 = st.columns(2)
    c1.metric("Words saved", s["words_saved"])
    c2.metric("Due for review", s["words_due_for_review"])
    c1.metric("Quiz accuracy", f"{s['quiz_accuracy_percent']}%" if s["quiz_accuracy_percent"] is not None else "–")
    c2.metric("Streak 🔥", f"{s['streak_days']} d")
    st.progress(len(s["lessons_completed"]) / len(LESSONS), text=f"Lessons: {len(s['lessons_completed'])}/{len(LESSONS)}")
    slow = st.toggle("🐢 Slow audio for practice", value=True)
    st.divider()
    st.caption(
        "**Sarvam APIs used:** Mayura (translate) · Transliterate · Bulbul (text-to-speech) · "
        "Saaras (speech-to-text) · Sarvam-105B (tutor agent with tool calling)"
    )

pace = 0.75 if slow else 1.0

st.header("नमस्ते! 🙏 Translate, listen, speak and learn Hindi")
tab_translate, tab_tutor, tab_notebook = st.tabs(["🔁 Translate & Speak", "💬 Tutor chat", "📒 Notebook"])


# ---- tab 1: the core flow -------------------------------------------------------

with tab_translate:
    left, right = st.columns([3, 2])
    with left:
        text = st.text_area(
            "Type anything in English, Hindi or Hinglish",
            placeholder="e.g. Where is the railway station?  /  मुझे भूख लगी है",
            height=90,
        )
    with right:
        style = st.radio("Style", ["Standard Hindi", "Hinglish (casual)"], horizontal=True)
        go = st.button("Translate ➜", type="primary", use_container_width=True)

    if go and text.strip():
        with st.spinner("Translating with Sarvam…"):
            try:
                mode = "formal" if style == "Standard Hindi" else "modern-colloquial"
                first = sarvam.translate(text.strip(), source="auto", target="hi-IN", mode=mode)
                if first.get("source_language_code") == "hi-IN":
                    hindi = text.strip()
                    english = sarvam.translate(hindi, source="hi-IN", target="en-IN", mode="formal")["translated_text"]
                else:
                    hindi, english = first["translated_text"], text.strip()
                st.session_state.result = {"hindi": hindi, "english": english, "roman": sarvam.romanize(hindi)}
                st.session_state.pop("explanation", None)
            except SarvamError as err:
                show_error(err)

    result = st.session_state.get("result")
    if result:
        st.markdown(f"### {result['hindi']}")
        st.markdown(f"🗣️ *{result['roman']}*  \n📝 {result['english']}")

        a, b, c = st.columns(3)
        with a:
            try:
                st.audio(tts(api_key, result["hindi"], pace), format="audio/wav")
            except SarvamError as err:
                show_error(err)
        with b:
            if st.button("📒 Save to notebook", use_container_width=True):
                store.add_word(result["hindi"], result["roman"], result["english"], part_of_speech="phrase")
                st.toast(f"Saved {result['hindi']} 📒")
        with c:
            if st.button("🧑‍🏫 Explain the grammar", use_container_width=True):
                with st.spinner("Your tutor is preparing an explanation…"):
                    st.session_state.explanation = agent.chat(
                        f"Briefly explain this Hindi sentence word by word for a beginner, with any grammar or "
                        f"formality notes: {result['hindi']} (meaning: {result['english']})"
                    ).text

        if st.session_state.get("explanation"):
            with st.container(border=True):
                st.markdown(st.session_state.explanation)

        st.subheader("🎤 Your turn - say it in Hindi")
        recording = st.audio_input("Record yourself reading the Hindi sentence", key=f"rec-{result['hindi']}")
        if recording:
            with st.spinner("Listening with Sarvam Saaras…"):
                try:
                    heard = sarvam.transcribe(recording.getvalue(), filename="speech.wav")["transcript"]
                except SarvamError as err:
                    show_error(err)
                    heard = None
            if heard is not None:
                scored = score_pronunciation(result["hindi"], heard)
                st.metric("Pronunciation score", f"{scored['score']}/100")
                st.markdown(f"**I heard:** {heard or '(nothing)'}")
                st.markdown(
                    " ".join(
                        f":{'green' if w['ok'] else 'red'}[{w['word']}]" for w in scored["words"]
                    )
                )
                st.info(feedback(scored["score"]))
                store.state["stats"]["quiz_total"] += 1
                store.state["stats"]["quiz_correct"] += int(scored["score"] >= 70)
                store.touch()
                store.save()


# ---- tab 2: tutor agent ---------------------------------------------------------

with tab_tutor:
    cols = st.columns(len(QUICK_ACTIONS) + 1)
    clicked = None
    for col, (label, prompt) in zip(cols, QUICK_ACTIONS.items()):
        if col.button(label, use_container_width=True):
            clicked = prompt
    if cols[-1].button("🧹 New", use_container_width=True):
        agent.reset()
        st.session_state.chat = []
        st.rerun()

    if not st.session_state.chat:
        st.caption(
            "Ask anything: **Explain का / की / के** · **How do I say “I'm learning Hindi” politely?** · "
            "**मेरा नाम Asha है, मुझे बातचीत सिखाओ**"
        )

    for i, turn in enumerate(st.session_state.chat):
        with st.chat_message(turn["role"], avatar="🧑‍🎓" if turn["role"] == "user" else "🪔"):
            for note in turn.get("notes", []):
                st.caption(note)
            st.markdown(turn["text"])
            hindi = ". ".join(DEVANAGARI.findall(turn["text"]))
            if turn["role"] == "assistant" and hindi:
                if st.button("🔊 Listen", key=f"listen-{i}"):
                    st.session_state[f"audio-{i}"] = True
                if st.session_state.get(f"audio-{i}"):
                    try:
                        st.audio(tts(api_key, hindi, pace), format="audio/wav", autoplay=True)
                    except SarvamError as err:
                        show_error(err)

    user_input = st.chat_input("Type in English, Hindi (हिंदी) or Hinglish…") or clicked
    if user_input:
        st.session_state.chat.append({"role": "user", "text": user_input})
        with st.spinner("सोच रहा हूँ… (thinking)"):
            reply = agent.chat(user_input)
        notes = [TOOL_LABELS[t["name"]](t["input"]) for t in reply.tools_used if t["name"] in TOOL_LABELS]
        st.session_state.chat.append({"role": "assistant", "text": reply.text, "notes": notes})
        st.rerun()


# ---- tab 3: notebook ------------------------------------------------------------

with tab_notebook:
    words = store.list_words(limit=500)
    if words:
        st.dataframe(
            [
                {"Hindi": w["hindi"], "Say it": w["transliteration"], "English": w["english"],
                 "Box (1-5)": w["box"], "Next review": w["next_review"]}
                for w in words
            ],
            hide_index=True,
            use_container_width=True,
        )
        st.caption("Words move up a box each time you get them right in a quiz, and come back for review on schedule.")
    else:
        st.info("Words you save from translations and lessons will appear here.")
