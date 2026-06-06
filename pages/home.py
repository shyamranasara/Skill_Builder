"""
home.py — Dashboard page shown as "Dashboard" in navigation.
"""

import json
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path
from utils.firebase_service import (
    get_overall_completion,
    get_test_history,
    get_all_scores,
    get_total_questions_today,
    get_streak,
    get_subject_completion,
    _init_state,
    log_page_visit,
)
from utils.question_hash import get_total_seen

_init_state()
log_page_visit("Dashboard")


@st.cache_data
def load_syllabus():
    path = Path(__file__).parent.parent / "data" / "gate_syllabus.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


syllabus = load_syllabus()
overall_pct = get_overall_completion(syllabus)

# ── Hero Section ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='background:linear-gradient(135deg,#0E0E1A 0%,#1A1A2E 50%,#16213E 100%);
border-radius:16px;padding:2.5rem 2rem;margin-bottom:1.5rem;
border:1px solid #2D2D4A;position:relative;overflow:hidden;'>
<div style='position:absolute;top:-50%;left:-50%;width:200%;height:200%;
background:radial-gradient(circle at 30% 30%,#6C63FF22 0%,transparent 50%),
radial-gradient(circle at 70% 70%,#06B6D422 0%,transparent 50%);'></div>
<h1 style='position:relative;z-index:1;font-size:2.5rem;margin:0;
background:linear-gradient(90deg,#6C63FF,#06B6D4,#EC4899);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
🎓 GATE & ML Job Prep</h1>
<p style='position:relative;z-index:1;color:#9CA3AF;font-size:1.1rem;margin:0.5rem 0 1rem;'>
Your AI-powered study companion · GATE CS 2024 · ML Engineering</p>
<div style='position:relative;z-index:1;display:flex;gap:1rem;flex-wrap:wrap;'>
<span style='background:#6C63FF22;color:#A78BFA;padding:6px 14px;border-radius:20px;font-size:0.85rem;border:1px solid #6C63FF44;'>🔮 Gemini 2.0 Flash</span>
<span style='background:#06B6D422;color:#67E8F9;padding:6px 14px;border-radius:20px;font-size:0.85rem;border:1px solid #06B6D444;'>♾️ Non-repeatable MCQs</span>
<span style='background:#EC489922;color:#F9A8D4;padding:6px 14px;border-radius:20px;font-size:0.85rem;border:1px solid #EC489944;'>🎤 Voice Interview Practice</span>
<span style='background:#10B98122;color:#6EE7B7;padding:6px 14px;border-radius:20px;font-size:0.85rem;border:1px solid #10B98144;'>📊 9 Study Sections</span>
</div></div>
""", unsafe_allow_html=True)

# ── Top Metrics ────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)

pct_color = "#4CAF50" if overall_pct >= 0.8 else "#FF9800" if overall_pct >= 0.4 else "#6C63FF"
with m1:
    st.markdown(f"""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:12px;padding:1.2rem;'>
    <p style='color:#9CA3AF;font-size:0.78rem;margin:0;'>SYLLABUS PROGRESS</p>
    <h2 style='color:{pct_color};margin:0.4rem 0;'>{overall_pct*100:.1f}%</h2>
    <div style='background:#2D2D4A;border-radius:3px;height:6px;'>
    <div style='background:{pct_color};width:{overall_pct*100:.1f}%;height:6px;border-radius:3px;'></div>
    </div></div>""", unsafe_allow_html=True)

with m2:
    today_q = get_total_questions_today()
    st.markdown(f"""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:12px;padding:1.2rem;'>
    <p style='color:#9CA3AF;font-size:0.78rem;margin:0;'>TODAY'S QUESTIONS</p>
    <h2 style='color:#06B6D4;margin:0.4rem 0;'>{today_q}</h2>
    <p style='color:#4B5563;font-size:0.8rem;margin:0;'>answered today</p></div>""", unsafe_allow_html=True)

with m3:
    streak = get_streak()
    st.markdown(f"""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:12px;padding:1.2rem;'>
    <p style='color:#9CA3AF;font-size:0.78rem;margin:0;'>STREAK</p>
    <h2 style='color:#F59E0B;margin:0.4rem 0;'>🔥 {streak}</h2>
    <p style='color:#4B5563;font-size:0.8rem;margin:0;'>consecutive days</p></div>""", unsafe_allow_html=True)

with m4:
    history = get_test_history()
    best = max([h["percentage"] for h in history], default=0)
    st.markdown(f"""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:12px;padding:1.2rem;'>
    <p style='color:#9CA3AF;font-size:0.78rem;margin:0;'>BEST MOCK SCORE</p>
    <h2 style='color:#EC4899;margin:0.4rem 0;'>{best:.0f}%</h2>
    <p style='color:#4B5563;font-size:0.8rem;margin:0;'>{len(history)} tests taken</p></div>""", unsafe_allow_html=True)

st.markdown("")

# ── Charts ─────────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("#### 📚 Syllabus Coverage")
    subjects, percentages = [], []
    for subject, data in syllabus.items():
        topics = data.get("topics", data.get("subtopics", []))
        pct = get_subject_completion(subject, len(topics)) * 100
        subjects.append(subject[:22])
        percentages.append(pct)

    fig = go.Figure(go.Bar(
        x=percentages, y=subjects, orientation="h",
        marker=dict(color=percentages, colorscale=[[0,"#6C63FF"],[0.4,"#FF9800"],[1,"#4CAF50"]], cmin=0, cmax=100),
        text=[f"{p:.0f}%" for p in percentages], textposition="outside",
    ))
    fig.update_layout(paper_bgcolor="#0E0E1A", plot_bgcolor="#1A1A2E", font_color="#E8E8F0", height=340,
        xaxis=dict(range=[0,115], showgrid=False), yaxis=dict(showgrid=False),
        margin=dict(l=10, r=60, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with chart_col2:
    st.markdown("#### 🎯 Mock Test Score History")
    if history:
        df = pd.DataFrame(history)
        fig2 = px.line(df, x="timestamp", y="percentage", markers=True, line_shape="spline",
            labels={"percentage":"Score (%)","timestamp":""}, color_discrete_sequence=["#6C63FF"])
        fig2.update_layout(paper_bgcolor="#0E0E1A", plot_bgcolor="#1A1A2E", font_color="#E8E8F0", height=340,
            xaxis=dict(showgrid=False, tickangle=-30), yaxis=dict(range=[0,100], gridcolor="#2D2D4A"),
            margin=dict(l=10, r=10, t=10, b=10))
        fig2.add_hline(y=70, line_dash="dash", line_color="#F59E0B",
            annotation_text="70% target", annotation_font_color="#F59E0B")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown("""<div style='height:340px;display:flex;align-items:center;justify-content:center;
        background:linear-gradient(135deg,#1A1A2E,#16213E);border-radius:12px;border:1px solid #2D2D4A;'>
        <div style='text-align:center;color:#4B5563;'>
        <p style='font-size:2.5rem;margin:0;'>🎯</p>
        <p style='margin:0.5rem 0 0;'>Take a mock test to see your score trend</p>
        </div></div>""", unsafe_allow_html=True)

# ── Session Performance ────────────────────────────────────────────────────────
all_scores = get_all_scores()
if all_scores:
    st.markdown("---")
    st.markdown("#### 📊 Session Performance by Topic")
    score_data = {
        "Topic": list(all_scores.keys()),
        "Score%": [v["correct"]/v["total"]*100 if v["total"]>0 else 0 for v in all_scores.values()],
    }
    df_s = pd.DataFrame(score_data)
    fig3 = px.bar(df_s, x="Topic", y="Score%", color="Score%",
        color_continuous_scale=["#F44336","#FF9800","#4CAF50"], range_color=[0,100], text_auto=".0f")
    fig3.update_layout(paper_bgcolor="#0E0E1A", plot_bgcolor="#1A1A2E", font_color="#E8E8F0",
        coloraxis_showscale=False, xaxis=dict(tickangle=-30), height=260,
        margin=dict(l=0, r=0, t=10, b=0))
    fig3.add_hline(y=70, line_dash="dash", line_color="#6C63FF")
    st.plotly_chart(fig3, use_container_width=True)

# ── Quick Start (real clickable buttons) ───────────────────────────────────────
st.markdown("---")
st.markdown("### 🚀 Quick Start")

# Row 1
row1 = st.columns(4)

with row1[0]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #6C63FF;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>📚</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Syllabus Tracker</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Track GATE CS topics</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_syllabus", use_container_width=True):
        st.switch_page("pages/syllabus_tracker.py")

with row1[1]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #06B6D4;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>💻</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>CS Core MCQs</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>DSA · OS · DBMS · CN</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_cs", use_container_width=True):
        st.switch_page("pages/cs_mcq.py")

with row1[2]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #F59E0B;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>🧮</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Aptitude Questions</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Quant & Reasoning</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_apt", use_container_width=True):
        st.switch_page("pages/aptitude_mcq.py")

with row1[3]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #10B981;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>📝</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>English MCQs</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Grammar · Vocabulary</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_eng", use_container_width=True):
        st.switch_page("pages/english_mcq.py")

# Row 2
st.markdown("")
row2 = st.columns(4)

with row2[0]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #EC4899;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>🤖</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>ML Engineering MCQs</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Transformers · MLOps</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_ml", use_container_width=True):
        st.switch_page("pages/ml_mcq.py")

with row2[1]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #F59E0B;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>☕</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Java & Spring Boot</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Spring · Hibernate · Microservices</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_java", use_container_width=True):
        st.switch_page("pages/java_mcq.py")

with row2[2]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #EF4444;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>🎯</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Mock Test</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Timed 30-question test</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_mock", use_container_width=True):
        st.switch_page("pages/mock_test.py")

with row2[3]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #3B82F6;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>📖</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Study Guide</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>AI explanation + chat</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_study", use_container_width=True):
        st.switch_page("pages/study_guide.py")

st.markdown("")
row3 = st.columns(4)
with row3[0]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #8B5CF6;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>🎤</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Communication Practice</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Voice interview + AI</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_comm", use_container_width=True):
        st.switch_page("pages/communication.py")

with row3[1]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #EF4444;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>📊</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>CP Theory MCQs</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Contest theory & patterns</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_cp_mcq", use_container_width=True):
        st.switch_page("pages/competitive_mcq.py")

with row3[2]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #10B981;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>💻</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Coding Ground</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>Solve coding challenges</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_coding_ground", use_container_width=True):
        st.switch_page("pages/coding_ground.py")

with row3[3]:
    st.markdown("""<div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:3px solid #8B5CF6;border-radius:12px;padding:0.9rem 1rem 0.3rem;margin-bottom:0.3rem;'>
    <p style='margin:0;font-size:1.3rem;'>🏛️</p>
    <p style='margin:0.2rem 0 0;color:#E8E8F0;font-weight:600;font-size:0.9rem;'>Govt Exam MCQs</p>
    <p style='margin:0;color:#6B7280;font-size:0.75rem;'>UPSC · SSC · Bank · Police</p></div>""",
    unsafe_allow_html=True)
    if st.button("Open →", key="qs_govt_mcq", use_container_width=True):
        st.switch_page("pages/govt_mcq.py")


st.markdown("""<div style='text-align:center;color:#4B5563;font-size:0.78rem;padding:1.5rem 0 0.5rem;'>
🎓 GATE & ML Job Prep · Gemini 2.0 Flash · $0/month · 100% Python
</div>""", unsafe_allow_html=True)
