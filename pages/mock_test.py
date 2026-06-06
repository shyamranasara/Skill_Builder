"""
mock_test.py — Timed 30-question mock test with countdown, topic-wise breakdown, score history.
"""

import time
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.gemini_service import generate_mcq_batch, is_api_configured
from utils.question_hash import save_hash, get_question_hash
from utils.firebase_service import save_test_result, get_test_history, log_page_visit

log_page_visit("Mock Test")



# ── Constants ─────────────────────────────────────────────────────────────────
MOCK_TOPICS = [
    "Data Structures and Algorithms (GATE CSE)",
    "Operating Systems (GATE CSE)",
    "Database Management Systems (GATE CSE)",
    "Computer Networks (GATE CSE)",
    "Theory of Computation (GATE CSE)",
    "Compiler Design (GATE CSE)",
    "Computer Organization and Architecture (GATE CSE)",
    "Discrete Mathematics for GATE CSE",
    "Quantitative Aptitude for GATE GA",
    "Verbal Ability for GATE GA",
]

BATCH_SIZE = 5  # Fetch 5 questions at a time to reduce API calls

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background: linear-gradient(90deg, #EF4444, #F59E0B);
-webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
🎯 Mock Test</h1>
<p style='color:#9CA3AF;'>Timed test · GATE-style questions · Detailed score analysis</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add your key to `.env` and restart.")
    st.stop()

# ── State Helpers ─────────────────────────────────────────────────────────────
def init_test_state():
    st.session_state.update({
        "test_active": False,
        "test_questions": [],
        "test_current_idx": 0,
        "test_answers": {},
        "test_start_time": None,
        "test_duration": 60,  # minutes
        "test_num_q": 30,
        "test_completed": False,
    })

if "test_active" not in st.session_state:
    init_test_state()

# ── Score History Chart ───────────────────────────────────────────────────────
def show_history():
    history = get_test_history()
    if not history:
        return
    st.markdown("### 📈 Your Score History")
    df = pd.DataFrame(history)
    fig = px.line(
        df, x="timestamp", y="percentage",
        markers=True, line_shape="spline",
        title="Mock Test Score Trend",
        labels={"percentage": "Score (%)", "timestamp": "Date"},
        color_discrete_sequence=["#6C63FF"],
    )
    fig.update_layout(
        paper_bgcolor="#0E0E1A", plot_bgcolor="#1A1A2E",
        font_color="#E8E8F0", title_font_color="#E8E8F0",
        xaxis=dict(showgrid=False), yaxis=dict(range=[0, 100], gridcolor="#2D2D4A"),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Test Setup Screen ─────────────────────────────────────────────────────────
if not st.session_state.test_active and not st.session_state.test_completed:
    show_history()
    st.markdown("---")
    st.markdown("### ⚙️ Test Configuration")
    cfg_col1, cfg_col2 = st.columns(2)
    with cfg_col1:
        num_q = st.select_slider("Number of Questions", [10, 20, 30], value=30, key="cfg_num_q")
    with cfg_col2:
        duration = st.select_slider("Time Limit (minutes)", [15, 30, 45, 60], value=60, key="cfg_dur")

    st.markdown("**Topics to include:**")
    selected_topics = []
    topic_cols = st.columns(2)
    for i, t in enumerate(MOCK_TOPICS):
        col = topic_cols[i % 2]
        if col.checkbox(t.split("(")[0].strip(), value=True, key=f"mock_topic_{i}"):
            selected_topics.append(t)

    st.markdown("---")
    if st.button("🚀 Start Mock Test", type="primary", use_container_width=True):
        if not selected_topics:
            st.error("Please select at least one topic.")
        else:
            with st.spinner(f"Generating {num_q} questions... (this may take 30–60 seconds)"):
                all_questions = []
                remaining = num_q
                while remaining > 0:
                    batch_n = min(BATCH_SIZE, remaining)
                    qs, err = generate_mcq_batch(selected_topics, count=batch_n)
                    if err or not qs:
                        st.error(f"Error generating questions: {err}")
                        break
                    all_questions.extend(qs[:batch_n])
                    remaining -= batch_n

            if len(all_questions) >= 5:
                st.session_state.test_active = True
                st.session_state.test_questions = all_questions
                st.session_state.test_current_idx = 0
                st.session_state.test_answers = {}
                st.session_state.test_start_time = time.time()
                st.session_state.test_duration = duration
                st.session_state.test_num_q = len(all_questions)
                st.session_state.test_completed = False
                st.rerun()

# ── Active Test ───────────────────────────────────────────────────────────────
elif st.session_state.test_active and not st.session_state.test_completed:
    questions = st.session_state.test_questions
    idx = st.session_state.test_current_idx
    total = len(questions)

    # Countdown
    elapsed = time.time() - st.session_state.test_start_time
    limit_secs = st.session_state.test_duration * 60
    remaining_secs = max(0, limit_secs - int(elapsed))
    mins, secs = divmod(remaining_secs, 60)

    timer_color = "#4CAF50" if remaining_secs > limit_secs * 0.5 else "#FF9800" if remaining_secs > limit_secs * 0.2 else "#F44336"

    # Header bar
    h_col1, h_col2, h_col3 = st.columns([2, 2, 1])
    with h_col1:
        st.markdown(f"**Question {idx + 1} of {total}**")
        st.progress((idx) / total)
    with h_col2:
        st.markdown(f"""<div style='text-align:center; font-size:1.8rem; font-weight:700;
        color:{timer_color};'>⏱️ {mins:02d}:{secs:02d}</div>""", unsafe_allow_html=True)
    with h_col3:
        if st.button("🏁 End Test", use_container_width=True):
            st.session_state.test_active = False
            st.session_state.test_completed = True
            st.rerun()

    if remaining_secs == 0:
        st.warning("⏰ Time's up! Submitting your test...")
        st.session_state.test_active = False
        st.session_state.test_completed = True
        st.rerun()

    st.markdown("---")

    q = questions[idx]
    topic_tag = q.get("topic", "General")
    st.markdown(f"<span style='background:#2D2D4A; color:#F59E0B; padding:3px 10px; border-radius:12px; font-size:0.78rem;'>📌 {topic_tag}</span>", unsafe_allow_html=True)
    st.markdown("")

    st.markdown(f"""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:4px solid #EF4444; border-radius:8px; padding:1.2rem 1.5rem; margin-bottom:1rem;'>
    <b style='color:#E8E8F0; font-size:1.05rem;'>{q["question"]}</b></div>""", unsafe_allow_html=True)

    prev_answer = st.session_state.test_answers.get(idx)
    options = q.get("options", [])
    selected = st.radio(
        "Select your answer:",
        options,
        index=options.index(prev_answer) if prev_answer and prev_answer in options else 0,
        key=f"mock_radio_{idx}",
        label_visibility="collapsed",
    )
    st.session_state.test_answers[idx] = selected

    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
    with nav_col1:
        if idx > 0 and st.button("⬅️ Previous", use_container_width=True):
            st.session_state.test_current_idx -= 1
            st.rerun()
    with nav_col2:
        if idx < total - 1 and st.button("➡️ Next", use_container_width=True, type="primary"):
            st.session_state.test_current_idx += 1
            st.rerun()
    with nav_col3:
        if idx == total - 1:
            if st.button("🏁 Submit Test", use_container_width=True, type="primary"):
                st.session_state.test_active = False
                st.session_state.test_completed = True
                st.rerun()

    # Question navigator
    st.markdown("---")
    st.markdown("**Question Navigator:**")
    nav_cols = st.columns(10)
    for i in range(total):
        col = nav_cols[i % 10]
        answered = i in st.session_state.test_answers
        bg = "#4CAF50" if answered and i == idx else "#6C63FF" if i == idx else "#4CAF50" if answered else "#2D2D4A"
        if col.button(str(i + 1), key=f"nav_{i}", use_container_width=True):
            st.session_state.test_current_idx = i
            st.rerun()

# ── Results Screen ────────────────────────────────────────────────────────────
elif st.session_state.test_completed:
    questions = st.session_state.test_questions
    answers = st.session_state.test_answers
    total = len(questions)
    correct_count = 0
    topic_breakdown = {}

    for i, q in enumerate(questions):
        user_ans = answers.get(i)
        is_correct = user_ans is not None and user_ans[0] in q.get("correct", [])
        if is_correct:
            correct_count += 1
        t = q.get("topic", "General").split("(")[0].strip()
        if t not in topic_breakdown:
            topic_breakdown[t] = {"correct": 0, "total": 0}
        topic_breakdown[t]["total"] += 1
        if is_correct:
            topic_breakdown[t]["correct"] += 1

    pct = correct_count / total * 100 if total > 0 else 0
    save_test_result(correct_count, total, topic_breakdown)

    # Score banner
    banner_color = "#4CAF50" if pct >= 70 else "#FF9800" if pct >= 40 else "#F44336"
    st.markdown(f"""
    <div style='text-align:center; background:linear-gradient(135deg,{banner_color}33,{banner_color}11);
    border:2px solid {banner_color}; border-radius:16px; padding:2rem; margin-bottom:2rem;'>
    <h1 style='color:{banner_color}; font-size:3rem; margin:0;'>{correct_count}/{total}</h1>
    <h2 style='color:{banner_color}; margin:0.5rem 0;'>{pct:.1f}%</h2>
    <p style='color:#9CA3AF; margin:0;'>
    {"🏆 Excellent!" if pct >= 80 else "👍 Good job!" if pct >= 60 else "📚 Keep practicing!"}</p>
    </div>""", unsafe_allow_html=True)

    # Topic breakdown chart
    st.markdown("### 📊 Topic-wise Breakdown")
    if topic_breakdown:
        bd_data = {
            "Topic": list(topic_breakdown.keys()),
            "Correct": [v["correct"] for v in topic_breakdown.values()],
            "Total": [v["total"] for v in topic_breakdown.values()],
            "Percentage": [v["correct"] / v["total"] * 100 if v["total"] > 0 else 0 for v in topic_breakdown.values()],
        }
        df_bd = pd.DataFrame(bd_data)
        fig = px.bar(
            df_bd, x="Topic", y="Percentage",
            color="Percentage", color_continuous_scale=["#F44336", "#FF9800", "#4CAF50"],
            range_color=[0, 100], title="Score % by Topic",
            labels={"Percentage": "Score (%)"},
        )
        fig.update_layout(
            paper_bgcolor="#0E0E1A", plot_bgcolor="#1A1A2E",
            font_color="#E8E8F0", showlegend=False, coloraxis_showscale=False,
            xaxis=dict(tickangle=-30),
        )
        fig.add_hline(y=70, line_dash="dash", line_color="#6C63FF", annotation_text="70% target")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Detailed Breakdown:**")
        st.dataframe(df_bd[["Topic", "Correct", "Total", "Percentage"]].sort_values("Percentage"), use_container_width=True)

    # Review wrong answers
    st.markdown("### 🔍 Review Answers")
    for i, q in enumerate(questions):
        user_ans = answers.get(i, "Not answered")
        is_correct = user_ans is not None and user_ans[0] in q.get("correct", [])
        icon = "✅" if is_correct else "❌"
        with st.expander(f"{icon} Q{i+1}: {q['question'][:80]}..."):
            st.markdown(f"**Your answer:** {user_ans}")
            st.markdown(f"**Correct answer:** {', '.join(q.get('correct', []))}")
            st.markdown(f"**Explanation:** {q.get('explanation', 'N/A')}")

    if st.button("🔄 Start New Test", type="primary", use_container_width=True):
        init_test_state()
        st.rerun()
