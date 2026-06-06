"""
signup.py — Skill Builder account creation with Firebase Authentication.
"""

import streamlit as st
from utils.auth_service import sign_up, login_user, validate_password, is_logged_in
from utils.mcq_helper import render_custom_logo

if is_logged_in():
    st.switch_page("pages/home.py")
    st.stop()

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    render_custom_logo(alignment="center")

st.markdown("<div style='text-align:center;color:#9CA3AF;margin-bottom:2rem;'>Create your free account</div>", unsafe_allow_html=True)

_, card_col, _ = st.columns([1, 2, 1])
with card_col:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:16px;padding:2rem 2rem 1rem;
    box-shadow:0 8px 32px #6C63FF22;'>
    <h2 style='color:#E8E8F0;text-align:center;margin-bottom:0.2rem;'>Create Account 🎓</h2>
    <p style='color:#6B7280;text-align:center;font-size:0.88rem;margin-bottom:1.5rem;'>Start your AI-powered prep journey today</p>
    """, unsafe_allow_html=True)

    name     = st.text_input("👤 Full Name", placeholder="Your Name", key="su_name")
    email    = st.text_input("📧 Email", placeholder="you@example.com", key="su_email")
    password = st.text_input("🔒 Password", type="password", placeholder="Min 6 characters", key="su_pass")
    confirm  = st.text_input("🔒 Confirm Password", type="password", placeholder="Repeat password", key="su_confirm")

    # Goal selector
    goal = st.selectbox("🎯 Primary Goal", [
        "🎓 GATE CSE Preparation",
        "💼 Software Engineer Placement",
        "☕ Java Backend Developer",
        "🤖 ML Engineer",
        "📚 General Skill Building",
    ], key="su_goal")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    if st.button("✨ Create Account", use_container_width=True, type="primary"):
        if not all([name.strip(), email.strip(), password, confirm]):
            st.error("Please fill in all fields.")
        elif password != confirm:
            st.error("Passwords do not match.")
        else:
            ok, pw_err = validate_password(password)
            if not ok:
                st.error(pw_err)
            else:
                with st.spinner("Creating your account..."):
                    user, err = sign_up(email.strip(), password, name.strip())
                if err:
                    st.error(f"❌ {err}")
                else:
                    login_user(user)
                    # Store goal in session
                    st.session_state["user_goal"] = goal
                    st.session_state["login_success_redirect"] = True
                    st.success(f"🎉 Account created! Welcome, **{user['displayName']}**! Redirecting...")
                    st.balloons()

    st.markdown("<hr style='border:none;border-top:1px solid #2D2D4A;margin:1.2rem 0;'>", unsafe_allow_html=True)

    if st.button("← Already have an account? Sign In", use_container_width=True):
        st.switch_page("pages/login.py")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style='text-align:center;color:#374151;font-size:0.75rem;padding:1.5rem 0 0;'>
🔒 Secured by Firebase · Free forever on Spark plan
</div>
""", unsafe_allow_html=True)
