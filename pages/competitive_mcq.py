"""
competitive_mcq.py — Competitive Programming MCQs with 20-question batch queue.
Covers DSA contest topics, algorithm analysis, problem-solving patterns.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answers_batch, get_topic_score, log_page_visit

log_page_visit("CP Theory MCQs")

PAGE = "cp_mcq"
BATCH_SIZE = 20

TOPICS = {
    "🔄 Arrays & Strings": "Competitive programming arrays and strings: two pointers technique, sliding window, prefix sums, suffix arrays, string hashing, KMP algorithm, Z-algorithm, Manacher's algorithm for palindromes, subarray problems, kadane's algorithm, monotonic stack and queue",

    "🌲 Trees & Graphs": "Competitive programming trees and graphs: DFS, BFS, shortest paths (Dijkstra, Bellman-Ford, Floyd-Warshall), minimum spanning tree (Kruskal, Prim), topological sort, strongly connected components (Kosaraju, Tarjan), LCA (Lowest Common Ancestor), binary lifting, Euler tour, tree DP, segment trees on trees",

    "⚡ Dynamic Programming": "Competitive programming dynamic programming: classical DP (0/1 knapsack, LCS, LIS, matrix chain multiplication, edit distance), bitmask DP, digit DP, DP on trees, interval DP, DP with optimization (divide and conquer optimization, convex hull trick), state space reduction, memoization vs tabulation trade-offs",

    "🔢 Math & Number Theory": "Competitive programming mathematics: modular arithmetic, modular exponentiation, Euler's totient function, Sieve of Eratosthenes, prime factorization, GCD/LCM, Bezout's identity, Chinese Remainder Theorem, combinatorics (nCr mod p, Lucas theorem), matrix exponentiation for Fibonacci, inclusion-exclusion principle",

    "📊 Segment Trees & BIT": "Competitive programming data structures: segment trees (range queries, lazy propagation, merge sort tree), Fenwick trees / Binary Indexed Trees (BIT), sparse tables for RMQ, sqrt decomposition, persistent segment trees, 2D segment trees, order statistics tree (policy-based in C++)",

    "🎯 Greedy Algorithms": "Competitive programming greedy algorithms: activity selection, interval scheduling, Huffman coding, job sequencing, fractional knapsack, greedy graph algorithms, exchange argument proof technique, greedy with sorting, greedy with priority queues, classic greedy DP crossover problems",

    "🔍 Binary Search & Ternary Search": "Competitive programming search techniques: binary search on answer (classic and advanced applications), binary search on monotone functions, ternary search for unimodal functions, parallel binary search, binary search on segment trees, fractional cascading",

    "🔗 Graph Algorithms Advanced": "Advanced competitive programming graph algorithms: network flow (Ford-Fulkerson, Dinic's), bipartite matching, Hungarian algorithm, articulation points and bridges, 2-SAT problem, Euler circuit/path, Hamiltonian path heuristics, centroid decomposition, heavy-light decomposition",
}

# ── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem; background:linear-gradient(90deg,#EF4444,#F59E0B);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
🏆 Competitive Programming MCQs</h1>
<p style='color:#9CA3AF;'>Contest-level DSA theory · Algorithm analysis · Problem patterns · 20 questions per set</p>
""", unsafe_allow_html=True)

# Difficulty guide
with st.expander("📖 Difficulty Guide", expanded=False):
    c1, c2, c3 = st.columns(3)
    c1.markdown("**Easy** — Codeforces Div.2 A/B level\nConcept identification, definition questions")
    c2.markdown("**Medium** — Codeforces Div.2 C/D level\nAlgorithm application and complexity analysis")
    c3.markdown("**Hard** — Codeforces Div.1 level\nAdvanced techniques, proofs, edge cases")

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

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏆 Contest Stats")
    s = get_topic_score(topic_label)
    if s["total"] > 0:
        pct = s["correct"] / s["total"] * 100
        st.metric("Correct", f"{s['correct']}/{s['total']}", f"{pct:.0f}%")
        st.progress(s["correct"] / s["total"])
        # Rating estimate
        if pct >= 80:
            st.success("🟢 Contest Ready!")
        elif pct >= 60:
            st.warning("🟡 Needs Practice")
        else:
            st.error("🔴 Study More")
    else:
        st.info("Start practicing!")
    st.markdown("---")
    st.metric("🔢 Total Qs Solved", get_total_seen())
    if st.button("🗑️ Reset topic", use_container_width=True):
        clear_topic_history(topic_label)
        st.success("Cleared!")

# ── Session State ──────────────────────────────────────────────────────────────
Q_KEY = f"{PAGE}_queue"; ANSWERED_KEY = f"{PAGE}_answered"
ANSWER_KEY = f"{PAGE}_user_ans"; TOPIC_KEY = f"{PAGE}_lt"; DIFF_KEY = f"{PAGE}_ld"; TYPE_KEY = f"{PAGE}_ltype"

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
        if st.button(f"🏆 Generate {BATCH_SIZE} Contest Questions", use_container_width=True, type="primary"):
            with st.spinner(f"Generating {BATCH_SIZE} competitive programming questions..."):
                qs, err = generate_mcq_set(topic, difficulty, q_type_val, count=BATCH_SIZE)
            if err:
                st.error(f"❌ {err}")
            elif qs:
                st.session_state.update({Q_KEY: qs, ANSWERED_KEY: False, ANSWER_KEY: {}})
                st.rerun()
    st.markdown("""
    <div style='text-align:center;color:#4B5563;padding:2rem;'>
    <p style='font-size:1.1rem;'>👆 Click to load 20 contest-level theory questions</p>
    <p style='font-size:0.82rem;'>Master the WHY behind algorithms — not just the HOW</p>
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
        st.markdown(f"<span style='background:#2D2D4A;color:#EF4444;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
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
