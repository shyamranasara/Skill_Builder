"""
study_guide.py — AI-powered study guide with Gemini explanations + chat follow-up.
"""

import streamlit as st
from utils.gemini_service import generate_explanation, get_chat_response, is_api_configured
from utils.firebase_service import log_page_visit

log_page_visit("Study Guide")



st.markdown("""
<h1 style='font-size:2.2rem; background: linear-gradient(90deg, #06B6D4, #3B82F6);
-webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
📖 AI Study Guide</h1>
<p style='color:#9CA3AF;'>Enter any topic → Get a complete explanation → Ask follow-up questions</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add your key to `.env` and restart.")
    st.stop()

# ── Quick-access topics ───────────────────────────────────────────────────────
QUICK_TOPICS = [
    "Virtual Memory", "Deadlock", "B+ Trees", "TCP vs UDP",
    "Normalization (DBMS)", "AVL Trees", "Attention Mechanism",
    "Gradient Descent", "LoRA Fine-tuning", "NP-Completeness",
    "Paging vs Segmentation", "SQL Joins", "BERT vs GPT",
    "Backpropagation", "RLHF",
]

st.markdown("**⚡ Quick Topics:**")
quick_cols = st.columns(5)
for i, qt in enumerate(QUICK_TOPICS):
    if quick_cols[i % 5].button(qt, key=f"quick_{i}", use_container_width=True):
        st.session_state["guide_topic_input"] = qt
        st.session_state["guide_explanation"] = None
        st.session_state["guide_chat_history"] = []

# ── Topic Input ───────────────────────────────────────────────────────────────
st.markdown("---")
topic_input = st.text_input(
    "🔍 Enter a topic to explain:",
    value=st.session_state.get("guide_topic_input", ""),
    placeholder="e.g., Virtual Memory, Gradient Descent, LoRA, SQL Joins...",
    key="guide_topic_field",
)

explain_col, clear_col, _ = st.columns([1, 1, 4])
with explain_col:
    explain_clicked = st.button("📖 Explain this topic", type="primary", use_container_width=True)
with clear_col:
    if st.button("🗑️ Clear", use_container_width=True):
        st.session_state["guide_explanation"] = None
        st.session_state["guide_chat_history"] = []
        st.session_state["guide_topic_input"] = ""
        st.rerun()

if explain_clicked and topic_input.strip():
    st.session_state["guide_topic_input"] = topic_input.strip()
    with st.spinner(f"Generating explanation for **{topic_input}**..."):
        explanation, err = generate_explanation(topic_input.strip())
    if err:
        st.error(err)
    else:
        st.session_state["guide_explanation"] = explanation
        st.session_state["guide_chat_history"] = []
        # Pre-load chat history with context
        st.session_state["_guide_gemini_history"] = [
            {
                "role": "user",
                "parts": [f"Please explain the topic: {topic_input.strip()}"],
            },
            {
                "role": "model",
                "parts": [explanation],
            },
        ]

# ── Explanation Display ───────────────────────────────────────────────────────
if st.session_state.get("guide_explanation"):
    topic_name = st.session_state.get("guide_topic_input", "")
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border-top:3px solid #06B6D4; border-radius:12px; padding:1.5rem 2rem; margin:1rem 0;'>
    <h3 style='color:#06B6D4; margin-top:0;'>📚 {topic_name}</h3>
    </div>""", unsafe_allow_html=True)
    
    st.markdown(st.session_state["guide_explanation"])

    # Download button
    st.download_button(
        "⬇️ Download explanation",
        st.session_state["guide_explanation"],
        file_name=f"{topic_name.replace(' ', '_')}_notes.md",
        mime="text/markdown",
    )

    # ── Chat Follow-up ────────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 💬 Ask Follow-up Questions")

    # Render chat history
    chat_history = st.session_state.get("guide_chat_history", [])
    for msg in chat_history:
        with st.chat_message(msg["role"], avatar="🧑‍💻" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])

    # Chat input
    user_q = st.chat_input(f"Ask anything about {topic_name}...")
    if user_q:
        # Show user message
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_q)
        chat_history.append({"role": "user", "content": user_q})

        # Get Gemini response
        gemini_history = st.session_state.get("_guide_gemini_history", [])
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                response, err = get_chat_response(gemini_history, user_q)
            if err:
                st.error(err)
            else:
                st.markdown(response)
                chat_history.append({"role": "assistant", "content": response})
                # Update Gemini history
                gemini_history.append({"role": "user", "parts": [user_q]})
                gemini_history.append({"role": "model", "parts": [response]})
                st.session_state["_guide_gemini_history"] = gemini_history

        st.session_state["guide_chat_history"] = chat_history

elif not st.session_state.get("guide_topic_input"):
    # Welcome state
    st.markdown("---")
    st.markdown("""
    <div style='text-align:center; padding:3rem; color:#4B5563;'>
    <h3>👆 Enter a topic above to get started</h3>
    <p>You can ask about any CS or ML concept — get full explanations with GATE exam angles,
    common mistakes, and examples. Then follow up with any questions in the chat.</p>
    </div>""", unsafe_allow_html=True)
