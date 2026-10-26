"""Look and feel for the Streamlit app: global CSS and small HTML building blocks."""

from __future__ import annotations

from html import escape

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

:root {
  --saffron: #EA580C; --saffron-soft: #FFF1E6; --rose: #DB2777; --ink: #1E1B4B;
  --muted: #64748B; --line: #FED7AA; --card: #FFFFFF; --ok: #16A34A; --bad: #DC2626;
}
html, body, p, li, label, h1, h2, h3, h4, button, input, textarea, select { font-family: 'Poppins', sans-serif; }
.block-container { padding-top: 1.6rem; max-width: 1120px; }
[data-testid="stToolbar"], [data-testid="stDecoration"], footer, #MainMenu { display: none !important; }
header[data-testid="stHeader"] { background: transparent; }

/* hero */
.hero { background: linear-gradient(120deg, #F97316 0%, #DB2777 55%, #6D28D9 100%); border-radius: 24px;
  padding: 26px 30px; color: #fff; display: flex; flex-wrap: wrap; gap: 18px; align-items: center;
  justify-content: space-between; box-shadow: 0 18px 40px rgba(219, 39, 119, .25); margin-bottom: 18px; }
.hero h1 { color: #fff; font-size: 2.1rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.25; }
.hero h1 span { font-weight: 500; opacity: .85; font-size: 1.3rem; margin-left: 8px; }
.hero p { margin: 4px 0 0; opacity: .92; font-size: .98rem; }
.hero-stats { display: flex; gap: 10px; flex-wrap: wrap; }
.stat { background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.3); backdrop-filter: blur(6px);
  border-radius: 16px; padding: 8px 14px; min-width: 86px; text-align: center; }
.stat b { display: block; font-size: 1.3rem; line-height: 1.3; }
.stat span { font-size: .72rem; opacity: .9; text-transform: uppercase; letter-spacing: .04em; }

/* navigation (segmented control) */
.st-key-nav button[data-variant="segmented_control"] { flex: 1; padding: 10px 6px; font-weight: 600; font-size: 1rem;
  background: #fff; border-color: var(--line); }
.st-key-nav button[data-variant="segmented_control"][aria-checked="true"] {
  background: linear-gradient(135deg, #F97316, #DB2777) !important; color: #fff !important; border-color: transparent !important; }
.st-key-nav button[data-variant="segmented_control"] * { white-space: nowrap; }

/* buttons */
.stButton > button, [data-testid="stBaseButton-secondary"] { border-radius: 12px; border: 1px solid var(--line);
  font-weight: 500; transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease; }
.stButton > button:hover { transform: translateY(-1px); border-color: var(--saffron); color: var(--saffron);
  box-shadow: 0 6px 16px rgba(234, 88, 12, .18); }
[data-testid="stBaseButton-primary"] { background: linear-gradient(135deg, #F97316, #DB2777) !important;
  border: none !important; color: #fff !important; font-weight: 600 !important; }
[data-testid="stBaseButton-primary"]:hover { color: #fff !important; filter: brightness(1.05); }

/* cards */
.st-key-input-card, .st-key-result-card, .st-key-practice-card, .st-key-explain-card, .st-key-flashcard,
[class*="st-key-lesson-"] { background: var(--card); border: 1px solid var(--line); border-radius: 20px;
  padding: 20px 22px; box-shadow: 0 10px 28px rgba(234, 88, 12, .08); }
.st-key-result-card { border-top: 5px solid var(--saffron); animation: pop .35s ease; }
.st-key-explain-card { background: #FAF5FF; border-color: #E9D5FF; }
@keyframes pop { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

.hindi-big { font-size: 2.3rem !important; font-weight: 600; color: var(--ink); line-height: 1.45; margin: 0; }
.roman { color: #C2410C; font-style: italic; font-size: 1.1rem; margin-top: 2px; }
.english { color: var(--muted); font-size: 1rem; margin-top: 2px; }
.label { font-size: .72rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--saffron); }

/* pills */
button[data-variant="pills"] { border-radius: 999px; background: #fff; border-color: var(--line);
  transition: transform .12s ease, border-color .12s ease; }
button[data-variant="pills"]:hover { transform: translateY(-1px); border-color: var(--saffron); color: var(--saffron); }
button[data-variant="pills"][aria-checked="true"] { background: var(--saffron-soft); border-color: var(--saffron);
  color: var(--saffron); }
.st-key-result-card button[data-variant="pills"] { font-size: 1.05rem; padding: 6px 14px; }

/* pronunciation */
.score-wrap { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.word-chip { display: inline-block; padding: 4px 12px; border-radius: 999px; margin: 3px; font-size: 1.15rem; font-weight: 500; }
.word-chip.ok { background: #DCFCE7; color: #166534; }
.word-chip.bad { background: #FEE2E2; color: #991B1B; text-decoration: underline wavy #F87171; }
.heard { color: var(--muted); font-size: .92rem; }

/* flashcards */
.st-key-flashcard { text-align: center; padding: 34px 22px; min-height: 230px;
  background: radial-gradient(circle at top, #FFF7ED, #FFFFFF 70%); }
.fc-hindi { font-size: 3rem !important; font-weight: 700; color: var(--ink); line-height: 1.4; }
.fc-back { margin-top: 10px; animation: pop .3s ease; }
.fc-meta { color: var(--muted); font-size: .85rem; }
.box-dots { letter-spacing: 4px; color: var(--saffron); }

/* lessons */
[class*="st-key-lesson-"] { padding: 16px 18px; }
.lesson-num { font-size: .75rem; font-weight: 700; color: var(--saffron); letter-spacing: .06em; }
.lesson-title { font-weight: 600; color: var(--ink); font-size: 1.02rem; margin: 2px 0 6px; }
.lesson-goals { color: var(--muted); font-size: .85rem; line-height: 1.6; height: 4.8em; overflow: hidden;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
.lesson-title { min-height: 2.9em; }
.badge { display: inline-block; font-size: .72rem; font-weight: 600; padding: 2px 10px; border-radius: 999px; }
.badge.done { background: #DCFCE7; color: #166534; } .badge.next { background: #FFEDD5; color: #C2410C; }
.badge.todo { background: #F1F5F9; color: #64748B; }

/* chat */
[data-testid="stChatMessage"] { background: var(--card); border: 1px solid #F3E8DD; border-radius: 18px;
  padding: 14px 16px; box-shadow: 0 4px 14px rgba(30, 27, 75, .05); }
[data-testid="stChatInput"] { border-radius: 16px; }
.welcome { text-align: center; padding: 26px 10px 8px; }
.welcome h3 { margin-bottom: 4px; color: var(--ink); }

/* sidebar */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #FFF7ED 0%, #FDF2F8 100%); border-right: 1px solid var(--line); }
.brand { font-size: 1.45rem; font-weight: 700; color: var(--ink); }
.brand small { display: block; font-size: .8rem; font-weight: 400; color: var(--muted); }
@media (max-width: 640px) {
  .hero { padding: 20px; border-radius: 20px; }
  .hero h1 { font-size: 1.6rem; }
  .stat { min-width: 64px; padding: 6px 10px; }
  .stat b { font-size: 1.1rem; }
  .st-key-nav button[data-variant="segmented_control"] { font-size: .85rem; padding: 8px 2px; }
  .hindi-big { font-size: 1.8rem !important; }
  .fc-hindi { font-size: 2.3rem !important; }
}
.api-badge { display: inline-block; background: #fff; border: 1px solid var(--line); border-radius: 999px;
  padding: 3px 10px; margin: 3px 2px; font-size: .74rem; color: #9A3412; }
</style>
"""


def hero(summary: dict, lessons_total: int) -> str:
    acc = summary["quiz_accuracy_percent"]
    stats = [
        (f"🔥 {summary['streak_days']}", "day streak"),
        (str(summary["words_saved"]), "words"),
        (str(summary["words_due_for_review"]), "due today"),
        (f"{acc}%" if acc is not None else "–", "accuracy"),
        (f"{len(summary['lessons_completed'])}/{lessons_total}", "lessons"),
    ]
    stat_html = "".join(f'<div class="stat"><b>{v}</b><span>{k}</span></div>' for v, k in stats)
    name = summary["profile"].get("name")
    greeting = f"नमस्ते, {escape(name)}! " if name else "नमस्ते! "
    return f"""
    <div class="hero">
      <div><h1>हिंदी साथी<span>Hindi Saathi</span></h1>
        <p>{greeting}Translate · Listen · Speak · Learn - your AI Hindi companion</p></div>
      <div class="hero-stats">{stat_html}</div>
    </div>"""


def result_block(hindi: str, roman: str, english: str) -> str:
    return f"""
    <div class="label">Hindi</div>
    <div class="hindi-big">{escape(hindi)}</div>
    <div class="roman">🗣️ {escape(roman)}</div>
    <div class="english">📝 {escape(english)}</div>"""


def score_ring(score: int, heard: str, words: list[dict], message: str) -> str:
    color = "#16A34A" if score >= 70 else "#F59E0B" if score >= 40 else "#DC2626"
    circumference = 2 * 3.1416 * 52
    offset = circumference * (1 - score / 100)
    chips = "".join(f'<span class="word-chip {"ok" if w["ok"] else "bad"}">{escape(w["word"])}</span>' for w in words)
    return f"""
    <div class="score-wrap">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="52" stroke="#FDE7D3" stroke-width="12" fill="none"/>
        <circle cx="60" cy="60" r="52" stroke="{color}" stroke-width="12" fill="none" stroke-linecap="round"
          stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{offset:.1f}" transform="rotate(-90 60 60)"/>
        <text x="60" y="66" text-anchor="middle" font-size="30" font-weight="700" fill="#1E1B4B"
          font-family="Poppins, sans-serif">{score}</text>
        <text x="60" y="84" text-anchor="middle" font-size="11" fill="#64748B" font-family="Poppins, sans-serif">/ 100</text>
      </svg>
      <div style="flex:1;min-width:220px">
        <div style="font-weight:600;font-size:1.05rem;color:#1E1B4B">{escape(message)}</div>
        <div style="margin:6px 0">{chips}</div>
        <div class="heard">I heard: <b>{escape(heard) or "(nothing)"}</b></div>
      </div>
    </div>"""


def flashcard(word: dict, revealed: bool) -> str:
    dots = "●" * word["box"] + "○" * (5 - word["box"])
    back = ""
    if revealed:
        example = f'<div class="fc-meta" style="margin-top:8px">{escape(word["example"])}</div>' if word.get("example") else ""
        back = f"""<div class="fc-back">
          <div class="roman" style="font-size:1.25rem">{escape(word["transliteration"])}</div>
          <div style="font-size:1.3rem;font-weight:600;color:#1E1B4B">{escape(word["english"])}</div>{example}</div>"""
    return f"""
    <div class="fc-meta">Mastery <span class="box-dots">{dots}</span></div>
    <div class="fc-hindi">{escape(word["hindi"])}</div>{back}"""


def lesson_card(index: int, lesson: dict, status: str) -> str:
    badge = {"done": "✓ Done", "next": "▶ Up next", "todo": "To learn"}[status]
    return f"""
    <div class="lesson-num">LESSON {index:02d} <span class="badge {status}" style="float:right">{badge}</span></div>
    <div class="lesson-title">{escape(lesson["title"])}</div>
    <div class="lesson-goals">{escape(lesson["goals"])}</div>"""


SIDEBAR_BRAND = '<div class="brand">🪔 Hindi Saathi<small>AI Hindi tutor & translator</small></div>'
API_BADGES = "".join(
    f'<span class="api-badge">{name}</span>'
    for name in ["Mayura · translate", "Transliterate", "Bulbul · voice", "Saaras · listen", "Sarvam-105B · tutor"]
)
