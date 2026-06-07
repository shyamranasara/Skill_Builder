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
from utils.firebase_service import record_answers_batch, get_topic_score, log_page_visit

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
ANSWERED_KEY= f"{PAGE}_answered"
ANSWER_KEY  = f"{PAGE}_user_ans"
TOPIC_KEY   = f"{PAGE}_loaded_topic"
DIFF_KEY    = f"{PAGE}_loaded_diff"
TYPE_KEY    = f"{PAGE}_loaded_type"

def _queue():   return st.session_state.get(Q_KEY, [])

# ── Settings Change Reset ────────────────────────────────────────────────────
if (st.session_state.get(TOPIC_KEY) != topic_query or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    for k in [Q_KEY, ANSWERED_KEY, ANSWER_KEY]:
        st.session_state.pop(k, None)
    st.session_state.update({TOPIC_KEY: topic_query, DIFF_KEY: difficulty, TYPE_KEY: q_type_val})

st.markdown("---")
queue = _queue()

if not queue:
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"✨ Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} questions for {exam_clean}..."):
                qs, err = generate_mcq_set(
                    topic=topic_query,
                    difficulty=difficulty,
                    q_type=q_type_val,
                    count=BATCH_SIZE
                )
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({Q_KEY: qs, ANSWERED_KEY: False, ANSWER_KEY: {}})
                st.rerun()

    st.markdown("""
    <div style='text-align:center;color:#4B5563;padding:3rem 1rem;'>
    <p style='font-size:2.5rem;margin:0;'>🏛️</p>
    <p style='font-size:1.1rem;margin-top:0.5rem;'>Select your exam & subject above and click generate to load 20 questions.</p>
    <p style='font-size:0.82rem;'>AI-driven custom competitive exams preparation, fully syllabus aligned.</p>
    </div>""", unsafe_allow_html=True)
else:
    total = len(queue)
    submitted = st.session_state.get(ANSWERED_KEY, False)
    saved_answers = st.session_state.get(ANSWER_KEY, {})

    if submitted:
        correct_count = 0
        for idx, q in enumerate(queue):
            ans = saved_answers.get(idx)
            correct = q.get("correct", [])
            is_correct = False
            if ans:
                if isinstance(ans, list):
                    is_correct = sorted(ans) == sorted(correct)
                else:
                    is_correct = ans in correct
            if is_correct:
                correct_count += 1
        
        st.markdown("### 🏆 Exam Results")
        render_score_badge(correct_count, total)
        st.markdown("---")

    user_answers = {}
    for idx, q in enumerate(queue):
        st.markdown(f"#### 📝 Question {idx+1} of {total}")
        st.markdown(f"<span style='background:#2D2D4A;color:#8B5CF6;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
        st.markdown("")

        prev_ans = saved_answers.get(idx)
        ans = render_question_card(q, key_prefix=f"{PAGE}_q{idx}", disabled=submitted, default_val=prev_ans)
        user_answers[idx] = ans

        if submitted:
            render_feedback(q, prev_ans)
        
        st.markdown("<div style='margin-bottom:2rem;'></div>", unsafe_allow_html=True)

    st.markdown("---")
    submit_col, reset_col = st.columns(2)
    
    if not submitted:
        with submit_col:
            if st.button("📝 Submit Exam", type="primary", use_container_width=True):
                results = []
                for idx, q in enumerate(queue):
                    ans = user_answers[idx]
                    correct = q.get("correct", [])
                    is_correct = False
                    if ans:
                        if isinstance(ans, list):
                            is_correct = sorted(ans) == sorted(correct)
                        else:
                            is_correct = ans in correct
                    
                    results.append(is_correct)
                    h = get_question_hash(q["question"], q["correct"])
                    save_hash(topic_query, h, q.get("keyword", ""))
                
                record_answers_batch(topic_query, results)
                
                st.session_state[ANSWER_KEY] = user_answers
                st.session_state[ANSWERED_KEY] = True
                st.rerun()
        with reset_col:
            if st.button("🗑️ Discard & Load New Set", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = {}
                st.rerun()
    else:
        with submit_col:
            st.info("Exam submitted! Answers and explanations are shown under each question.")
        with reset_col:
            if st.button("🔄 Generate New Exam Set", type="primary", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = {}
                st.rerun()
