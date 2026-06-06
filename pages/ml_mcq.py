"""
ml_mcq.py — ML Engineering MCQs with 20-question batch queue.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answer, get_topic_score, log_page_visit

log_page_visit("ML Engineering MCQs")

PAGE = "ml"
BATCH_SIZE = 20

TOPICS = {
    "🤖 ML Fundamentals": "Machine Learning fundamentals for ML engineer interviews: supervised learning, unsupervised learning, reinforcement learning, bias-variance tradeoff, overfitting, regularization (L1/L2), cross-validation, evaluation metrics (precision, recall, F1, AUC-ROC), feature engineering, feature selection",
    "🧠 Deep Learning & Neural Nets": "Deep Learning for ML engineer interviews: feedforward networks, backpropagation, activation functions (ReLU, sigmoid, tanh, GELU), batch normalization, dropout, convolutional neural networks, recurrent networks (LSTM, GRU), attention mechanism, residual connections",
    "🔮 Transformers & LLMs": "Transformer architecture and Large Language Models for ML engineers: self-attention, multi-head attention, positional encoding, BERT, GPT, T5, fine-tuning vs prompting, tokenization, embeddings, RAG (retrieval augmented generation), RLHF, LoRA and PEFT methods",
    "⚙️ MLOps & Production": "MLOps for ML engineer interviews: model versioning, experiment tracking (MLflow, W&B), CI/CD for ML, model monitoring, data drift, concept drift, feature stores, model serving (TorchServe, TFServing, Triton), containerization with Docker, Kubernetes for ML workloads",
    "📊 Data Engineering for ML": "Data engineering concepts for ML engineers: data pipelines, ETL vs ELT, Apache Spark, distributed computing, SQL for ML, NoSQL databases, data versioning (DVC), vector databases (Pinecone, Weaviate, Faiss), streaming data (Kafka, Flink)",
    "🐍 Python for ML": "Python for ML engineering interviews: NumPy, Pandas, Scikit-learn APIs, PyTorch tensors and autograd, TensorFlow/Keras, vectorization vs loops, memory efficiency, Python decorators and generators for ML, multiprocessing for data loading",
}

st.markdown("""
<h1 style='font-size:2.2rem; background:linear-gradient(90deg,#8B5CF6,#EC4899);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
🤖 ML Engineering MCQs</h1>
<p style='color:#9CA3AF;'>Transformers, MLOps, Deep Learning & Production ML · 20 questions per set</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add key to `.streamlit/secrets.toml`")
    st.stop()

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    topic_label = st.selectbox("📌 Topic", list(TOPICS.keys()), key=f"{PAGE}_topic")
    topic = TOPICS[topic_label]
with col2:
    difficulty = st.select_slider(
        "🎯 Difficulty", options=["easy", "medium", "hard"], value="medium", key=f"{PAGE}_diff"
    )
with col3:
    q_type = st.radio("Type", ["Single", "Multi"], key=f"{PAGE}_qtype", horizontal=True)
    q_type_val = "single" if q_type == "Single" else "multi"

with st.sidebar:
    st.markdown("### 📊 Session Stats")
    s = get_topic_score(topic_label)
    if s["total"] > 0:
        st.metric("Correct", f"{s['correct']}/{s['total']}", f"{s['correct']/s['total']*100:.0f}%")
        st.progress(s["correct"] / s["total"])
    else:
        st.info("No questions answered yet")
    st.markdown("---")
    st.metric("🔢 Unique Qs seen", get_total_seen())
    if st.button("🗑️ Reset topic history", use_container_width=True):
        clear_topic_history(topic_label)
        st.success("Cleared!")

Q_KEY = f"{PAGE}_queue"; IDX_KEY = f"{PAGE}_idx"; ANSWERED_KEY = f"{PAGE}_answered"
ANSWER_KEY = f"{PAGE}_user_ans"; TOPIC_KEY = f"{PAGE}_ltopic"; DIFF_KEY = f"{PAGE}_ldiff"; TYPE_KEY = f"{PAGE}_ltype"

def _queue():   return st.session_state.get(Q_KEY, [])
def _idx():     return st.session_state.get(IDX_KEY, 0)
def _current(): q = _queue(); i = _idx(); return q[i] if q and i < len(q) else None

if (st.session_state.get(TOPIC_KEY) != topic_label or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    for k in [Q_KEY, IDX_KEY, ANSWERED_KEY, ANSWER_KEY]:
        st.session_state.pop(k, None)
    st.session_state.update({TOPIC_KEY: topic_label, DIFF_KEY: difficulty, TYPE_KEY: q_type_val})

st.markdown("---")
queue = _queue()

if not queue:
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"🎯 Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} ML questions..."):
                qs, err = generate_mcq_set(topic, difficulty, q_type_val, count=BATCH_SIZE)
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({Q_KEY: qs, IDX_KEY: 0, ANSWERED_KEY: False, ANSWER_KEY: None})
                st.rerun()
    st.markdown("<div style='text-align:center;color:#4B5563;padding:2rem;'><p style='font-size:1.1rem;'>👆 Click to load 20 questions</p></div>", unsafe_allow_html=True)
else:
    idx = _idx(); total = len(queue)
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.8rem;'>
    <span style='color:#8B5CF6;font-weight:700;font-size:1rem;'>Q {idx+1} / {total}</span>
    <div style='flex:1;background:#2D2D4A;border-radius:4px;height:8px;'>
    <div style='background:linear-gradient(90deg,#8B5CF6,#EC4899);width:{idx/total*100:.0f}%;height:8px;border-radius:4px;'></div>
    </div>
    <span style='color:#6B7280;font-size:0.82rem;'>{topic_label[:25]}</span>
    </div>""", unsafe_allow_html=True)

    q = _current()
    if q is None:
        st.info("✅ All questions completed!")
        if st.button("🔄 Generate New Set", type="primary"):
            st.session_state[Q_KEY] = []; st.rerun()
    else:
        st.markdown(f"<span style='background:#2D2D4A;color:#8B5CF6;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
        st.markdown("")
        user_answer = render_question_card(q, key_prefix=f"{PAGE}_q{idx}")

        c1, c2, c3, _ = st.columns([1, 1, 1, 2])
        with c1:
            if not st.session_state.get(ANSWERED_KEY, False):
                if st.button("✅ Submit", use_container_width=True, type="primary"):
                    if user_answer:
                        is_correct = render_feedback(q, user_answer)
                        save_hash(topic_label, get_question_hash(q["question"], q["correct"]), q.get("keyword", ""))
                        record_answer(topic_label, is_correct)
                        st.session_state.update({ANSWERED_KEY: True, ANSWER_KEY: user_answer})
                    else:
                        st.warning("Please select an answer first.")
            else:
                render_feedback(q, st.session_state[ANSWER_KEY])

        with c2:
            if st.session_state.get(ANSWERED_KEY, False):
                is_last = idx >= total - 1
                if st.button("🔄 New Set" if is_last else f"Next → Q{idx+2}/{total}", use_container_width=True):
                    if is_last:
                        st.session_state[Q_KEY] = []; st.session_state[IDX_KEY] = 0
                    else:
                        st.session_state[IDX_KEY] = idx + 1
                    st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None})
                    st.rerun()

        with c3:
            if st.button("⚡ New Set Now", use_container_width=True):
                st.session_state[Q_KEY] = []; st.session_state[IDX_KEY] = 0
                st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None}); st.rerun()

s = get_topic_score(topic_label)
if s["total"] > 0:
    st.markdown("---"); render_score_badge(s["correct"], s["total"])
