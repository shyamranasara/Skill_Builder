"""
auth_service.py — Firebase Authentication via REST API + firebase-admin token verification.
Handles: sign-up, sign-in, password reset, token verification, session management.
"""

import requests
import logging
import streamlit as st
import firebase_admin
from firebase_admin import credentials, auth as fb_auth, firestore

log = logging.getLogger("auth_service")

# ── Firebase Admin SDK Init ───────────────────────────────────────────────────

def _get_firebase_app():
    """Initialize (or return existing) Firebase Admin app."""
    if not firebase_admin._apps:
        try:
            fb_config = dict(st.secrets["firebase"])
            # Fix private_key newlines (TOML may escape them)
            fb_config["private_key"] = fb_config["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(fb_config)
            firebase_admin.initialize_app(cred)
            log.info("Firebase Admin initialized OK")
        except Exception as e:
            log.error(f"Firebase Admin init failed: {e}")
            return None
    return firebase_admin.get_app()


def _get_web_api_key() -> str | None:
    """Return Firebase Web API Key from secrets."""
    key = st.secrets.get("FIREBASE_WEB_API_KEY", "")
    if not key or key == "YOUR_FIREBASE_WEB_API_KEY_HERE":
        return None
    return key


# ── REST Auth Helpers ─────────────────────────────────────────────────────────

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def sign_up(email: str, password: str, display_name: str = "") -> tuple[dict | None, str | None]:
    """
    Create a new user with email + password.
    Returns (user_dict, error_message).
    user_dict = {uid, email, displayName, idToken, refreshToken}
    """
    web_key = _get_web_api_key()
    if not web_key:
        # Fallback: use firebase-admin to create user (no idToken returned)
        return _admin_sign_up(email, password, display_name)

    try:
        resp = requests.post(
            f"{FIREBASE_AUTH_BASE}:signUp?key={web_key}",
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            msg = data["error"].get("message", "Sign-up failed")
            return None, _friendly_error(msg)

        # Update display name
        if display_name:
            requests.post(
                f"{FIREBASE_AUTH_BASE}:update?key={web_key}",
                json={"idToken": data["idToken"], "displayName": display_name, "returnSecureToken": True},
                timeout=10,
            )
        return {
            "uid": data["localId"],
            "email": data["email"],
            "displayName": display_name or data.get("email", "").split("@")[0],
            "idToken": data["idToken"],
            "refreshToken": data["refreshToken"],
        }, None

    except Exception as e:
        log.error(f"sign_up error: {e}")
        return None, f"Network error: {e}"


def _admin_sign_up(email: str, password: str, display_name: str = "") -> tuple[dict | None, str | None]:
    """Fallback sign-up using firebase-admin SDK."""
    try:
        _get_firebase_app()
        user = fb_auth.create_user(email=email, password=password, display_name=display_name or email.split("@")[0])
        return {
            "uid": user.uid,
            "email": user.email,
            "displayName": user.display_name or email.split("@")[0],
            "idToken": None,
        }, None
    except Exception as e:
        err = str(e)
        return None, _friendly_error(err)


def sign_in(email: str, password: str) -> tuple[dict | None, str | None]:
    """
    Sign in with email + password via Firebase REST API.
    Returns (user_dict, error_message).
    """
    web_key = _get_web_api_key()
    if not web_key:
        return None, "⚠️ Firebase Web API Key not configured. Add FIREBASE_WEB_API_KEY to .streamlit/secrets.toml"

    try:
        resp = requests.post(
            f"{FIREBASE_AUTH_BASE}:signInWithPassword?key={web_key}",
            json={"email": email, "password": password, "returnSecureToken": True},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            msg = data["error"].get("message", "Sign-in failed")
            return None, _friendly_error(msg)

        return {
            "uid": data["localId"],
            "email": data["email"],
            "displayName": data.get("displayName") or data["email"].split("@")[0],
            "idToken": data["idToken"],
            "refreshToken": data["refreshToken"],
        }, None

    except Exception as e:
        log.error(f"sign_in error: {e}")
        return None, f"Network error: {e}"


def reset_password(email: str) -> tuple[bool, str | None]:
    """Send password reset email. Returns (success, error_message)."""
    web_key = _get_web_api_key()
    if not web_key:
        # Fallback: use admin SDK
        try:
            _get_firebase_app()
            link = fb_auth.generate_password_reset_link(email)
            return True, None
        except Exception as e:
            return False, str(e)

    try:
        resp = requests.post(
            f"{FIREBASE_AUTH_BASE}:sendOobCode?key={web_key}",
            json={"requestType": "PASSWORD_RESET", "email": email},
            timeout=10,
        )
        data = resp.json()
        if "error" in data:
            return False, _friendly_error(data["error"].get("message", "Failed"))
        return True, None
    except Exception as e:
        return False, f"Network error: {e}"


# ── Session State Helpers ─────────────────────────────────────────────────────

def get_current_user() -> dict | None:
    """Return current user from session_state, or None if not logged in."""
    return st.session_state.get("user")


def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def login_user(user_dict: dict):
    """Store user in session_state and set persistence cookie."""
    st.session_state["user"] = user_dict
    st.session_state["firestore_synced"] = True
    log.info(f"User logged in: {user_dict.get('email')} (uid: {user_dict.get('uid')})")
    
    # Save session cookie
    try:
        import json
        import datetime
        
        cookie_manager = st.session_state.get("cookie_manager")
        if not cookie_manager:
            import extra_streamlit_components as stx
            cookie_manager = stx.CookieManager()
        
        expires = datetime.datetime.now() + datetime.timedelta(days=30)
        cookie_manager.set("sb_session", json.dumps(user_dict), expires_at=expires)
    except Exception as e:
        log.error(f"Failed to set session cookie: {e}")

    try:
        from utils.firebase_service import sync_firestore_to_local
        sync_firestore_to_local(user_dict.get("uid"))
    except Exception as e:
        log.error(f"Failed to sync Firestore on login: {e}")


def logout():
    """Clear user session, persistence cookie, and progress keys."""
    try:
        cookie_manager = st.session_state.get("cookie_manager")
        if not cookie_manager:
            import extra_streamlit_components as stx
            cookie_manager = stx.CookieManager()
        cookie_manager.delete("sb_session")
    except Exception as e:
        log.error(f"Failed to delete session cookie: {e}")

    st.session_state.pop("user", None)
    st.session_state.pop("user_data", None)
    st.session_state.pop("firestore_synced", None)
    st.session_state.pop("syllabus_progress", None)
    st.session_state.pop("test_history", None)
    st.session_state.pop("session_scores", None)
    st.session_state.pop("streak_data", None)
    st.session_state.pop("communication_sessions", None)
    st.session_state.pop("daily_activity", None)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 6:
        return False, "Password must be at least 6 characters"
    return True, ""


def _friendly_error(code: str) -> str:
    """Convert Firebase error codes to user-friendly messages."""
    m = {
        "EMAIL_EXISTS": "This email is already registered. Please sign in.",
        "INVALID_EMAIL": "Invalid email address format.",
        "WEAK_PASSWORD : Password should be at least 6 characters": "Password must be at least 6 characters.",
        "EMAIL_NOT_FOUND": "No account found with this email.",
        "INVALID_PASSWORD": "Incorrect password. Please try again.",
        "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
        "USER_DISABLED": "This account has been disabled.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many failed attempts. Please try again later.",
        "OPERATION_NOT_ALLOWED": "Email/password sign-in is not enabled in Firebase Console.",
    }
    return m.get(code, code.replace("_", " ").title())


# ── Firestore Helpers (after init) ───────────────────────────────────────────

def get_db():
    """Return Firestore client, initializing Firebase if needed."""
    _get_firebase_app()
    try:
        return firestore.client()
    except Exception as e:
        log.error(f"Firestore client error: {e}")
        return None


def save_user_profile(uid: str, data: dict):
    """Save/update user profile in Firestore users/{uid}."""
    db = get_db()
    if db:
        db.collection("users").document(uid).set(data, merge=True)


def get_user_profile(uid: str) -> dict:
    """Get user profile from Firestore."""
    db = get_db()
    if not db:
        return {}
    doc = db.collection("users").document(uid).get()
    return doc.to_dict() if doc.exists else {}
