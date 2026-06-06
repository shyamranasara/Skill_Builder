"""
gemini_service.py — All Gemini API interactions using the new google-genai SDK.
Handles API key loading, retry logic, MCQ generation, study explanations, and audio analysis.

All errors and key events are logged to: logs/gemini.log
"""

import os
import time
import uuid
import logging
import traceback
import streamlit as st
from google import genai
from google.genai import types
from pathlib import Path

# ─────────────────────────────────────────────
# Logging Setup — writes to logs/gemini.log
# ─────────────────────────────────────────────

_PROJECT_ROOT = Path(__file__).parent.parent
_LOG_DIR = _PROJECT_ROOT / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "gemini.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),   # also print to console
    ],
)
log = logging.getLogger("gemini_service")
log.info("=" * 60)
log.info("gemini_service module loaded")
log.info(f"Log file: {_LOG_FILE}")
log.info(f"Project root: {_PROJECT_ROOT}")


# ─────────────────────────────────────────────
# Prompts (imported below to avoid circular issues)
# ─────────────────────────────────────────────

from utils.prompts import (
    MCQ_SINGLE_PROMPT,
    MCQ_MULTI_PROMPT,
    MCQ_BATCH_20_PROMPT,
    JAVA_MCQ_BATCH_PROMPT,
    STUDY_EXPLANATION_PROMPT,
    FOLLOWUP_SYSTEM_PROMPT,
    INTERVIEW_QUESTION_PROMPT,
    AUDIO_FEEDBACK_PROMPT,
    MOCK_TEST_BATCH_PROMPT,
)
from utils.mcq_helper import parse_mcq_response, parse_batch_response, validate_mcq
from utils.question_hash import get_seen_keywords


# ─────────────────────────────────────────────
# .env loader — reads directly from file
# ─────────────────────────────────────────────

_ENV_FILE = _PROJECT_ROOT / ".env"


def _read_env_file() -> dict:
    """Read key=value pairs from the .env file directly."""
    env_vars = {}
    if _ENV_FILE.exists():
        with open(_ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
        log.debug(f".env file read OK — keys found: {list(env_vars.keys())}")
    else:
        log.warning(f".env file NOT found at: {_ENV_FILE}")
    return env_vars


# ─────────────────────────────────────────────
# API Key & Client Initialization
# ─────────────────────────────────────────────

def _get_api_key() -> str | None:
    """Load Gemini API key — checks st.secrets, then os.environ, then .env file directly."""
    # 1. Streamlit Cloud secrets
    try:
        key = st.secrets.get("GEMINI_API_KEY", None)
        if key and key != "your_gemini_api_key_here":
            log.debug(f"API key loaded from st.secrets (len={len(key)}, prefix={key[:8]}...)")
            return key
        elif key:
            log.warning("st.secrets has GEMINI_API_KEY but it's still a placeholder!")
    except Exception as ex:
        log.debug(f"st.secrets not available: {ex}")

    # 2. Environment variable
    key = os.getenv("GEMINI_API_KEY")
    if key and key != "your_gemini_api_key_here":
        log.debug(f"API key loaded from os.environ (len={len(key)}, prefix={key[:8]}...)")
        return key

    # 3. Read .env file directly
    env_vars = _read_env_file()
    key = env_vars.get("GEMINI_API_KEY")
    if key and key != "your_gemini_api_key_here":
        log.debug(f"API key loaded from .env file (len={len(key)}, prefix={key[:8]}...)")
        return key

    log.error("No valid GEMINI_API_KEY found in st.secrets, os.environ, or .env file!")
    return None


def get_client() -> genai.Client | None:
    """Initialize and return Gemini client. Returns None if no key found."""
    api_key = _get_api_key()
    if not api_key:
        log.error("get_client(): API key is None — cannot create client")
        return None
    try:
        client = genai.Client(api_key=api_key)
        log.info(f"Gemini client created OK (key prefix: {api_key[:8]}...)")
        return client
    except Exception as e:
        log.error(f"get_client(): Failed to create client: {e}")
        return None


def is_api_configured() -> bool:
    """Check if API key is available and not placeholder."""
    key = _get_api_key()
    return bool(key and key != "your_gemini_api_key_here")


# Model fallback chain — tries each model in order on quota/rate errors
MODEL_ID = "models/gemini-2.5-flash"
MODEL_FALLBACKS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash-lite",
    "models/gemini-flash-latest",
]
log.info(f"Primary model: {MODEL_ID}, fallbacks: {MODEL_FALLBACKS[1:]}")


# ─────────────────────────────────────────────
# Retry Helper
# ─────────────────────────────────────────────

def _call_with_retry(fn, max_retries: int = 3, base_delay: float = 2.0):
    """
    Call fn() with exponential backoff on rate limit / server errors.
    Returns (result, error_message). Always returns the real error message.
    """
    last_error = "Unknown error"
    for attempt in range(max_retries):
        log.debug(f"_call_with_retry: attempt {attempt + 1}/{max_retries}")
        try:
            result = fn()
            log.debug(f"_call_with_retry: attempt {attempt + 1} succeeded")
            return result, None
        except Exception as e:
            last_error = str(e)
            err_str = last_error.lower()
            log.warning(f"_call_with_retry attempt {attempt + 1} FAILED: {type(e).__name__}: {last_error[:300]}")

            is_retryable = any(x in err_str for x in ["429", "quota", "rate", "503", "overloaded", "unavailable"])
            if is_retryable and attempt < max_retries - 1:
                wait = base_delay * (2 ** attempt)
                log.info(f"Rate limit detected — waiting {wait:.1f}s before retry...")
                time.sleep(wait)
            else:
                log.error(f"Non-retryable error or last attempt — giving up: {last_error[:300]}")
                return None, last_error
    return None, last_error


def _call_with_model_fallback(client, prompt, max_retries: int = 2):
    """
    Try each model in MODEL_FALLBACKS until one works.
    Returns (result, error_message, model_used).
    """
    last_error = "No models available"
    for model in MODEL_FALLBACKS:
        log.info(f"_call_with_model_fallback: trying model {model}")
        result, err = _call_with_retry(
            lambda m=model: client.models.generate_content(model=m, contents=prompt),
            max_retries=max_retries,
        )
        if result is not None:
            log.info(f"_call_with_model_fallback: SUCCESS with model {model}")
            return result, None, model
        last_error = err or "Unknown error"
        err_lower = last_error.lower()
        # Only fall back if it's a quota/rate error
        if any(x in err_lower for x in ["429", "quota", "rate", "exhausted"]):
            log.warning(f"Model {model} quota exhausted — trying next fallback...")
            continue
        else:
            # Non-quota error — stop immediately
            log.error(f"Model {model} failed with non-quota error: {last_error[:200]}")
            break
    return None, last_error, None



# ─────────────────────────────────────────────
# MCQ Generation
# ─────────────────────────────────────────────

def generate_mcq(
    topic: str,
    difficulty: str = "medium",
    q_type: str = "single",
    max_attempts: int = 3,
) -> tuple[dict | None, str | None]:
    """
    Generate one non-repeatable MCQ using Gemini.
    Returns (mcq_dict, error_message).
    """
    log.info(f"generate_mcq() called — topic='{topic[:50]}', difficulty={difficulty}, type={q_type}")

    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured. Please add your key to the .env file."

    seen_keywords = get_seen_keywords(topic)
    avoid_str = ", ".join(seen_keywords[-30:]) if seen_keywords else "none"
    seed = f"{uuid.uuid4()}-{time.time()}"

    template = MCQ_MULTI_PROMPT if q_type == "multi" else MCQ_SINGLE_PROMPT
    prompt = template.format(
        topic=topic,
        difficulty=difficulty,
        seed=seed,
        avoid_keywords=avoid_str,
    )
    log.debug(f"Prompt built (len={len(prompt)} chars). Sending to model...")

    for attempt_num in range(max_attempts):
        log.info(f"generate_mcq: MCQ attempt {attempt_num + 1}/{max_attempts}")
        result, err, model_used = _call_with_model_fallback(client, prompt)
        if err:
            log.error(f"generate_mcq: All models failed: {err[:300]}")
            return None, f"API Error: {err}"
        if result is None:
            log.warning("generate_mcq: result is None, retrying...")
            continue

        raw_text = result.text
        log.debug(f"generate_mcq: raw response ({len(raw_text)} chars) via {model_used}: {raw_text[:200]}")

        mcq = parse_mcq_response(raw_text)
        if mcq is None:
            log.warning(f"generate_mcq: parse_mcq_response returned None — bad JSON/format")
            continue

        valid, validation_err = validate_mcq(mcq)
        if valid:
            log.info(f"generate_mcq: SUCCESS via {model_used} — question: '{str(mcq.get('question',''))[:60]}...'")
            return mcq, None
        else:
            log.warning(f"generate_mcq: validation failed: {validation_err}")

    log.error(f"generate_mcq: All {max_attempts} attempts failed")
    return None, "Failed to generate a valid question after multiple attempts. Please try again."


# ─────────────────────────────────────────────
# Batch Question Set Generation (20 questions, 1 API call)
# ─────────────────────────────────────────────

def generate_mcq_set(
    topic: str,
    difficulty: str = "medium",
    q_type: str = "single",
    count: int = 20,
    prompt_template: str = "standard",
) -> tuple[list[dict] | None, str | None]:
    """
    Generate a set of {count} MCQ questions in a single API call.
    Uses MCQ_BATCH_20_PROMPT or JAVA_MCQ_BATCH_PROMPT depending on prompt_template.
    Returns (list_of_mcqs, error_message).
    Token-efficient: 1 API call instead of 20.
    """
    log.info(f"generate_mcq_set() — topic='{topic[:50]}', diff={difficulty}, type={q_type}, count={count}, template={prompt_template}")

    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    seen_keywords = get_seen_keywords(topic)
    avoid_str = ", ".join(seen_keywords[-50:]) if seen_keywords else "none"
    seed = f"{uuid.uuid4()}-{time.time()}"

    template = JAVA_MCQ_BATCH_PROMPT if prompt_template == "java" else MCQ_BATCH_20_PROMPT
    prompt = template.format(
        topic=topic,
        difficulty=difficulty,
        q_type=q_type,
        count=count,
        seed=seed,
        avoid_keywords=avoid_str,
    )
    log.debug(f"generate_mcq_set: prompt built ({len(prompt)} chars), requesting {count} questions...")

    result, err, model_used = _call_with_model_fallback(client, prompt, max_retries=2)
    if err:
        log.error(f"generate_mcq_set: API failed: {err[:300]}")
        return None, f"API Error: {err}"
    if result is None:
        return None, "No response from Gemini"

    raw = result.text
    log.debug(f"generate_mcq_set: raw response ({len(raw)} chars) via {model_used}")

    questions = parse_batch_response(raw)
    if not questions:
        log.warning(f"generate_mcq_set: parse_batch_response returned None. Raw[:300]: {raw[:300]}")
        return None, "Failed to parse question batch. The model may have returned invalid JSON — please try again."

    # Validate each question, keep valid ones
    valid_qs = []
    for i, q in enumerate(questions):
        ok, err_msg = validate_mcq(q)
        if ok:
            valid_qs.append(q)
        else:
            log.warning(f"generate_mcq_set: Q{i+1} invalid: {err_msg}")

    if not valid_qs:
        log.error("generate_mcq_set: No valid questions in the batch")
        return None, "All generated questions failed validation. Please try again."

    log.info(f"generate_mcq_set: SUCCESS — {len(valid_qs)}/{count} valid questions via {model_used}")
    return valid_qs, None



def generate_mcq_batch(
    topics: list[str],
    count: int = 5,
    difficulty_mix: str = "60% medium, 30% hard, 10% easy",
) -> tuple[list[dict] | None, str | None]:
    """
    Generate a batch of MCQs in one API call (more efficient for mock tests).
    Returns (list_of_mcqs, error_message).
    """
    log.info(f"generate_mcq_batch() called — topics={topics}, count={count}")
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    seed = f"{uuid.uuid4()}-{time.time()}"
    prompt = MOCK_TEST_BATCH_PROMPT.format(
        count=count,
        topics=", ".join(topics),
        difficulty_mix=difficulty_mix,
        seed=seed,
    )

    result, err, model_used = _call_with_model_fallback(client, prompt)
    if err:
        log.error(f"generate_mcq_batch: API error: {err[:300]}")
        return None, f"API Error: {err}"
    if result is None:
        return None, "No response from Gemini"

    questions = parse_batch_response(result.text)
    if not questions:
        log.warning(f"generate_mcq_batch: parse_batch_response returned None. Raw: {result.text[:200]}")
        return None, "Failed to parse question batch from Gemini response"

    log.info(f"generate_mcq_batch: SUCCESS via {model_used} — {len(questions)} questions parsed")
    return questions, None


# ─────────────────────────────────────────────
# Study Guide / Explanation
# ─────────────────────────────────────────────

def generate_explanation(topic: str) -> tuple[str | None, str | None]:
    """
    Generate a full study explanation for a topic.
    Returns (explanation_text, error_message).
    """
    log.info(f"generate_explanation() — topic: {topic[:60]}")
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    prompt = STUDY_EXPLANATION_PROMPT.format(topic=topic)
    result, err, model_used = _call_with_model_fallback(client, prompt)
    if err:
        log.error(f"generate_explanation: {err[:200]}")
        return None, f"API Error: {err}"
    log.info(f"generate_explanation: SUCCESS via {model_used}")
    return result.text if result else None, None


def get_chat_response(
    messages: list[dict],
    user_input: str,
) -> tuple[str | None, str | None]:
    """
    Continue a study guide chat conversation.
    messages: list of {"role": "user"|"model", "parts": [text]}
    Returns (response_text, error_message).
    """
    log.info(f"get_chat_response() — history_len={len(messages)}, input='{user_input[:60]}'")
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        parts_text = msg.get("parts", [""])
        text = parts_text[0] if isinstance(parts_text, list) and parts_text else str(parts_text)
        contents.append(types.Content(role=role, parts=[types.Part(text=text)]))

    contents.append(types.Content(role="user", parts=[types.Part(text=user_input)]))

    result, err, model_used = _call_with_model_fallback(client, contents)
    if err:
        log.error(f"get_chat_response: {err[:200]}")
        return None, f"API Error: {err}"
    log.info(f"get_chat_response: SUCCESS via {model_used}")
    return result.text if result else None, None


# ─────────────────────────────────────────────
# Interview Question Generation
# ─────────────────────────────────────────────

def get_interview_question(
    domain: str = "ML Engineering",
    difficulty: str = "medium",
) -> tuple[str | None, str | None]:
    """
    Generate one interview question.
    Returns (question_text, error_message).
    """
    log.info(f"get_interview_question() — domain={domain}, difficulty={difficulty}")
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    prompt = INTERVIEW_QUESTION_PROMPT.format(domain=domain, difficulty=difficulty)
    result, err = _call_with_retry(
        lambda: client.models.generate_content(model=MODEL_ID, contents=prompt)
    )
    if err:
        log.error(f"get_interview_question: {err[:200]}")
        return None, f"API Error: {err}"
    log.info("get_interview_question: SUCCESS")
    return result.text.strip() if result else None, None


# ─────────────────────────────────────────────
# Audio / Voice Analysis
# ─────────────────────────────────────────────

def analyze_audio_answer(
    question: str,
    audio_bytes: bytes,
    mime_type: str = "audio/wav",
) -> tuple[str | None, str | None]:
    """
    Send audio recording to Gemini for transcription + structured feedback.
    Returns (feedback_text, error_message).
    """
    log.info(f"analyze_audio_answer() — question: '{question[:60]}', audio_size={len(audio_bytes)} bytes")
    client = get_client()
    if not client:
        return None, "⚠️ Gemini API key not configured."

    prompt_text = AUDIO_FEEDBACK_PROMPT.format(question=question)
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=prompt_text),
                types.Part(inline_data=types.Blob(mime_type=mime_type, data=audio_bytes)),
            ],
        )
    ]

    result, err = _call_with_retry(
        lambda: client.models.generate_content(model=MODEL_ID, contents=contents)
    )
    if err:
        log.error(f"analyze_audio_answer: {err[:200]}")
        return None, f"API Error: {err}"
    log.info("analyze_audio_answer: SUCCESS")
    return result.text if result else None, None
