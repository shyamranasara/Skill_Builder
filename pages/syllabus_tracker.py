"""
syllabus_tracker.py — Syllabus Tracker with progress tracking for GATE CSE & Government Exams.
"""

import json
import streamlit as st
from pathlib import Path
from utils.firebase_service import (
    save_syllabus_progress,
    get_syllabus_progress,
    get_subject_completion,
    get_overall_completion,
    log_page_visit,
)

# ── Track Telemetry ─────────────────────────────────────────────────────────
log_page_visit("Syllabus Tracker")

# ── Load syllabus data ──────────────────────────────────────────────────────
@st.cache_data
def load_gate_syllabus():
    path = Path(__file__).parent.parent / "data" / "gate_syllabus.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_govt_syllabus():
    path = Path(__file__).parent.parent / "data" / "govt_syllabus.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ── Selector for Exam ────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background: linear-gradient(90deg, #6C63FF, #A78BFA);
-webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0.2rem;'>
📚 Syllabus Tracker</h1>
<p style='color:#9CA3AF; margin-top:0;'>Track your preparation across GATE CSE & Government Exams</p>
""", unsafe_allow_html=True)

exam_options = [
    "🎓 GATE CSE",
    "🏛️ UPSC CSE (Civil Services)",
    "💳 Bank Exams (IBPS / SBI PO & Clerk)",
    "💼 SSC CGL Exam",
    "👮 State Police SI & Constable"
]

selected_exam = st.selectbox("Select Exam Syllabus:", exam_options, key="syllabus_selected_exam")

# Load correct syllabus based on selection
if selected_exam == "🎓 GATE CSE":
    syllabus = load_gate_syllabus()
    exam_prefix = "GATE_CSE"
else:
    govt_data = load_govt_syllabus()
    syllabus = govt_data.get(selected_exam, {})
    # Map selection name to prefix for database consistency
    exam_prefix = selected_exam.split(" ", 1)[-1].strip()

saved_progress = get_syllabus_progress()
overall_pct = get_overall_completion(syllabus, exam_prefix=exam_prefix)

# ── Overall Progress ─────────────────────────────────────────────────────────
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    color = "#4CAF50" if overall_pct >= 0.8 else "#FF9800" if overall_pct >= 0.4 else "#6C63FF"
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E); border-radius:12px;
    padding:1.2rem 1.5rem; border:1px solid #2D2D4A;'>
    <p style='color:#9CA3AF; margin:0; font-size:0.85rem;'>{selected_exam.upper()} OVERALL PROGRESS</p>
    <h2 style='color:{color}; margin:0.3rem 0;'>{overall_pct*100:.1f}%</h2>
    <div style='background:#2D2D4A; border-radius:4px; height:8px; margin-top:0.5rem;'>
    <div style='background:{color}; width:{overall_pct*100:.1f}%; height:8px; border-radius:4px;'></div>
    </div></div>
    """, unsafe_allow_html=True)

with col2:
    total_topics = sum(len(v.get("topics", v.get("subtopics", []))) for v in syllabus.values())
    done_topics = int(overall_pct * total_topics)
    st.metric("✅ Topics Completed", f"{done_topics}/{total_topics}")

with col3:
    remaining = total_topics - done_topics
    st.metric("📌 Remaining", remaining)

st.markdown("---")

# ── Controls ─────────────────────────────────────────────────────────────────
ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 2])
with ctrl_col1:
    if st.button("✅ Expand All", use_container_width=True):
        st.session_state["expand_all"] = True
with ctrl_col2:
    if st.button("📦 Collapse All", use_container_width=True):
        st.session_state["expand_all"] = False

# Filter
with ctrl_col3:
    filter_opt = st.selectbox(
        "Show:",
        ["All topics", "Incomplete only", "Completed only"],
        key="syllabus_filter",
        label_visibility="collapsed",
    )

st.markdown("---")

# ── Subject Sections ──────────────────────────────────────────────────────────
for subject, data in syllabus.items():
    icon = data.get("icon", "📘")
    topics = data.get("topics", data.get("subtopics", []))
    
    # Use composite key for exam
    subj_key = f"{exam_prefix}::{subject}"
    subj_progress = saved_progress.get(subj_key, {})
    done_count = sum(1 for t in topics if subj_progress.get(t, False))
    subj_pct = (done_count / len(topics) * 100) if topics else 0

    # Progress color
    bar_color = "#4CAF50" if subj_pct >= 80 else "#FF9800" if subj_pct >= 40 else "#F44336"

    expand_default = st.session_state.get("expand_all", False)
    with st.expander(f"{icon} {subject}  —  {done_count}/{len(topics)} topics ({subj_pct:.0f}%)", expanded=expand_default):
        # Mini progress bar
        st.markdown(f"""
        <div style='background:#2D2D4A; border-radius:4px; height:6px; margin-bottom:1rem;'>
        <div style='background:{bar_color}; width:{subj_pct:.1f}%; height:6px; border-radius:4px;'></div>
        </div>""", unsafe_allow_html=True)

        cols = st.columns(2)
        for i, topic in enumerate(topics):
            # Apply filter
            is_done = subj_progress.get(topic, False)
            if filter_opt == "Incomplete only" and is_done:
                continue
            if filter_opt == "Completed only" and not is_done:
                continue

            col = cols[i % 2]
            with col:
                checked = col.checkbox(
                    topic,
                    value=is_done,
                    key=f"syllabus_{exam_prefix}_{subject}_{i}",
                )
                if checked != is_done:
                    save_syllabus_progress(subj_key, topic, checked)
                    st.rerun()

        # Mark all / Clear all buttons
        btn_col1, btn_col2, _ = st.columns([1, 1, 3])
        with btn_col1:
            if st.button("✅ Mark all done", key=f"all_{exam_prefix}_{subject}"):
                for t in topics:
                    save_syllabus_progress(subj_key, t, True)
                st.rerun()
        with btn_col2:
            if st.button("🔄 Reset", key=f"reset_{exam_prefix}_{subject}"):
                for t in topics:
                    save_syllabus_progress(subj_key, t, False)
                st.rerun()

# ── Footer note ──────────────────────────────────────────────────────────────
st.info("🔒 Progress is saved to your Firebase profile and syncs across all devices.")
