"""
app.py — Skill Builder · Entry point.
Handles navigation, shared sidebar, auth gate, and branding.
"""

import streamlit as st
from utils.firebase_service import _init_state, get_streak, get_total_questions_today
from utils.question_hash import get_total_seen
from utils.gemini_service import is_api_configured
from utils.mcq_helper import render_custom_logo

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Skill Builder — AI-Powered Learning",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #0E0E1A; border-right: 1px solid #2D2D4A; }

/* Button glow */
.stButton > button { transition: all 0.2s ease; }
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(108,99,255,0.3); }

/* Progress bar */
.stProgress > div > div > div > div { background: linear-gradient(90deg, #6C63FF, #06B6D4); }

/* Nav items */
[data-testid="stSidebarNavItems"] a { border-radius: 8px; margin: 2px 0; transition: background 0.15s; }
[data-testid="stSidebarNavItems"] a:hover { background: #1A1A2E !important; }

/* Ace editor frame */
.ace-container { border-radius: 8px; overflow: hidden; border: 1px solid #2D2D4A; }
</style>
""", unsafe_allow_html=True)

# ── Initialize state ───────────────────────────────────────────────────────────
_init_state()

# Initialize CookieManager globally so it is always in the render tree
import extra_streamlit_components as stx
cookie_manager = stx.CookieManager(key="sb_cookie_manager")
st.session_state["cookie_manager"] = cookie_manager

# Handle deferred login redirects first
if st.session_state.get("login_success_redirect"):
    st.session_state.pop("login_success_redirect", None)
    st.switch_page("pages/home.py")
    st.stop()

# ── Auth gate — redirect unauthenticated users ─────────────────────────────────
# NOTE: Set ENABLE_AUTH = True once Firebase Web API Key is configured in secrets.toml
ENABLE_AUTH = True   # ← Change to True after adding FIREBASE_WEB_API_KEY

if ENABLE_AUTH:
    from utils.auth_service import is_logged_in, login_user
    
    # Try cookie-based auto-login first
    if not is_logged_in():
        try:
            import json
            saved_session = cookie_manager.get("sb_session")
            if saved_session:
                if isinstance(saved_session, str):
                    user_dict = json.loads(saved_session)
                else:
                    user_dict = saved_session
                
                if user_dict and "uid" in user_dict:
                    login_user(user_dict)
                    st.rerun()
        except Exception as e:
            pass

    if not is_logged_in():
        # Only allow auth pages without login
        auth_pages = st.navigation([
            st.Page("pages/login.py",          title="Sign In",           icon="🔐", default=True),
            st.Page("pages/signup.py",          title="Create Account",    icon="📝"),
            st.Page("pages/forgot_password.py", title="Reset Password",    icon="🔑"),
        ], position="hidden")
        auth_pages.run()
        st.stop()

# ── Navigation ─────────────────────────────────────────────────────────────────
pages = st.navigation(
    {
        "🏠 Home": [
            st.Page("pages/home.py",               title="Dashboard",              icon="🏠", default=True),
            st.Page("pages/syllabus_tracker.py",   title="Syllabus Tracker",       icon="📚"),
        ],
        "📚 GATE Preparation": [
            st.Page("pages/cs_mcq.py",             title="CS Core MCQs",           icon="💻"),
            st.Page("pages/aptitude_mcq.py",       title="Aptitude Questions",     icon="🧮"),
            st.Page("pages/english_mcq.py",        title="English MCQs",           icon="📝"),
        ],
        "🏛️ Government Exams": [
            st.Page("pages/govt_mcq.py",           title="Govt Exam MCQs",         icon="🏛️"),
        ],
        "🤖 ML Engineering": [
            st.Page("pages/ml_mcq.py",             title="ML Engineering MCQs",    icon="🤖"),
        ],
        "☕ Java Backend": [
            st.Page("pages/java_mcq.py",           title="Java & Spring Boot MCQs",icon="☕"),
        ],
        "🏆 Competitive Programming": [
            st.Page("pages/competitive_mcq.py",    title="CP Theory MCQs",         icon="📊"),
            st.Page("pages/coding_ground.py",      title="Coding Ground",          icon="💻"),
        ],
        "🎯 Practice & Test": [
            st.Page("pages/mock_test.py",          title="Mock Test",              icon="🎯"),
            st.Page("pages/study_guide.py",        title="Study Guide",            icon="📖"),
            st.Page("pages/communication.py",      title="Communication Practice", icon="🎤"),
        ],
        "⚙️ Settings": [
            st.Page("pages/api_status.py",         title="API Status",             icon="🔧"),
            st.Page("pages/login.py",              title="Login / Account",        icon="👤"),
        ],
    },
    position="sidebar",
)

# ── Shared Sidebar ─────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    render_custom_logo(alignment="flex-start")

    st.markdown("<div style='border-bottom:1px solid #2D2D4A;margin:0.5rem 0;'></div>", unsafe_allow_html=True)

    # User info if logged in
    if ENABLE_AUTH:
        try:
            from utils.auth_service import get_current_user, logout
            user = get_current_user()
            if user:
                st.markdown(f"""
                <div style='background:#1A1A2E;border-radius:8px;padding:0.6rem 0.8rem;
                border:1px solid #2D2D4A;margin-bottom:0.5rem;'>
                <p style='color:#A78BFA;font-size:0.8rem;margin:0;font-weight:600;'>👤 {user.get('displayName','User')}</p>
                <p style='color:#6B7280;font-size:0.72rem;margin:0;'>{user.get('email','')}</p>
                </div>""", unsafe_allow_html=True)
                if st.button("🚪 Sign Out", use_container_width=True):
                    logout()
                    st.rerun()
        except Exception:
            pass

    # API Status
    if is_api_configured():
        st.success("🟢 Gemini API connected", icon=None)
    else:
        st.error("🔴 API key missing")
        st.caption("Add key to `.streamlit/secrets.toml`")

    st.markdown("---")

    # Session stats
    streak   = get_streak()
    today_q  = get_total_questions_today()
    total_seen = get_total_seen()

    st.markdown(f"""
    <div style='background:#1A1A2E;border-radius:10px;padding:0.9rem 1rem;border:1px solid #2D2D4A;'>
    <p style='color:#9CA3AF;font-size:0.72rem;margin:0 0 0.5rem;letter-spacing:0.05em;'>SESSION STATS</p>
    <p style='color:#E8E8F0;margin:0.25rem 0;font-size:0.88rem;'>🔥 Streak: <b style='color:#F59E0B;'>{streak} days</b></p>
    <p style='color:#E8E8F0;margin:0.25rem 0;font-size:0.88rem;'>📅 Today: <b style='color:#06B6D4;'>{today_q} questions</b></p>
    <p style='color:#E8E8F0;margin:0.25rem 0;font-size:0.88rem;'>🔢 Total seen: <b style='color:#6C63FF;'>{total_seen}</b></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style='text-align:center;color:#374151;font-size:0.7rem;padding:1rem 0 0;'>
    ⚡ Skill Builder · AI-Powered · $0/month
    </div>""", unsafe_allow_html=True)

# ── Run selected page ──────────────────────────────────────────────────────────
pages.run()
