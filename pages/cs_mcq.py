"""
cs_mcq.py — CS Core MCQs with 20-question batch queue system.
One API call generates 20 questions; user works through them one by one.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answer, get_topic_score, log_page_visit

log_page_visit("CS Core MCQs")

PAGE = "cs"
BATCH_SIZE = 20

TOPICS = {
    "📊 Data Structures & Algorithms": "Data Structures and Algorithms (GATE CSE): arrays, linked lists, stacks, queues, trees, graphs, heaps, hashing, sorting algorithms (quicksort, mergesort, heapsort), searching, dynamic programming, greedy algorithms, time/space complexity analysis",
    "🖥️ Operating Systems": "Operating Systems (GATE CSE): process scheduling (FCFS, SJF, Round Robin, Priority), memory management, paging, segmentation, virtual memory, deadlock detection and prevention, concurrency, semaphores, mutex, file systems, disk scheduling",
    "🗄️ Database Management Systems": "Database Management Systems (GATE CSE): ER model, relational model, relational algebra, SQL queries, joins, normalization (1NF-BCNF), transactions, ACID properties, concurrency control, locks, indexing, B-trees",
    "🌐 Computer Networks": "Computer Networks (GATE CSE): OSI model, TCP/IP stack, routing algorithms (Dijkstra, Bellman-Ford), IP addressing, subnetting, CIDR, TCP vs UDP, congestion control, DNS, HTTP/HTTPS, network security, ARP, ICMP",
    "⚙️ Compiler Design": "Compiler Design (GATE CSE): lexical analysis, finite automata, regular expressions, context-free grammars, parsing (LL, LR, SLR, LALR), syntax directed translation, intermediate code generation, optimization, code generation",
    "🔢 Theory of Computation": "Theory of Computation (GATE CSE): finite automata (DFA, NFA), regular languages, context-free languages, pushdown automata, Turing machines, decidability, NP-completeness, reductions",
    "💡 Digital Logic": "Digital Logic (GATE CSE): Boolean algebra, logic gates, Karnaugh maps, combinational circuits (adders, multiplexers, encoders), sequential circuits (flip-flops, counters, registers), state machines",
    "🧮 Discrete Mathematics": "Discrete Mathematics (GATE CSE): sets, relations, functions, propositional logic, predicate logic, graph theory, trees, combinatorics, probability, recurrence relations",
}

# ── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background:linear-gradient(90deg,#6C63FF,#06B6D4);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
💻 CS Core MCQs</h1>
<p style='color:#9CA3AF;'>GATE-style questions on DSA, OS, DBMS, Networks & more · 20 questions per set</p>
""", unsafe_allow_html=True)

if not is_api_configured():
    st.warning("⚠️ **Gemini API key not set.** Add key to `.streamlit/secrets.toml`")
    st.stop()

# ── Topic & Settings ───────────────────────────────────────────────────────────
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

# ── Sidebar Stats ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 Session Stats")
    score_data = get_topic_score(topic_label)
    correct_cnt = score_data["correct"]
    total_ans   = score_data["total"]
    if total_ans > 0:
        pct = correct_cnt / total_ans * 100
        st.metric("Correct", f"{correct_cnt}/{total_ans}", f"{pct:.0f}%")
        st.progress(correct_cnt / total_ans)
    else:
        st.info("No questions answered yet")
    st.markdown("---")
    st.metric("🔢 Unique Qs seen (all topics)", get_total_seen())
    if st.button("🗑️ Reset topic history", use_container_width=True):
        clear_topic_history(topic_label)
        st.success("Topic history cleared!")

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

# ── Detect settings change — reset queue ──────────────────────────────────────
if (st.session_state.get(TOPIC_KEY) != topic_label or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    st.session_state[Q_KEY] = []
    st.session_state[IDX_KEY] = 0
    st.session_state[ANSWERED_KEY] = False
    st.session_state[ANSWER_KEY] = None
    st.session_state[TOPIC_KEY] = topic_label
    st.session_state[DIFF_KEY] = difficulty
    st.session_state[TYPE_KEY] = q_type_val

# ── Generate Button + Progress ────────────────────────────────────────────────
st.markdown("---")

queue = _queue()

if not queue:
    # Show Generate button
    gen_col, _ = st.columns([2, 3])
    with gen_col:
        if st.button(f"🎯 Generate {BATCH_SIZE} Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} unique questions — one API call..."):
                qs, err = generate_mcq_set(topic, difficulty, q_type_val, count=BATCH_SIZE)
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state[Q_KEY] = qs
                st.session_state[IDX_KEY] = 0
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = None
                st.rerun()
    st.markdown("""<div style='text-align:center;color:#4B5563;padding:2rem;'>
    <p style='font-size:1.1rem;'>👆 Click to load 20 questions in one go</p>
    <p style='font-size:0.85rem;'>19× more token-efficient than generating one at a time</p>
    </div>""", unsafe_allow_html=True)
else:
    queue = _queue()
    idx   = _idx()
    total = len(queue)

    # Progress bar
    prog_pct = (idx) / total
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.8rem;'>
    <span style='color:#A78BFA;font-weight:700;font-size:1rem;white-space:nowrap;'>Q {idx+1} / {total}</span>
    <div style='flex:1;background:#2D2D4A;border-radius:4px;height:8px;'>
    <div style='background:linear-gradient(90deg,#6C63FF,#06B6D4);width:{prog_pct*100:.0f}%;height:8px;border-radius:4px;transition:width 0.3s;'></div>
    </div>
    <span style='color:#6B7280;font-size:0.82rem;white-space:nowrap;'>{topic_label[:25]}</span>
    </div>
    """, unsafe_allow_html=True)

    q = _current()
    if q is None:
        st.info("All questions completed!")
        if st.button("🔄 Generate New Set", type="primary"):
            st.session_state[Q_KEY] = []
            st.rerun()
    else:
        # Keyword tag
        st.markdown(
            f"<span style='background:#2D2D4A;color:#A78BFA;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>",
            unsafe_allow_html=True
        )
        st.markdown("")

        user_answer = render_question_card(q, key_prefix=f"{PAGE}_q{idx}")

        submit_col, next_col, reset_col, _ = st.columns([1, 1, 1, 2])

        with submit_col:
            if not st.session_state.get(ANSWERED_KEY, False):
                if st.button("✅ Submit", use_container_width=True, type="primary"):
                    if user_answer:
                        is_correct = render_feedback(q, user_answer)
                        h = get_question_hash(q["question"], q["correct"])
                        save_hash(topic_label, h, q.get("keyword", ""))
                        record_answer(topic_label, is_correct)
                        st.session_state[ANSWERED_KEY] = True
                        st.session_state[ANSWER_KEY] = user_answer
                    else:
                        st.warning("Please select an answer first.")
            else:
                render_feedback(q, st.session_state[ANSWER_KEY])

        with next_col:
            if st.session_state.get(ANSWERED_KEY, False):
                is_last = (idx >= total - 1)
                btn_label = "🔄 New Set" if is_last else f"Next → (Q{idx+2}/{total})"
                if st.button(btn_label, use_container_width=True):
                    if is_last:
                        st.session_state[Q_KEY] = []
                        st.session_state[IDX_KEY] = 0
                    else:
                        st.session_state[IDX_KEY] = idx + 1
                    st.session_state[ANSWERED_KEY] = False
                    st.session_state[ANSWER_KEY] = None
                    st.rerun()

        with reset_col:
            if st.button("⚡ New Set Now", use_container_width=True):
                st.session_state[Q_KEY] = []
                st.session_state[IDX_KEY] = 0
                st.session_state[ANSWERED_KEY] = False
                st.session_state[ANSWER_KEY] = None
                st.rerun()

# ── Score Summary ──────────────────────────────────────────────────────────────
s = get_topic_score(topic_label)
if s["total"] > 0:
    st.markdown("---")
    render_score_badge(s["correct"], s["total"])
