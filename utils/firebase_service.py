"""
firebase_service.py — Firebase Firestore implementation of all persistence.
Integrates user session state with remote Firestore database when logged in.
Falls back to local session_state when unauthenticated.
"""

import streamlit as st
from datetime import date, datetime
import logging
import threading

log = logging.getLogger("firebase_service")

# ─────────────────────────────────────────────
# DB Connection Helper
# ─────────────────────────────────────────────

def get_db():
    """Lazy-load Firestore client to prevent circular imports."""
    try:
        from utils.auth_service import get_db as auth_get_db
        return auth_get_db()
    except Exception as e:
        log.error(f"Failed to get Firestore client: {e}")
        return None


def save_to_firestore(uid: str, field_name: str, value) -> None:
    """Save a specific field to the user's Firestore document asynchronously."""
    def _write():
        db = get_db()
        if not db:
            return
        try:
            doc_ref = db.collection("users").document(uid)
            doc_ref.set({field_name: value}, merge=True)
            log.info(f"Async save of {field_name} completed.")
        except Exception as e:
            log.error(f"Error saving {field_name} to Firestore asynchronously: {e}")

    threading.Thread(target=_write, daemon=True).start()


def log_page_visit(page_name: str) -> None:
    """Track user page views and active durations in Firestore asynchronously with page change deduplication."""
    _init_state()
    user = st.session_state.get("user")
    if not user or not user.get("uid"):
        return

    uid = user["uid"]
    email = user.get("email", "unknown")
    now = datetime.now()

    # Calculate duration spent on previous page
    prev_page = st.session_state.get("telemetry_current_page")
    prev_start = st.session_state.get("telemetry_page_start")

    # Optimization: Only log if the page actually changed (reduces redundant writes on rerun)
    if prev_page == page_name:
        return

    # Update local state immediately for next calculation
    st.session_state["telemetry_current_page"] = page_name
    st.session_state["telemetry_page_start"] = now

    def _write_telemetry():
        db = get_db()
        if not db:
            return
        try:
            # 1. Log previous page duration if it exists and wasn't too long ago (< 1 hour)
            if prev_page and prev_start:
                start_dt = prev_start
                if isinstance(start_dt, str):
                    start_dt = datetime.fromisoformat(start_dt)
                duration = int((now - start_dt).total_seconds())
                if 0 < duration < 3600:
                    db.collection("telemetry").add({
                        "uid": uid,
                        "email": email,
                        "page": prev_page,
                        "event_type": "page_duration",
                        "duration_seconds": duration,
                        "timestamp": start_dt.isoformat(),
                    })
            
            # 2. Log current page view event
            db.collection("telemetry").add({
                "uid": uid,
                "email": email,
                "page": page_name,
                "event_type": "page_view",
                "timestamp": now.isoformat(),
            })
            log.info(f"Async telemetry log for page '{page_name}' completed.")
        except Exception as e:
            log.error(f"Telemetry logging failed asynchronously: {e}")

    threading.Thread(target=_write_telemetry, daemon=True).start()



def sync_firestore_to_local(uid: str) -> None:
    """Fetch user's data from Firestore and populate session_state."""
    db = get_db()
    if not db:
        return
    try:
        doc_ref = db.collection("users").document(uid)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict() or {}
            if "syllabus_progress" in data:
                st.session_state["syllabus_progress"] = data["syllabus_progress"]
            if "test_history" in data:
                st.session_state["test_history"] = data["test_history"]
            if "session_scores" in data:
                st.session_state["session_scores"] = data["session_scores"]
            if "daily_activity" in data:
                st.session_state["daily_activity"] = data["daily_activity"]
            if "communication_sessions" in data:
                st.session_state["communication_sessions"] = data["communication_sessions"]
            log.info(f"Successfully synced Firestore data for user {uid}")
    except Exception as e:
        log.error(f"Error syncing Firestore to local for {uid}: {e}")

# ─────────────────────────────────────────────
# State Initialization
# ─────────────────────────────────────────────

def _init_state():
    """Initialize all required session_state keys if missing."""
    defaults = {
        "syllabus_progress": {},       # {subject: {topic: bool}}
        "test_history": [],            # [{score, total, breakdown, timestamp}]
        "session_scores": {},          # {topic: {correct: int, total: int}}
        "streak_data": {},             # {date_str: int questions_answered}
        "communication_sessions": [],  # [{question, feedback, score, timestamp}]
        "daily_activity": {},          # {date_str: count}
        "firestore_synced": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

    # Trigger async sync if user is logged in but firestore_synced is False
    user = st.session_state.get("user")
    if user and not st.session_state.get("firestore_synced"):
        st.session_state["firestore_synced"] = True
        uid = user.get("uid")
        if uid:
            sync_firestore_to_local(uid)


# ─────────────────────────────────────────────
# Syllabus Progress
# ─────────────────────────────────────────────

def save_syllabus_progress(subject: str, topic: str, checked: bool) -> None:
    """Mark a syllabus topic as complete/incomplete."""
    _init_state()
    if subject not in st.session_state.syllabus_progress:
        st.session_state.syllabus_progress[subject] = {}
    st.session_state.syllabus_progress[subject][topic] = checked

    user = st.session_state.get("user")
    if user and user.get("uid"):
        save_to_firestore(user["uid"], "syllabus_progress", st.session_state.syllabus_progress)


def get_syllabus_progress() -> dict:
    """Return all saved syllabus checkbox states."""
    _init_state()
    return st.session_state.syllabus_progress


def get_subject_completion(subject: str, total_topics: int) -> float:
    """Return completion percentage for a subject (0.0 to 1.0)."""
    _init_state()
    progress = st.session_state.syllabus_progress.get(subject, {})
    if total_topics == 0:
        return 0.0
    done = sum(1 for v in progress.values() if v)
    return done / total_topics


def get_overall_completion(syllabus: dict, exam_prefix: str = "") -> float:
    """Return overall syllabus completion percentage."""
    _init_state()
    total, done = 0, 0
    for subject, data in syllabus.items():
        topics = data.get("topics", data.get("subtopics", []))
        total += len(topics)
        key = f"{exam_prefix}::{subject}" if exam_prefix else subject
        progress = st.session_state.syllabus_progress.get(key, {})
        done += sum(1 for t in topics if progress.get(t, False))
    return (done / total) if total > 0 else 0.0


# ─────────────────────────────────────────────
# Test / Score History
# ─────────────────────────────────────────────

def save_test_result(score: int, total: int, breakdown: dict) -> None:
    """Save a completed mock test result."""
    _init_state()
    st.session_state.test_history.append({
        "score": score,
        "total": total,
        "percentage": round(score / total * 100, 1) if total > 0 else 0,
        "breakdown": breakdown,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    user = st.session_state.get("user")
    if user and user.get("uid"):
        save_to_firestore(user["uid"], "test_history", st.session_state.test_history)


def get_test_history() -> list:
    """Return all mock test results."""
    _init_state()
    return st.session_state.test_history


def get_best_score() -> dict | None:
    """Return the best test result."""
    _init_state()
    history = st.session_state.test_history
    if not history:
        return None
    return max(history, key=lambda x: x["percentage"])


# ─────────────────────────────────────────────
# Session Scores (per MCQ page)
# ─────────────────────────────────────────────

def record_answer(topic: str, is_correct: bool) -> None:
    """Record a question answer for a given topic."""
    _init_state()
    if topic not in st.session_state.session_scores:
        st.session_state.session_scores[topic] = {"correct": 0, "total": 0}
    st.session_state.session_scores[topic]["total"] += 1
    if is_correct:
        st.session_state.session_scores[topic]["correct"] += 1

    # Track daily activity
    today = str(date.today())
    st.session_state.daily_activity[today] = (
        st.session_state.daily_activity.get(today, 0) + 1
    )

    user = st.session_state.get("user")
    if user and user.get("uid"):
        save_to_firestore(user["uid"], "session_scores", st.session_state.session_scores)
        save_to_firestore(user["uid"], "daily_activity", st.session_state.daily_activity)


def record_answers_batch(topic: str, results: list[bool]) -> None:
    """Record multiple question answers in a single batch, updating Firestore once."""
    _init_state()
    if not results:
        return

    if topic not in st.session_state.session_scores:
        st.session_state.session_scores[topic] = {"correct": 0, "total": 0}

    for is_correct in results:
        st.session_state.session_scores[topic]["total"] += 1
        if is_correct:
            st.session_state.session_scores[topic]["correct"] += 1

    # Track daily activity
    today = str(date.today())
    st.session_state.daily_activity[today] = (
        st.session_state.daily_activity.get(today, 0) + len(results)
    )

    user = st.session_state.get("user")
    if user and user.get("uid"):
        save_to_firestore(user["uid"], "session_scores", st.session_state.session_scores)
        save_to_firestore(user["uid"], "daily_activity", st.session_state.daily_activity)



def get_topic_score(topic: str) -> dict:
    """Return score dict {correct, total} for a topic."""
    _init_state()
    return st.session_state.session_scores.get(topic, {"correct": 0, "total": 0})


def get_all_scores() -> dict:
    """Return all session scores."""
    _init_state()
    return st.session_state.session_scores


def get_total_questions_today() -> int:
    """Return total questions answered today."""
    _init_state()
    today = str(date.today())
    return st.session_state.daily_activity.get(today, 0)


# ─────────────────────────────────────────────
# Streak Tracking
# ─────────────────────────────────────────────

def get_streak() -> int:
    """Calculate current consecutive-day streak."""
    _init_state()
    activity = st.session_state.daily_activity
    if not activity:
        return 0
    streak = 0
    current = date.today()
    while str(current) in activity and activity[str(current)] > 0:
        streak += 1
        current = date.fromordinal(current.toordinal() - 1)
    return streak


# ─────────────────────────────────────────────
# Communication Sessions
# ─────────────────────────────────────────────

def save_communication_session(question: str, feedback: str, score: int | None) -> None:
    """Save one interview communication session."""
    _init_state()
    st.session_state.communication_sessions.append({
        "question": question,
        "feedback": feedback,
        "score": score,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })

    user = st.session_state.get("user")
    if user and user.get("uid"):
        save_to_firestore(user["uid"], "communication_sessions", st.session_state.communication_sessions)


def get_communication_sessions() -> list:
    """Return all saved communication sessions."""
    _init_state()
    return st.session_state.communication_sessions
