"""
mcq_helper.py — MCQ JSON parsing, validation, and Streamlit rendering helpers.
"""

import json
import re
import streamlit as st


# ─────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────

def parse_mcq_response(raw_text: str) -> dict | None:
    """
    Robustly parse Gemini MCQ response.
    Handles markdown fences, leading/trailing text.
    Returns parsed dict or None on failure.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Try to find a JSON object or array
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if json_match:
        text = json_match.group(0)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def parse_batch_response(raw_text: str) -> list[dict] | None:
    """Parse a batch of MCQ questions returned as a JSON array."""
    if not raw_text:
        return None

    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    text = text.strip()

    # Find JSON array
    arr_match = re.search(r"\[[\s\S]*\]", text)
    if arr_match:
        text = arr_match.group(0)

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        pass

    return None


# ─────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────

REQUIRED_KEYS = {"question", "type", "options", "correct", "explanation", "keyword"}

def validate_mcq(mcq: dict) -> tuple[bool, str]:
    """
    Validate an MCQ dict has all required fields.
    Returns (is_valid, error_message).
    """
    if not isinstance(mcq, dict):
        return False, "Response is not a dictionary"

    missing = REQUIRED_KEYS - set(mcq.keys())
    if missing:
        return False, f"Missing keys: {missing}"

    if not isinstance(mcq["options"], list) or len(mcq["options"]) < 2:
        return False, "Options must be a list with at least 2 items"

    if not isinstance(mcq["correct"], list) or len(mcq["correct"]) == 0:
        return False, "Correct must be a non-empty list"

    if not mcq["question"].strip():
        return False, "Question text is empty"

    return True, ""


# ─────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────

def render_question_card(q: dict, key_prefix: str = "mcq", disabled: bool = False, default_val=None) -> str | list | None:
    """
    Render an MCQ question with options as a Streamlit card.
    Returns the user's selected answer(s) or None if not answered.
    """
    # Question display
    st.markdown(
        f"""<div style='background: linear-gradient(135deg, #1A1A2E, #16213E);
        border-left: 4px solid #6C63FF; border-radius: 8px;
        padding: 1.2rem 1.5rem; margin-bottom: 1rem;'>
        <p style='color: #E8E8F0; font-size: 1.05rem; margin: 0; line-height: 1.6;'>
        {q['question']}</p></div>""",
        unsafe_allow_html=True,
    )

    q_type = q.get("type", "single")
    options = q.get("options", [])

    if q_type == "multi":
        st.caption("🔘 Select **all** correct answers:")
        selected = []
        for opt in options:
            is_checked = False
            if default_val and opt[0] in default_val:
                is_checked = True
            if st.checkbox(opt, key=f"{key_prefix}_{opt[:10]}", value=is_checked, disabled=disabled):
                selected.append(opt[0])  # letter only: "A", "B", etc.
        return selected if selected else None
    else:
        st.caption("🔘 Select one answer:")
        default_index = None
        if default_val:
            for o_idx, opt in enumerate(options):
                if opt.startswith(default_val):
                    default_index = o_idx
                    break
        answer = st.radio(
            "Your answer:",
            options,
            key=f"{key_prefix}_radio",
            label_visibility="collapsed",
            index=default_index,
            disabled=disabled,
        )
        if answer:
            return answer[0]  # return letter "A", "B", etc.
        return None


def render_feedback(q: dict, user_answer) -> bool:
    """
    Render correct/incorrect feedback and explanation.
    Returns True if answer was correct.
    """
    correct = q.get("correct", [])

    if isinstance(user_answer, list):
        is_correct = sorted(user_answer) == sorted(correct)
    else:
        is_correct = user_answer in correct

    if is_correct:
        st.success("✅ **Correct!** Well done.")
    else:
        correct_str = ", ".join(correct)
        st.error(f"❌ **Incorrect.** Correct answer: **{correct_str}**")

    with st.expander("📖 See explanation", expanded=is_correct):
        st.markdown(q.get("explanation", "No explanation provided."))

    return is_correct


def render_score_badge(correct: int, total: int):
    """Render a styled score badge."""
    pct = (correct / total * 100) if total > 0 else 0
    color = "#4CAF50" if pct >= 70 else "#FF9800" if pct >= 40 else "#F44336"
    st.markdown(
        f"""<div style='text-align:center; padding:1rem; background:{color}22;
        border: 2px solid {color}; border-radius: 12px; margin: 1rem 0;'>
        <h2 style='color:{color}; margin:0;'>{correct}/{total}</h2>
        <p style='color:{color}; margin:0; font-size:1.1rem;'>{pct:.1f}% Score</p>
        </div>""",
        unsafe_allow_html=True,
    )


def render_custom_logo(alignment: str = "center") -> None:
    """Render a modern, responsive SVG vector logo instead of a clunky image file."""
    logo_html = f"""
    <div style='display: flex; align-items: center; justify-content: {alignment}; gap: 12px; width: 100%; margin: 0 auto; padding: 0.5rem 0;'>
        <svg width="38" height="38" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="flex-shrink: 0;">
            <defs>
                <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#6C63FF" />
                    <stop offset="100%" stop-color="#06B6D4" />
                </linearGradient>
                <filter id="logo-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="6" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
            </defs>
            <rect x="10" y="10" width="80" height="80" rx="22" fill="url(#logo-grad)" opacity="0.15" stroke="url(#logo-grad)" stroke-width="2"/>
            <path d="M50 18 L28 55 H47 L41 82 L72 45 H53 L59 18 Z" fill="url(#logo-grad)" filter="url(#logo-glow)"/>
        </svg>
        <div style='display: flex; flex-direction: column;'>
            <span style='font-size: 1.45rem; font-weight: 900; background: linear-gradient(90deg, #6C63FF, #06B6D4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 0.5px; line-height: 1.2; white-space: nowrap;'>
                Skill Builder
            </span>
            <span style='color: #9CA3AF; font-size: 0.65rem; letter-spacing: 1px; text-transform: uppercase; font-weight: 600; line-height: 1;'>
                AI-Powered Academy
            </span>
        </div>
    </div>
    """
    st.markdown(logo_html, unsafe_allow_html=True)
