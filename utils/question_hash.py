"""
question_hash.py — In-memory question hash store to prevent repeated questions.
Uses session_state as the backing store (Firebase can replace this later).
"""

import hashlib
import streamlit as st


def _get_hash_store() -> dict:
    """Return the hash store from session_state, initializing if needed."""
    if "question_hash_store" not in st.session_state:
        st.session_state.question_hash_store = {}
    return st.session_state.question_hash_store


def get_question_hash(question: str, correct: list) -> str:
    """Generate a stable MD5 hash for a question to detect duplicates."""
    content = question[:80].strip().lower() + str(sorted(correct))
    return hashlib.md5(content.encode()).hexdigest()


def save_hash(topic: str, question_hash: str, keyword: str) -> None:
    """Save a question hash to the store so it won't be generated again."""
    store = _get_hash_store()
    if topic not in store:
        store[topic] = {}
    store[topic][question_hash] = keyword


def is_duplicate(topic: str, question_hash: str) -> bool:
    """Check whether a question has already been seen for this topic."""
    store = _get_hash_store()
    return topic in store and question_hash in store[topic]


def get_seen_keywords(topic: str) -> list[str]:
    """Return list of keyword tags already seen for a topic."""
    store = _get_hash_store()
    if topic not in store:
        return []
    return list(store[topic].values())


def clear_topic_history(topic: str) -> None:
    """Clear question history for a specific topic."""
    store = _get_hash_store()
    if topic in store:
        del store[topic]


def get_total_seen() -> int:
    """Return total number of unique questions seen across all topics."""
    store = _get_hash_store()
    return sum(len(v) for v in store.values())


def get_topic_stats() -> dict:
    """Return per-topic question counts."""
    store = _get_hash_store()
    return {topic: len(hashes) for topic, hashes in store.items()}
