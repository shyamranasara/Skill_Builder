"""
ml_mcq.py — ML Engineering MCQs with 20-question batch queue.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answers_batch, get_topic_score, log_page_visit

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

Q_KEY = f"{PAGE}_queue"; ANSWERED_KEY = f"{PAGE}_answered"
ANSWER_KEY = f"{PAGE}_user_ans"; TOPIC_KEY = f"{PAGE}_ltopic"; DIFF_KEY = f"{PAGE}_ldiff"; TYPE_KEY = f"{PAGE}_ltype"

def _queue():   return st.session_state.get(Q_KEY, [])

if (st.session_state.get(TOPIC_KEY) != topic_label or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    for k in [Q_KEY, ANSWERED_KEY, ANSWER_KEY]:
        st.session_state.pop(k, None)
    st.session_state.update({TOPIC_KEY: topic_label, DIFF_KEY: difficulty, TYPE_KEY: q_type_val})

st.markdown("---")
queue = _queue()

if not queue:
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"🎯 Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} questions..."):
                qs, err = generate_mcq_set(topic, difficulty, q_type_val, count=BATCH_SIZE)
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({Q_KEY: qs, ANSWERED_KEY: False, ANSWER_KEY: {}})
                st.rerun()
    st.markdown("<div style='text-align:center;color:#4B5563;padding:2rem;'><p style='font-size:1.1rem;'>👆 Click to load 20 questions</p></div>", unsafe_allow_html=True)
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
                    save_hash(topic_label, h, q.get("keyword", ""))
                
                record_answers_batch(topic_label, results)
                
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
