"""
govt_mcq.py — Government Exams MCQs with 20-question batch queue system.
Covers Bank, SSC, UPSC, State Police, and more.
"""

import json
import streamlit as st
from pathlib import Path
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answer, get_topic_score, log_page_visit

PAGE = "govt"
BATCH_SIZE = 20

# ── Track Telemetry ─────────────────────────────────────────────────────────
log_page_visit("Government Exam MCQs")

# ── Load Syllabus Data ────────────────────────────────────────────────────────
@st.cache_data
def load_govt_syllabus():
    path = Path(__file__).parent.parent / "data" / "govt_syllabus.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

govt_syllabus = load_govt_syllabus()

# ── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background:linear-gradient(90deg,#8B5CF6,#EC4899);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
🏛️ Government Exam MCQs</h1>
<p style='color:#9CA3AF;'>Practice topic-wise MCQs for UPSC CSE, Bank PO & Clerk, SSC CGL, and State Police</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add key to `.streamlit/secrets.toml`")
    st.stop()

# ── Exam & Topic Selection ───────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    selected_exam = st.selectbox("📌 Select Exam", list(govt_syllabus.keys()), key=f"{PAGE}_exam")
    exam_topics = govt_syllabus[selected_exam]

with col2:
    selected_subject = st.selectbox("📚 Select Subject", list(exam_topics.keys()), key=f"{PAGE}_subject")
    subject_details = exam_topics[selected_subject]
    # Allow selection of specific topics or general subject level practice
    topics_list = ["All Topics"] + subject_details.get("topics", [])
    selected_topic = st.selectbox("📋 Select Topic", topics_list, key=f"{PAGE}_topic")

with col3:
    difficulty = st.select_slider(
        "🎯 Difficulty", options=["easy", "medium", "hard"], value="medium", key=f"{PAGE}_diff"
    )

q_type = st.radio("Question Type", ["Single Choice", "Multiple Choice"], key=f"{PAGE}_qtype_radio", horizontal=True)
q_type_val = "single" if q_type == "Single Choice" else "multi"

# Construct specific query context for Gemini prompt
exam_clean = selected_exam.split(" ", 1)[-1].strip()
topic_query = f"{exam_clean} - {selected_subject}"
if selected_topic != "All Topics":
    topic_query += f": {selected_topic}"

# ── Sidebar Stats ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏛️ Govt Exam Stats")
    score_data = get_topic_score(topic_query)
    correct_cnt = score_data["correct"]
    total_ans   = score_data["total"]
    if total_ans > 0:
        pct = correct_cnt / total_ans * 100
        st.metric("Correct", f"{correct_cnt}/{total_ans}", f"{pct:.0f}%")
        st.progress(correct_cnt / total_ans)
    else:
        st.info("Start practicing to see stats!")
    st.markdown("---")
    st.metric("🔢 Unique Qs seen (all exams)", get_total_seen())
    if st.button("🗑️ Reset topic history", use_container_width=True):
        clear_topic_history(topic_query)
        st.success("History cleared!")

# ── Session state keys ─────────────────────────────────────────────────────────
Q_KEY       = f"{PAGE}_queue"
IDX_KEY     = f"{PAGE}_idx"
ANSWERED_KEY= f"{PAGE}_answered"
ANSWER_KEY  = f"{PAGE}_user_ans"
TOPIC_KEY   = f"{PAGE}_loaded_topic"
DIFF_KEY    = f"{PAGE}_loaded_diff"
TYPE_KEY    = f"{PAGE}_loaded_type"

def _queue():   return st.session_state.get(Q_KEY, [])
def _idx():     return st.session_state.get(IDX_KEY, 0)
def _current(): q = _queue(); i = _idx(); return q[i] if q and i < len(q) else None

# ── Settings Change Reset ────────────────────────────────────────────────────
if (st.session_state.get(TOPIC_KEY) != topic_query or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    st.session_state[Q_KEY] = []
    st.session_state[IDX_KEY] = 0
    st.session_state[ANSWERED_KEY] = False
    st.session_state[ANSWER_KEY] = None
    st.session_state[TOPIC_KEY] = topic_query
    st.session_state[DIFF_KEY] = difficulty
    st.session_state[TYPE_KEY] = q_type_val

st.markdown("---")

queue = _queue()

if not queue:
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"✨ Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} questions for {exam_clean}..."):
                # Use general MCQ batch generator
                qs, err = generate_mcq_set(
                    topic=topic_query,
                    difficulty=difficulty,
                    q_type=q_type_val,
                    count=BATCH_SIZE
                )
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({
                    Q_KEY: qs,
                    IDX_KEY: 0,
                    ANSWERED_KEY: False,
                    ANSWER_KEY: None
                })
                st.rerun()

    st.markdown("""
    <div style='text-align:center;color:#4B5563;padding:3rem 1rem;'>
    <p style='font-size:2.5rem;margin:0;'>🏛️</p>
    <p style='font-size:1.1rem;margin-top:0.5rem;'>Select your exam & subject above and click generate to load 20 questions.</p>
    <p style='font-size:0.82rem;'>AI-driven custom competitive exams preparation, fully syllabus aligned.</p>
    </div>""", unsafe_allow_html=True)
else:
    idx = _idx()
    total = len(queue)
    
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.8rem;'>
    <span style='color:#8B5CF6;font-weight:700;font-size:1rem;'>Q {idx+1} / {total}</span>
    <div style='flex:1;background:#2D2D4A;border-radius:4px;height:8px;'>
    <div style='background:linear-gradient(90deg,#8B5CF6,#EC4899);width:{idx/total*100:.0f}%;height:8px;border-radius:4px;'></div>
    </div>
    <span style='color:#6B7280;font-size:0.82rem;'>{selected_subject}</span>
    </div>""", unsafe_allow_html=True)

    q = _current()
    if q is None:
        s = get_topic_score(topic_query)
        st.success(f"🎉 Practice Set Complete! Score: {s['correct']}/{s['total']}")
        if st.button("🔄 Start New Set", type="primary"):
            st.session_state[Q_KEY] = []
            st.rerun()
    else:
        # Keyword tag
        st.markdown(f"<span style='background:#2D2D4A;color:#A78BFA;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
        st.markdown("")
        
        user_answer = render_question_card(q, key_prefix=f"{PAGE}_q{idx}")
        
        c1, c2, c3, _ = st.columns([1, 1, 1, 2])
        with c1:
            if not st.session_state.get(ANSWERED_KEY, False):
                if st.button("✅ Submit Answer", use_container_width=True, type="primary"):
                    if user_answer:
                        is_correct = render_feedback(q, user_answer)
                        save_hash(topic_query, get_question_hash(q["question"], q["correct"]), q.get("keyword", ""))
                        record_answer(topic_query, is_correct)
                        st.session_state.update({ANSWERED_KEY: True, ANSWER_KEY: user_answer})
                    else:
                        st.warning("Please select an answer first.")
            else:
                render_feedback(q, st.session_state[ANSWER_KEY])

        with c2:
            if st.session_state.get(ANSWERED_KEY, False):
                is_last = idx >= total - 1
                next_label = "Finish Set" if is_last else f"Next Question (Q{idx+2})"
                if st.button(next_label, use_container_width=True):
                    if is_last:
                        st.session_state[Q_KEY] = []
                        st.session_state[IDX_KEY] = 0
                    else:
                        st.session_state[IDX_KEY] = idx + 1
                    st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None})
                    st.rerun()

        with c3:
            if st.button("🔄 Reset Queue", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[IDX_KEY] = 0
                st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None})
                st.rerun()

score_data = get_topic_score(topic_query)
if score_data["total"] > 0:
    st.markdown("---")
    render_score_badge(score_data["correct"], score_data["total"])
