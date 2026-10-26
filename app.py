"""Streamlit web app for Hindi Saathi.  Run:  streamlit run app.py"""

import re

import streamlit as st
from dotenv import load_dotenv

from hindi_saathi import ui
from hindi_saathi.agent import HindiTutorAgent
from hindi_saathi.curriculum import LESSONS
from hindi_saathi.practice import PUNCT, feedback, score_pronunciation
from hindi_saathi.sarvam import SarvamClient, SarvamError, get_api_key

load_dotenv()

st.set_page_config(page_title="Hindi Saathi", page_icon="🪔", layout="wide")
st.markdown(ui.CSS, unsafe_allow_html=True)

DEVANAGARI = re.compile(r"[ऀ-ॿ]+(?:[\s,।॥?!]+[ऀ-ॿ]+)*")
PAGES = ["🔁 Translate", "💬 Tutor", "🃏 Cards", "📚 Course"]
VOICES = {"Priya (female)": "priya", "Shubh (male)": "shubh", "Neha (female)": "neha", "Rahul (male)": "rahul"}

EXAMPLES = {
    "☕ Order tea": "I would like a cup of tea, please.",
    "🚉 Find the station": "Where is the railway station?",
    "🙋 Introduce yourself": "Hello, my name is Asha and I am learning Hindi.",
    "💰 Ask the price": "How much does this cost?",
    "🐢 Speak slowly": "Can you speak a little slowly?",
    "🍛 मुझे भूख लगी है": "मुझे भूख लगी है",
}

QUICK_ACTIONS = {
    "📚 Next lesson": "Teach me the next lesson in my curriculum.",
    "🧠 Quiz me": "Give me a short quiz (5 questions, one at a time) at my level.",
    "🔄 Review words": "Let's review my vocabulary words that are due.",
    "💬 Conversation": "Let's have a simple conversation in Hindi. You start, and correct my mistakes.",
    "📈 My progress": "How am I doing? Summarise my progress and suggest what to practise next.",
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


@st.cache_data(show_spinner=False, max_entries=300)
def tts(api_key: str, text: str, pace: float, speaker: str) -> bytes:
    return SarvamClient(api_key).speak(text, pace=pace, speaker=speaker)


def play(text: str, autoplay: bool = False) -> None:
    try:
        st.audio(tts(api_key, text, pace, voice), format="audio/wav", autoplay=autoplay)
    except SarvamError as err:
        show_error(err)


def word_pairs(hindi: str, roman: str) -> list[str]:
    hindi_words = PUNCT.sub(" ", hindi).split()
    roman_words = re.sub(r"[.,!?;:\"“”()।]", " ", roman).split()
    if len(hindi_words) == len(roman_words):
        return [f"{h} · {r.lower()}" for h, r in zip(hindi_words, roman_words)]
    return hindi_words


# ---- session setup -----------------------------------------------------------------

api_key = get_api_key()
with st.sidebar:
    st.markdown(ui.SIDEBAR_BRAND, unsafe_allow_html=True)
    if not api_key:
        api_key = st.text_input("Sarvam API key", type="password", help="Or set SARVAM_API_KEY in .env / Streamlit secrets")

if not api_key:
    st.markdown(ui.hero({"streak_days": 0, "words_saved": 0, "words_due_for_review": 0, "quiz_accuracy_percent": None,
                         "lessons_completed": [], "profile": {}}, len(LESSONS)), unsafe_allow_html=True)
    st.info("Add your Sarvam API key in the sidebar (or a `.env` file) to start.")
    st.stop()

if st.session_state.get("agent_key") != api_key:
    sarvam = SarvamClient(api_key)
    st.session_state.update(sarvam=sarvam, agent=HindiTutorAgent(sarvam), agent_key=api_key, chat=[])
sarvam: SarvamClient = st.session_state.sarvam
agent: HindiTutorAgent = st.session_state.agent
store = agent.store
st.session_state.setdefault("nav", PAGES[0])
st.session_state.setdefault("query", "")

with st.sidebar:
    st.write("")
    voice = VOICES[st.selectbox("🎙️ Voice", list(VOICES))]
    slow = st.toggle("🐢 Slow audio for practice", value=True)
    pace = 0.75 if slow else 1.0
    if st.button("🧹 New tutor chat", use_container_width=True):
        agent.reset()
        st.session_state.chat = []
    st.divider()
    st.caption("Powered by Sarvam AI")
    st.markdown(ui.API_BADGES, unsafe_allow_html=True)

st.markdown(ui.hero(store.summary(), len(LESSONS)), unsafe_allow_html=True)
page = st.segmented_control("Navigate", PAGES, key="nav", required=True, label_visibility="collapsed", width="stretch")
st.write("")


# ---- page: translate & speak (the core flow) -------------------------------------------

def translate_now() -> None:
    text = st.session_state.query.strip()
    if not text:
        return
    mode = "formal" if st.session_state.get("style", "Standard Hindi") == "Standard Hindi" else "modern-colloquial"
    try:
        first = sarvam.translate(text, source="auto", target="hi-IN", mode=mode)
        if first.get("source_language_code") == "hi-IN":
            hindi = text
            english = sarvam.translate(hindi, source="hi-IN", target="en-IN", mode="formal")["translated_text"]
        else:
            hindi, english = first["translated_text"], text
        st.session_state.result = {"hindi": hindi, "english": english, "roman": sarvam.romanize(hindi)}
        st.session_state.pop("explanation", None)
    except SarvamError as err:
        st.session_state.translate_error = str(err)


def save_result() -> None:
    r = st.session_state.result
    store.add_word(r["hindi"], r["roman"], r["english"], part_of_speech="phrase")
    st.session_state.saved_toast = r["hindi"]


def pick_example() -> None:
    choice = st.session_state.example
    if choice:
        st.session_state.query = EXAMPLES[choice]
        translate_now()
    st.session_state.example = None


if page == PAGES[0]:
    with st.container(key="input-card"):
        st.markdown('<div class="label">Type anything - English, हिंदी or Hinglish</div>', unsafe_allow_html=True)
        st.text_area("Your sentence", key="query", height=90, label_visibility="collapsed",
                     placeholder="e.g. Where is the railway station?  /  मुझे भूख लगी है")
        st.pills("✨ Try an example", list(EXAMPLES), key="example", on_change=pick_example)
        left, right = st.columns([2, 1], vertical_alignment="center")
        with left:
            st.radio("Style", ["Standard Hindi", "Hinglish (casual)"], key="style", horizontal=True,
                     label_visibility="collapsed")
        with right:
            if st.button("Translate ➜", type="primary", use_container_width=True):
                with st.spinner("Translating with Sarvam…"):
                    translate_now()

    if err := st.session_state.pop("translate_error", None):
        show_error(Exception(err))
    if saved := st.session_state.pop("saved_toast", None):
        st.toast(f"Saved {saved} to your notebook 📒")

    result = st.session_state.get("result")
    if result:
        st.write("")
        with st.container(key="result-card"):
            st.markdown(ui.result_block(result["hindi"], result["roman"], result["english"]), unsafe_allow_html=True)
            st.write("")
            a, b, c = st.columns([2.2, 1, 1.2], vertical_alignment="center")
            with a:
                play(result["hindi"])
            with b:
                st.button("📒 Save", use_container_width=True, on_click=save_result)
            with c:
                explain = st.button("🧑‍🏫 Explain grammar", use_container_width=True)
            word = st.pills("👆 Tap a word to hear it", word_pairs(result["hindi"], result["roman"]),
                            key=f"word-{result['hindi']}")
            if word:
                play(word.split(" · ")[0], autoplay=True)

        if explain:
            with st.spinner("Your tutor is preparing an explanation… (about 15 s)"):
                st.session_state.explanation = agent.chat(
                    f"Briefly explain this Hindi sentence word by word for a beginner, with any grammar or "
                    f"formality notes: {result['hindi']} (meaning: {result['english']})"
                ).text
        if st.session_state.get("explanation"):
            st.write("")
            with st.container(key="explain-card"):
                st.markdown('<div class="label">🧑‍🏫 Tutor explains</div>', unsafe_allow_html=True)
                st.markdown(st.session_state.explanation)

        st.write("")
        with st.container(key="practice-card"):
            st.markdown('<div class="label">🎤 Your turn</div>', unsafe_allow_html=True)
            st.markdown(f"Read this aloud: **{result['hindi']}**")
            recording = st.audio_input("Record yourself", sample_rate=16000, key=f"rec-{result['hindi']}",
                                       label_visibility="collapsed")
            if recording:
                with st.spinner("Listening with Sarvam Saaras…"):
                    try:
                        heard = sarvam.transcribe(recording.getvalue(), filename="speech.wav")["transcript"]
                    except SarvamError as err:
                        show_error(err)
                        heard = None
                if heard is not None:
                    scored = score_pronunciation(result["hindi"], heard)
                    st.markdown(ui.score_ring(scored["score"], heard, scored["words"], feedback(scored["score"])),
                                unsafe_allow_html=True)
                    if scored["score"] >= 90:
                        st.balloons()


# ---- page: tutor agent ------------------------------------------------------------------

elif page == PAGES[1]:
    def pick_action() -> None:
        if st.session_state.quick:
            st.session_state.pending = QUICK_ACTIONS[st.session_state.quick]
        st.session_state.quick = None

    st.pills("Quick actions", list(QUICK_ACTIONS), key="quick", on_change=pick_action, label_visibility="collapsed")
    pending = st.session_state.pop("pending", None)

    if not st.session_state.chat and not pending:
        st.markdown(
            '<div class="welcome"><h3>🪔 Namaste! I\'m your Hindi tutor.</h3>'
            "<p>Ask me to translate, explain grammar, teach a lesson, quiz you or chat in Hindi.</p></div>",
            unsafe_allow_html=True,
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
                    play(hindi, autoplay=True)

    user_input = st.chat_input("Type in English, Hindi (हिंदी) or Hinglish…") or pending
    if user_input:
        st.session_state.chat.append({"role": "user", "text": user_input})
        with st.chat_message("user", avatar="🧑‍🎓"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="🪔"):
            with st.spinner("सोच रहा हूँ… thinking"):
                reply = agent.chat(user_input)
        notes = [TOOL_LABELS[t["name"]](t["input"]) for t in reply.tools_used if t["name"] in TOOL_LABELS]
        st.session_state.chat.append({"role": "assistant", "text": reply.text, "notes": notes})
        st.rerun()


# ---- page: flashcards ---------------------------------------------------------------------

elif page == PAGES[2]:
    due = store.list_words(only_due=True, limit=200)
    deck = due or store.list_words(limit=200)
    if not deck:
        st.info("Your notebook is empty. Save words from **🔁 Translate** or let the tutor save them for you. 📒")
    else:
        st.session_state.setdefault("fc_i", 0)
        st.session_state.setdefault("fc_reveal", False)
        card = deck[st.session_state.fc_i % len(deck)]
        st.caption(f"{'🔔 ' + str(len(due)) + ' due for review' if due else '✨ Nothing due - free practice'} · "
                   f"card {st.session_state.fc_i % len(deck) + 1} of {len(deck)}")

        _, mid, _ = st.columns([1, 3, 1])
        with mid:
            with st.container(key="flashcard"):
                st.markdown(ui.flashcard(card, st.session_state.fc_reveal), unsafe_allow_html=True)
            st.write("")

            def answer(correct: bool) -> None:
                store.record_answer(card["hindi"], correct)
                st.session_state.fc_reveal = False
                if not due:
                    st.session_state.fc_i += 1

            if not st.session_state.fc_reveal:
                c1, c2 = st.columns(2)
                if c1.button("👀 Show answer", type="primary", use_container_width=True):
                    st.session_state.fc_reveal = True
                    st.rerun()
                if c2.button("⏭️ Skip", use_container_width=True):
                    st.session_state.fc_i += 1
                    st.rerun()
            else:
                play(card["hindi"], autoplay=True)
                c1, c2 = st.columns(2)
                c1.button("🔁 Again", use_container_width=True, on_click=answer, args=(False,))
                c2.button("✅ I knew it", type="primary", use_container_width=True, on_click=answer, args=(True,))

        with st.expander(f"📒 All words in your notebook ({len(store.state['vocabulary'])})"):
            st.dataframe(
                [{"Hindi": w["hindi"], "Say it": w["transliteration"], "English": w["english"],
                  "Mastery": "●" * w["box"] + "○" * (5 - w["box"]), "Next review": w["next_review"]}
                 for w in store.list_words(limit=500)],
                hide_index=True, use_container_width=True,
            )


# ---- page: course map ---------------------------------------------------------------------

else:
    done = set(store.state["lessons_completed"])
    next_id = next((lesson["id"] for lesson in LESSONS if lesson["id"] not in done), None)
    st.progress(len(done) / len(LESSONS), text=f"Course progress: {len(done)} of {len(LESSONS)} lessons")

    def start_lesson(lesson: dict) -> None:
        st.session_state.pending = f"Teach me lesson {lesson['id']}: {lesson['title']}."
        st.session_state.nav = PAGES[1]

    for row in range(0, len(LESSONS), 3):
        cols = st.columns(3)
        for col, (i, lesson) in zip(cols, list(enumerate(LESSONS, 1))[row:row + 3]):
            status = "done" if lesson["id"] in done else "next" if lesson["id"] == next_id else "todo"
            with col, st.container(key=f"lesson-{lesson['id']}"):
                st.markdown(ui.lesson_card(i, lesson, status), unsafe_allow_html=True)
                st.button("↺ Review" if status == "done" else "▶ Start lesson", key=f"start-{lesson['id']}",
                          type="primary" if status == "next" else "secondary", use_container_width=True,
                          on_click=start_lesson, args=(lesson,))
