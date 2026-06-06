"""
competitive_mcq.py — Competitive Programming MCQs with 20-question batch queue.
Covers DSA contest topics, algorithm analysis, problem-solving patterns.
"""

import streamlit as st
from utils.gemini_service import generate_mcq_set, is_api_configured
from utils.question_hash import save_hash, get_question_hash, get_total_seen, clear_topic_history
from utils.mcq_helper import render_question_card, render_feedback, render_score_badge
from utils.firebase_service import record_answer, get_topic_score, log_page_visit

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
Q_KEY = f"{PAGE}_queue"; IDX_KEY = f"{PAGE}_idx"; ANSWERED_KEY = f"{PAGE}_answered"
ANSWER_KEY = f"{PAGE}_ans"; TOPIC_KEY = f"{PAGE}_lt"; DIFF_KEY = f"{PAGE}_ld"; TYPE_KEY = f"{PAGE}_ltype"

def _queue():   return st.session_state.get(Q_KEY, [])
def _idx():     return st.session_state.get(IDX_KEY, 0)
def _current(): q = _queue(); i = _idx(); return q[i] if q and i < len(q) else None

if (st.session_state.get(TOPIC_KEY) != topic_label or
        st.session_state.get(DIFF_KEY) != difficulty or
        st.session_state.get(TYPE_KEY) != q_type_val):
    for k in [Q_KEY, IDX_KEY, ANSWERED_KEY, ANSWER_KEY]:
        st.session_state.pop(k, None)
    st.session_state.update({TOPIC_KEY: topic_label, DIFF_KEY: difficulty, TYPE_KEY: q_type_val})

# ── Generate / Queue ───────────────────────────────────────────────────────────
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
                st.session_state.update({Q_KEY: qs, IDX_KEY: 0, ANSWERED_KEY: False, ANSWER_KEY: None})
                st.rerun()
    st.markdown("""
    <div style='text-align:center;color:#4B5563;padding:2rem;'>
    <p style='font-size:1.1rem;'>👆 Click to load 20 contest-level theory questions</p>
    <p style='font-size:0.82rem;'>Master the WHY behind algorithms — not just the HOW</p>
    </div>""", unsafe_allow_html=True)
else:
    idx = _idx(); total = len(queue)
    st.markdown(f"""
    <div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.8rem;'>
    <span style='color:#EF4444;font-weight:700;font-size:1rem;'>Q {idx+1} / {total}</span>
    <div style='flex:1;background:#2D2D4A;border-radius:4px;height:8px;'>
    <div style='background:linear-gradient(90deg,#EF4444,#F59E0B);width:{idx/total*100:.0f}%;height:8px;border-radius:4px;'></div>
    </div>
    <span style='color:#6B7280;font-size:0.82rem;'>{topic_label[:25]}</span>
    </div>""", unsafe_allow_html=True)

    q = _current()
    if q is None:
        s = get_topic_score(topic_label)
        st.success(f"🏆 Set Complete! Score: {s['correct']}/{s['total']}")
        if st.button("🔄 New Set", type="primary"):
            st.session_state[Q_KEY] = []; st.rerun()
    else:
        st.markdown(f"<span style='background:#2D2D4A;color:#EF4444;padding:4px 12px;border-radius:20px;font-size:0.8rem;'>🏷️ {q.get('keyword','')}</span>", unsafe_allow_html=True)
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
                        st.warning("Select an answer first.")
            else:
                render_feedback(q, st.session_state[ANSWER_KEY])

        with c2:
            if st.session_state.get(ANSWERED_KEY, False):
                is_last = idx >= total - 1
                if st.button("🏆 Done!" if is_last else f"Next → Q{idx+2}/{total}", use_container_width=True):
                    if is_last:
                        st.session_state[Q_KEY] = []; st.session_state[IDX_KEY] = 0
                    else:
                        st.session_state[IDX_KEY] = idx + 1
                    st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None}); st.rerun()

        with c3:
            if st.button("⚡ New Set", use_container_width=True):
                st.session_state[Q_KEY] = []; st.session_state[IDX_KEY] = 0
                st.session_state.update({ANSWERED_KEY: False, ANSWER_KEY: None}); st.rerun()

s = get_topic_score(topic_label)
if s["total"] > 0:
    st.markdown("---"); render_score_badge(s["correct"], s["total"])
