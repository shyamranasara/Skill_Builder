"""
forgot_password.py — Password reset via Firebase Authentication.
"""

import streamlit as st
from utils.auth_service import reset_password
from utils.mcq_helper import render_custom_logo

col_l, col_c, col_r = st.columns([1, 2, 1])
with col_c:
    render_custom_logo(alignment="center")

_, card_col, _ = st.columns([1, 2, 1])
with card_col:
    st.markdown("""
    <div style='background:linear-gradient(135deg,#1A1A2E,#16213E);
    border:1px solid #2D2D4A;border-radius:16px;padding:2rem 2rem 1rem;
    box-shadow:0 8px 32px #6C63FF22;'>
    <h2 style='color:#E8E8F0;text-align:center;margin-bottom:0.2rem;'>Reset Password 🔑</h2>
    <p style='color:#6B7280;text-align:center;font-size:0.88rem;margin-bottom:1.5rem;'>
    Enter your email and we'll send a reset link</p>
    """, unsafe_allow_html=True)

    email = st.text_input("📧 Your Email", placeholder="you@example.com", key="fp_email")

    if st.button("📨 Send Reset Link", use_container_width=True, type="primary"):
        if not email.strip():
            st.error("Please enter your email address.")
        else:
            with st.spinner("Sending reset email..."):
                ok, err = reset_password(email.strip())
            if err:
                st.error(f"❌ {err}")
            else:
                st.success("✅ Password reset email sent! Check your inbox.")
                st.info("💡 Check your spam folder if you don't see it within 2 minutes.")

    st.markdown("<hr style='border:none;border-top:1px solid #2D2D4A;margin:1.2rem 0;'>", unsafe_allow_html=True)

    if st.button("← Back to Sign In", use_container_width=True):
        st.switch_page("pages/login.py")

    st.markdown("</div>", unsafe_allow_html=True)
