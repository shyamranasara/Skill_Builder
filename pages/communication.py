"""
communication.py — AI-powered voice interview practice with Gemini audio analysis.
"""

import streamlit as st
from utils.gemini_service import get_interview_question, analyze_audio_answer, is_api_configured
from utils.firebase_service import save_communication_session, get_communication_sessions, log_page_visit

log_page_visit("Communication Practice")



st.markdown("""
<h1 style='font-size:2.2rem; background: linear-gradient(90deg, #EC4899, #8B5CF6);
-webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
🎤 Communication Practice</h1>
<p style='color:#9CA3AF;'>AI interview questions · Record your answer · Get structured feedback</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add your key to `.env` and restart.")
    st.stop()

# ── Audio recorder import (graceful fail) ─────────────────────────────────────
try:
    from audio_recorder_streamlit import audio_recorder
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# ── Settings ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    domain = st.selectbox(
        "🎯 Interview Domain",
        ["ML Engineering", "Software Engineering", "Data Science", "CS Fundamentals", "HR & Behavioral"],
        key="comm_domain",
    )
with col2:
    difficulty = st.select_slider("💪 Difficulty", ["easy", "medium", "hard"], value="medium", key="comm_diff")

# ── Sidebar: Session Report ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 Session Report")
    sessions = get_communication_sessions()
    if sessions:
        total_sessions = len(sessions)
        scores = [s["score"] for s in sessions if s["score"] is not None]
        avg_score = sum(scores) / len(scores) if scores else 0
        st.metric("Questions Practiced", total_sessions)
        st.metric("Avg Score", f"{avg_score:.1f}/10" if scores else "N/A")

        with st.expander(f"📜 All Sessions ({total_sessions})", expanded=False):
            for i, s in enumerate(reversed(sessions[-10:])):
                st.markdown(f"""
                **Q{total_sessions - i}:** {s['question'][:60]}...
                **Score:** {s['score']}/10 · *{s['timestamp']}*
                """)
    else:
        st.info("No practice sessions yet.\nStart recording to build your report!")

    if sessions and st.button("⬇️ Download Report", use_container_width=True):
        report = "\n\n".join([
            f"Session {i+1} [{s['timestamp']}]\nQuestion: {s['question']}\n\nFeedback:\n{s['feedback']}\n{'─'*60}"
            for i, s in enumerate(sessions)
        ])
        st.download_button("Download", report, "communication_report.txt", mime="text/plain")

# ── Get Interview Question ────────────────────────────────────────────────────
st.markdown("---")
if st.button("🎲 Get Interview Question", type="primary", use_container_width=False):
    with st.spinner("Generating interview question..."):
        question, err = get_interview_question(domain, difficulty)
    if err:
        st.error(err)
    elif question:
        st.session_state["comm_question"] = question
        st.session_state["comm_feedback"] = None
        st.session_state["comm_audio"] = None

# ── Display Question ──────────────────────────────────────────────────────────
if "comm_question" in st.session_state and st.session_state["comm_question"]:
    question = st.session_state["comm_question"]
    
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-left:4px solid #EC4899; border-radius:10px; padding:1.5rem; margin:1rem 0;'>
    <p style='color:#9CA3AF; font-size:0.85rem; margin:0 0 0.5rem 0;'>🎯 INTERVIEW QUESTION</p>
    <p style='color:#E8E8F0; font-size:1.15rem; font-weight:600; margin:0; line-height:1.6;'>
    {question}</p>
    </div>""", unsafe_allow_html=True)

    # ── Voice Recording ────────────────────────────────────────────────────────
    st.markdown("### 🎙️ Record Your Answer")

    if AUDIO_AVAILABLE:
        st.info("💡 Click the microphone button below to start recording. Click again to stop.")
        audio_bytes = audio_recorder(
            text="",
            recording_color="#EC4899",
            neutral_color="#6C63FF",
            icon_size="3x",
            key="comm_recorder",
        )

        if audio_bytes and audio_bytes != st.session_state.get("comm_audio"):
            st.session_state["comm_audio"] = audio_bytes
            st.audio(audio_bytes, format="audio/wav")
            
            with st.spinner("Analyzing your response with Gemini..."):
                feedback, err = analyze_audio_answer(question, audio_bytes, "audio/wav")
            
            if err:
                st.error(f"Analysis failed: {err}")
            elif feedback:
                st.session_state["comm_feedback"] = feedback
                # Extract score (look for "X/10" pattern)
                import re
                score_match = re.search(r"(\d+(?:\.\d+)?)/10", feedback)
                score = float(score_match.group(1)) if score_match else None
                save_communication_session(question, feedback, score)
    else:
        # Fallback: text input for practice without microphone
        st.warning("🎙️ `audio-recorder-streamlit` package not installed. Using text input as fallback.")
        st.markdown("*Install with: `pip install audio-recorder-streamlit`*")
        text_answer = st.text_area(
            "Type your answer (text mode):",
            placeholder="Type your answer here for text-based feedback...",
            height=150,
            key="comm_text_answer",
        )
        if st.button("📊 Get Feedback on Text Answer", type="primary"):
            if text_answer.strip():
                # Use Gemini to analyze text instead of audio
                from utils.gemini_service import get_client, MODEL_ID
                client = get_client()
                if client:
                    with st.spinner("Analyzing your text answer..."):
                        text_prompt = f"""You are an interview coach. Analyze this text answer:
Question: {question}
Candidate's Answer: {text_answer}

Provide structured feedback on Content, Grammar, Structure, and Vocabulary.
Give an Overall Score out of 10."""
                        try:
                            result = client.models.generate_content(model=MODEL_ID, contents=text_prompt)
                            feedback = result.text
                            st.session_state["comm_feedback"] = feedback
                            import re
                            score_match = re.search(r"(\d+(?:\.\d+)?)/10", feedback)
                            score = float(score_match.group(1)) if score_match else None
                            save_communication_session(question, feedback, score)
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ── Feedback Display ───────────────────────────────────────────────────────
    if st.session_state.get("comm_feedback"):
        st.markdown("---")
        st.markdown("### 📊 AI Feedback")
        st.markdown(st.session_state["comm_feedback"])

        # Next question button
        col_next, _ = st.columns([1, 3])
        with col_next:
            if st.button("🔄 Next Question", use_container_width=True, type="primary"):
                with st.spinner("Getting new question..."):
                    new_q, err = get_interview_question(domain, difficulty)
                if err:
                    st.error(err)
                else:
                    st.session_state["comm_question"] = new_q
                    st.session_state["comm_feedback"] = None
                    st.session_state["comm_audio"] = None
                    st.rerun()

elif "comm_question" not in st.session_state:
    # Welcome state
    st.markdown("""
    <div style='text-align:center; padding:3rem; color:#4B5563;'>
    <h3>🎤 Ready to Practice?</h3>
    <p>Click <b>Get Interview Question</b> above to start.<br>
    Record your spoken answer and get AI-powered feedback on your<br>
    content accuracy, fluency, grammar, and vocabulary.</p>
    <br>
    <p style='font-size:0.85rem;'>Works best in Chrome or Edge browser.</p>
    </div>""", unsafe_allow_html=True)

# ── Tips ───────────────────────────────────────────────────────────────────────
with st.expander("💡 Tips for effective practice"):
    st.markdown("""
    - **Structure your answer**: Use STAR method (Situation, Task, Action, Result) for behavioral questions
    - **Technical questions**: Start with the definition, then give an example
    - **Speak clearly**: Don't rush — quality over speed
    - **Record multiple times**: Each attempt builds confidence
    - **Review the feedback**: Focus on the "Areas to improve" section each time
    - **Browser tip**: Use Chrome or Edge for best microphone support
    """)
