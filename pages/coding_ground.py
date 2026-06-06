"""
coding_ground.py — AI-generated coding problems with in-browser code editor.
Generates problem statements with test cases using Gemini,
executes Python code locally with sandboxed subprocess.
"""

import streamlit as st
import subprocess
import sys
import textwrap
import time
import json
import uuid
from utils.gemini_service import get_client, _call_with_model_fallback, MODEL_FALLBACKS
from utils.auth_service import get_current_user
from utils.firebase_service import log_page_visit

log_page_visit("Coding Ground")

try:
    from streamlit_ace import st_ace
    ACE_AVAILABLE = True
except ImportError:
    ACE_AVAILABLE = False

# ── Page Header ────────────────────────────────────────────────────────────────
st.markdown("""
<h1 style='font-size:2.2rem;background:linear-gradient(90deg,#10B981,#06B6D4);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
💻 Coding Ground</h1>
<p style='color:#9CA3AF;'>AI-generated coding problems · In-browser Python editor · Instant execution & AI feedback</p>
""", unsafe_allow_html=True)

# ── Topic Selection ────────────────────────────────────────────────────────────
TOPICS = {
    "📊 Arrays & Hashing": {
        "desc": "Two sum, subarray problems, prefix sums, frequency counting",
        "tags": ["easy", "medium"],
        "template": "arrays_hashing"
    },
    "🌀 Two Pointers": {
        "desc": "Sliding window, fast/slow pointers, container problems",
        "tags": ["easy", "medium"],
        "template": "two_pointers"
    },
    "🌲 Binary Trees": {
        "desc": "Traversals, BST operations, level order, path problems",
        "tags": ["medium", "hard"],
        "template": "binary_trees"
    },
    "📈 Dynamic Programming": {
        "desc": "1D/2D DP, memoization, classic DP patterns",
        "tags": ["medium", "hard"],
        "template": "dp"
    },
    "🔗 Linked Lists": {
        "desc": "Reversal, cycle detection, merge, operations",
        "tags": ["easy", "medium"],
        "template": "linked_lists"
    },
    "📐 Graphs": {
        "desc": "DFS, BFS, shortest paths, cycle detection",
        "tags": ["medium", "hard"],
        "template": "graphs"
    },
    "🔢 Math & Number Theory": {
        "desc": "Modular arithmetic, primes, GCD, combinatorics",
        "tags": ["easy", "medium", "hard"],
        "template": "math"
    },
    "🎯 Greedy": {
        "desc": "Interval problems, scheduling, greedy patterns",
        "tags": ["medium", "hard"],
        "template": "greedy"
    },
    "🔤 Strings": {
        "desc": "Pattern matching, palindromes, anagrams, string manipulation",
        "tags": ["easy", "medium"],
        "template": "strings"
    },
    "🏔️ Stack & Queue": {
        "desc": "Monotonic stack, expression evaluation, BFS patterns",
        "tags": ["easy", "medium"],
        "template": "stack_queue"
    },
}

col1, col2, col3 = st.columns([2, 2, 1])
with col1:
    topic_label = st.selectbox("📌 Topic", list(TOPICS.keys()), key="cg_topic")
    topic_meta  = TOPICS[topic_label]
with col2:
    difficulty  = st.select_slider("🎯 Difficulty", options=["easy", "medium", "hard"], value="medium", key="cg_diff")
with col3:
    lang = st.selectbox("🐍 Language", ["Python"], key="cg_lang")

st.markdown(f"<small style='color:#6B7280;'>💡 {topic_meta['desc']}</small>", unsafe_allow_html=True)

# ── Problem Generator ──────────────────────────────────────────────────────────
CODING_PROBLEM_PROMPT = """You are an expert competitive programming problem setter (LeetCode/Codeforces style).

Generate a {difficulty} difficulty coding problem on the topic: "{topic}"

The problem MUST:
1. Have a clear problem statement (2-4 paragraphs)
2. Have explicit constraints (input size, value ranges)
3. Have 2 example test cases with input, output, and explanation
4. Have 3 hidden test cases (input/expected output only, no explanation)
5. Have a time complexity hint
6. Have a starter code template in Python

Return ONLY valid JSON (no markdown fences, no extra text):
{{
  "title": "Problem Title",
  "difficulty": "{difficulty}",
  "topic": "{topic}",
  "problem_statement": "Full problem description...",
  "input_format": "Description of input format",
  "output_format": "Description of output format",  
  "constraints": ["1 <= n <= 10^5", "..."],
  "examples": [
    {{"input": "4\\n1 2 3 4", "output": "10", "explanation": "Sum of all elements"}},
    {{"input": "3\\n5 5 5", "output": "15", "explanation": "..."}}
  ],
  "hidden_tests": [
    {{"input": "1\\n0", "output": "0"}},
    {{"input": "5\\n-1 -2 3 4 5", "output": "9"}},
    {{"input": "6\\n100 200 300 400 500 600", "output": "2100"}}
  ],
  "time_complexity_hint": "O(n) expected",
  "starter_code": "def solve(n, arr):\\n    # Your code here\\n    pass\\n\\n# Input parsing\\nn = int(input())\\narr = list(map(int, input().split()))\\nprint(solve(n, arr))",
  "solution_approach": "Brief hint about the approach (no full solution)"
}}"""


def generate_problem(topic: str, difficulty: str) -> tuple[dict | None, str | None]:
    """Generate a coding problem using Gemini."""
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    prompt = CODING_PROBLEM_PROMPT.format(topic=topic, difficulty=difficulty)
    result, err, _ = _call_with_model_fallback(client, prompt, max_retries=2)
    if err:
        return None, f"API Error: {err}"

    raw = result.text.strip()
    # Strip markdown fences if any
    import re
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'\s*```$', '', raw, flags=re.MULTILINE)
    json_match = re.search(r'\{[\s\S]*\}', raw)
    if json_match:
        raw = json_match.group(0)

    try:
        problem = json.loads(raw)
        return problem, None
    except Exception as e:
        return None, f"Parse error: {e} | Raw: {raw[:200]}"


# ── Code Execution ─────────────────────────────────────────────────────────────

def run_python_code(code: str, stdin_input: str = "", timeout: int = 5) -> dict:
    """
    Execute Python code in a subprocess with timeout.
    Returns {output, error, time_ms, success}.
    """
    try:
        start = time.time()
        proc = subprocess.run(
            [sys.executable, "-c", code],
            input=stdin_input,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        elapsed = int((time.time() - start) * 1000)
        return {
            "output": proc.stdout.strip(),
            "error": proc.stderr.strip() if proc.returncode != 0 else "",
            "time_ms": elapsed,
            "success": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"output": "", "error": f"⏰ Time Limit Exceeded ({timeout}s)", "time_ms": timeout*1000, "success": False}
    except Exception as e:
        return {"output": "", "error": str(e), "time_ms": 0, "success": False}


# ── AI Code Review ─────────────────────────────────────────────────────────────

def get_ai_feedback(problem: dict, code: str, test_results: list) -> str | None:
    """Get AI feedback on the submitted code."""
    client = get_client()
    if not client:
        return None

    passed = sum(1 for r in test_results if r.get("passed"))
    total  = len(test_results)

    review_prompt = f"""You are an expert coding mentor reviewing a student's solution.

Problem: {problem.get('title', 'Unknown')}
Topic: {problem.get('topic', '')}
Difficulty: {problem.get('difficulty', '')}
Time Complexity Hint: {problem.get('time_complexity_hint', '')}

Student's Code:
```python
{code}
```

Test Results: {passed}/{total} passed

Provide concise, constructive feedback:
1. **Correctness**: Is the logic correct? Any edge case issues?
2. **Time Complexity**: What is the complexity? Is it optimal?
3. **Code Quality**: Is the code clean and Pythonic?
4. **Hint** (if failing): One specific hint to fix the issue (no full solution)
5. **Better Approach** (if suboptimal): Brief description

Keep total response under 300 words. Be encouraging but honest."""

    result, err, _ = _call_with_model_fallback(client, review_prompt, max_retries=1)
    return result.text if result else None


# ── Main UI ────────────────────────────────────────────────────────────────────
st.markdown("---")

# Generate Problem
gen_col, reload_col = st.columns([3, 1])
with gen_col:
    if st.button("🎲 Generate Coding Problem", use_container_width=True, type="primary",
                 key="cg_generate"):
        with st.spinner(f"Generating a {difficulty} {topic_label} problem..."):
            problem, err = generate_problem(
                topic_label.split(" ", 1)[-1].strip(),  # remove emoji
                difficulty
            )
        if err:
            st.error(f"❌ {err}")
        else:
            st.session_state["cg_problem"] = problem
            st.session_state["cg_results"] = []
            st.session_state["cg_ai_feedback"] = None
            st.rerun()

with reload_col:
    if st.session_state.get("cg_problem") and st.button("🔄 New Problem", use_container_width=True):
        st.session_state.pop("cg_problem", None)
        st.session_state.pop("cg_results", None)
        st.session_state.pop("cg_ai_feedback", None)
        st.rerun()

# ── Problem Display + Editor ───────────────────────────────────────────────────
problem = st.session_state.get("cg_problem")

if not problem:
    st.markdown("""
    <div style='text-align:center;padding:3rem;color:#4B5563;'>
    <p style='font-size:3rem;margin:0;'>💻</p>
    <p style='font-size:1.2rem;'>Select a topic and click "Generate Coding Problem"</p>
    <p style='font-size:0.85rem;'>AI generates a unique problem with test cases every time</p>
    </div>""", unsafe_allow_html=True)
else:
    left_col, right_col = st.columns([1, 1], gap="medium")

    # ── LEFT: Problem Statement ─────────────────────────────────────────────
    with left_col:
        diff_color = {"easy": "#10B981", "medium": "#F59E0B", "hard": "#EF4444"}.get(problem.get("difficulty", "medium"), "#6B7280")
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);border:1px solid #2D2D4A;
        border-radius:12px;padding:1.5rem;margin-bottom:1rem;'>
        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:0.8rem;'>
        <h3 style='color:#E8E8F0;margin:0;font-size:1.1rem;'>{problem.get('title','Problem')}</h3>
        <span style='background:{diff_color}22;color:{diff_color};padding:3px 10px;border-radius:12px;
        font-size:0.78rem;border:1px solid {diff_color}44;'>{problem.get('difficulty','').upper()}</span>
        </div>
        <p style='color:#9CA3AF;font-size:0.82rem;margin:0;'>🏷️ {problem.get('topic','')}</p>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Problem Statement", expanded=True):
            st.markdown(problem.get("problem_statement", ""))

            st.markdown("**Input Format:**")
            st.markdown(problem.get("input_format", ""))

            st.markdown("**Output Format:**")
            st.markdown(problem.get("output_format", ""))

            st.markdown("**Constraints:**")
            for c in problem.get("constraints", []):
                st.markdown(f"- `{c}`")

        with st.expander("📖 Examples", expanded=True):
            for i, ex in enumerate(problem.get("examples", [])):
                st.markdown(f"**Example {i+1}:**")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Input:**")
                    st.code(ex.get("input", ""), language="text")
                with c2:
                    st.markdown("**Output:**")
                    st.code(ex.get("output", ""), language="text")
                if ex.get("explanation"):
                    st.markdown(f"💡 *{ex['explanation']}*")
                st.markdown("---")

        with st.expander("⏱️ Time Complexity Hint"):
            st.info(f"Expected: `{problem.get('time_complexity_hint', 'Check constraints')}`")

        with st.expander("🔍 Approach Hint"):
            st.markdown(problem.get("solution_approach", "Think about the problem structure..."))

    # ── RIGHT: Code Editor + Runner ─────────────────────────────────────────
    with right_col:
        st.markdown("**✏️ Your Solution:**")

        # Initialize code with starter template
        starter = problem.get("starter_code", "# Write your solution here\n")
        if "cg_code" not in st.session_state:
            st.session_state["cg_code"] = starter

        # Code editor
        if ACE_AVAILABLE:
            code = st_ace(
                value=st.session_state.get("cg_code", starter),
                language="python",
                theme="monokai",
                key=f"ace_{problem.get('title','')[:20]}",
                height=340,
                font_size=14,
                wrap=False,
                show_gutter=True,
                show_print_margin=False,
                auto_update=True,
            )
            if code:
                st.session_state["cg_code"] = code
        else:
            code = st.text_area(
                "Code Editor",
                value=st.session_state.get("cg_code", starter),
                height=340,
                key="cg_code_area",
                label_visibility="collapsed",
            )
            st.session_state["cg_code"] = code
            st.caption("💡 Install `streamlit-ace` for syntax highlighting: `pip install streamlit-ace`")

        run_col, submit_col, reset_col = st.columns([1, 1, 1])

        with run_col:
            # Run against example tests
            if st.button("▶️ Run Examples", use_container_width=True):
                user_code = st.session_state.get("cg_code", "")
                examples = problem.get("examples", [])
                results = []
                for ex in examples:
                    res = run_python_code(user_code, ex.get("input", ""))
                    expected = ex.get("output", "").strip()
                    actual   = res["output"].strip()
                    results.append({
                        "input": ex.get("input", ""),
                        "expected": expected,
                        "actual": actual,
                        "passed": actual == expected,
                        "error": res.get("error", ""),
                        "time_ms": res.get("time_ms", 0),
                        "type": "example",
                    })
                st.session_state["cg_results"] = results
                st.rerun()

        with submit_col:
            if st.button("🚀 Submit All", use_container_width=True, type="primary"):
                user_code = st.session_state.get("cg_code", "")
                all_tests = problem.get("examples", []) + problem.get("hidden_tests", [])
                results = []
                for i, test in enumerate(all_tests):
                    res = run_python_code(user_code, test.get("input", ""))
                    expected = test.get("output", "").strip()
                    actual   = res["output"].strip()
                    results.append({
                        "input": test.get("input", ""),
                        "expected": expected,
                        "actual": actual,
                        "passed": actual == expected,
                        "error": res.get("error", ""),
                        "time_ms": res.get("time_ms", 0),
                        "type": "example" if i < len(problem.get("examples", [])) else "hidden",
                    })
                st.session_state["cg_results"] = results
                # Get AI feedback
                with st.spinner("Getting AI feedback..."):
                    feedback = get_ai_feedback(problem, user_code, results)
                st.session_state["cg_ai_feedback"] = feedback
                st.rerun()

        with reset_col:
            if st.button("🗑️ Reset Code", use_container_width=True):
                st.session_state["cg_code"] = starter
                st.session_state["cg_results"] = []
                st.session_state["cg_ai_feedback"] = None
                st.rerun()

        # ── Test Results ───────────────────────────────────────────────────
        results = st.session_state.get("cg_results", [])
        if results:
            st.markdown("---")
            passed = sum(1 for r in results if r["passed"])
            total  = len(results)

            # Score banner
            pct = passed / total * 100
            color = "#10B981" if pct == 100 else "#F59E0B" if pct >= 50 else "#EF4444"
            st.markdown(f"""
            <div style='background:{color}22;border:2px solid {color};border-radius:10px;
            padding:0.8rem;text-align:center;margin-bottom:1rem;'>
            <span style='color:{color};font-size:1.4rem;font-weight:800;'>{passed}/{total}</span>
            <span style='color:{color};font-size:0.9rem;'> tests passed ({pct:.0f}%)</span>
            </div>""", unsafe_allow_html=True)

            for i, r in enumerate(results):
                is_hidden = r.get("type") == "hidden"
                label = f"Test {i+1} {'🔒 Hidden' if is_hidden else '📖 Example'}"
                icon  = "✅" if r["passed"] else "❌"

                with st.expander(f"{icon} {label} — {r['time_ms']}ms", expanded=not r["passed"]):
                    if not is_hidden:
                        st.markdown(f"**Input:** `{r['input'][:80]}`")
                    st.markdown(f"**Expected:** `{r['expected']}`")
                    if not r["passed"]:
                        st.markdown(f"**Your Output:** `{r['actual'] or '(empty)'}`")
                        if r.get("error"):
                            st.code(r["error"], language="text")

        # ── AI Feedback ────────────────────────────────────────────────────
        ai_fb = st.session_state.get("cg_ai_feedback")
        if ai_fb:
            st.markdown("---")
            with st.expander("🤖 AI Code Review", expanded=True):
                st.markdown(ai_fb)
