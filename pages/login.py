"""
login.py — Beautiful Skill Builder login page with Firebase Authentication.
"""

import streamlit as st
from utils.auth_service import sign_in, login_user, is_logged_in, logout
from utils.mcq_helper import render_custom_logo

# ── Handle Logged In State Redirection or Profile View ────────────────────────
if is_logged_in():
    # Show Account profile details since they manually clicked Settings -> Login/Account
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        render_custom_logo(alignment="center")

    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    _, card_col, _ = st.columns([1, 2, 1])
    with card_col:
        user = st.session_state["user"]
        st.markdown(f"""
        <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
        border:1px solid #2D2D4A;border-radius:16px;padding:2rem 2rem 1.5rem;
        box-shadow:0 8px 32px #6C63FF22;'>
        <h2 style='color:#E8E8F0;text-align:center;margin-bottom:0.2rem;'>Your Account 👤</h2>
        <p style='color:#6B7280;text-align:center;font-size:0.88rem;margin-bottom:1.5rem;'>Logged in profile status</p>
        <div style='border-bottom:1px solid #2D2D4A; margin-bottom:1rem;'></div>
        <p style='color:#E8E8F0; margin-bottom:0.5rem; font-size: 0.95rem;'><b>Name:</b> {user.get('displayName', 'User')}</p>
        <p style='color:#E8E8F0; margin-bottom:0.5rem; font-size: 0.95rem;'><b>Email:</b> {user.get('email', '')}</p>
        <p style='color:#E8E8F0; margin-bottom:1.5rem; font-size: 0.95rem;'><b>UID:</b> <code style='font-size:0.75rem; color:#A78BFA;'>{user.get('uid', '')}</code></p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Sign Out & Disconnect", use_container_width=True, type="primary"):
            logout()
            st.rerun()
    st.stop()

# ── Styled Logo + Header ───────────────────────────────────────────────────────
col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    render_custom_logo(alignment="center")

st.markdown("""
<div style='text-align:center;margin-bottom:2rem;'>
<p style='color:#9CA3AF;font-size:1rem;'>AI-Powered GATE & Job Interview Prep</p>
</div>
""", unsafe_allow_html=True)

# ── Login Card ────────────────────────────────────────────────────────────────
_, card_col, _ = st.columns([1, 2, 1])
with card_col:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:16px;padding:2rem 2rem 1rem;
    box-shadow:0 8px 32px #6C63FF22;'>
    <h2 style='color:#E8E8F0;text-align:center;margin-bottom:0.2rem;'>Welcome Back 👋</h2>
    <p style='color:#6B7280;text-align:center;font-size:0.88rem;margin-bottom:1.5rem;'>Sign in to continue your learning journey</p>
    """, unsafe_allow_html=True)

    email    = st.text_input("📧 Email", placeholder="you@example.com", key="li_email")
    password = st.text_input("🔒 Password", type="password", placeholder="••••••••", key="li_pass")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    if st.button("🚀 Sign In", use_container_width=True, type="primary"):
        if not email or not password:
            st.error("Please enter your email and password.")
        else:
            with st.spinner("Signing in..."):
                user, err = sign_in(email.strip(), password)
            if err:
                st.error(f"❌ {err}")
            else:
                login_user(user)
                st.session_state["login_success_redirect"] = True
                st.success(f"✅ Welcome back, **{user['displayName']}**! Redirecting...")

    st.markdown("""
    <hr style='border:none;border-top:1px solid #2D2D4A;margin:1.2rem 0;'>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📝 Create Account", use_container_width=True):
            st.switch_page("pages/signup.py")
    with c2:
        if st.button("🔑 Forgot Password?", use_container_width=True):
            st.switch_page("pages/forgot_password.py")

    st.markdown("</div>", unsafe_allow_html=True)

# ── Security note ─────────────────────────────────────────────────────────────
st.markdown("""
<div style='text-align:center;color:#374151;font-size:0.75rem;padding:1.5rem 0 0;'>
🔒 Secured by Firebase Authentication · Your data is private and encrypted
</div>
""", unsafe_allow_html=True)
