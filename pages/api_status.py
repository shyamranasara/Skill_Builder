"""
api_status.py — Live API health check and log viewer.
Shows model status, API key info, and last 50 lines of gemini.log.
"""

import streamlit as st
from pathlib import Path
from utils.gemini_service import get_client, MODEL_FALLBACKS, _get_api_key, is_api_configured
from utils.firebase_service import log_page_visit

log_page_visit("API Status")

st.markdown("""
<h1 style='font-size:2rem; background:linear-gradient(90deg,#6C63FF,#06B6D4);
-webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
🔧 API Status & Diagnostics</h1>
<p style='color:#9CA3AF;'>Live health check for the Gemini API connection</p>
""", unsafe_allow_html=True)

# ── Model Health Check (Public) ─────────────────────────────────────────────────
st.markdown("### 🤖 Model Health Check")
st.caption("Click to test each model with a live API call")

client = get_client()
if not client:
    st.error("Cannot test — no API client (key missing)")
else:
    if st.button("⚡ Run Live Test on All Models", type="primary"):
        results = {}
        for model in MODEL_FALLBACKS:
            with st.spinner(f"Testing `{model}`..."):
                try:
                    resp = client.models.generate_content(model=model, contents="Say: PONG")
                    results[model] = ("✅ OK", resp.text.strip()[:40], None)
                except Exception as e:
                    err = str(e)
                    if "429" in err or "quota" in err.lower():
                        results[model] = ("⚠️ QUOTA", "Rate limit / quota exhausted", err[:200])
                    elif "404" in err:
                        results[model] = ("❌ NOT FOUND", "Model not available", err[:200])
                    else:
                        results[model] = ("❌ ERROR", str(e)[:60], err[:200])

        for model, (status, short, detail) in results.items():
            col1, col2 = st.columns([2, 3])
            with col1:
                st.markdown(f"**`{model}`**")
            with col2:
                st.markdown(f"{status} — {short}")
            if detail and status != "✅ OK":
                with st.expander("Full error"):
                    st.code(detail)

    else:
        st.info("Click the button above to run a live test. This makes real API calls.")

# ── API Key and Logs Security Gate (Admin Only) ─────────────────────────────────
if "api_status_authorized" not in st.session_state:
    st.session_state["api_status_authorized"] = False

if st.session_state["api_status_authorized"]:
    st.markdown("---")
    st.markdown("### 🔑 API Key Details")
    key = _get_api_key()
    if key:
        st.success(f"✅ Key found — `{key[:8]}...{key[-4:]}` (length: {len(key)})")
    else:
        st.error("❌ No API key found. Add `GEMINI_API_KEY` to `.streamlit/secrets.toml`")
        st.code('[general]\nGEMINI_API_KEY = "AIzaSy..."', language="toml")

    st.markdown("---")
    st.markdown("### 📋 Live Log (last 80 lines)")

    log_path = Path(__file__).parent.parent / "logs" / "gemini.log"

    col_r, col_c = st.columns([1, 1])
    with col_r:
        if st.button("🔄 Refresh Log"):
            st.rerun()
    with col_c:
        if st.button("🗑️ Clear Log"):
            if log_path.exists():
                log_path.write_text("", encoding="utf-8")
                st.success("Log cleared!")
                st.rerun()

    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        last_lines = lines[-80:] if len(lines) > 80 else lines
        log_text = "\n".join(last_lines)

        # Colour-code by level
        error_count = sum(1 for l in last_lines if "[ERROR]" in l)
        warn_count  = sum(1 for l in last_lines if "[WARNING]" in l)
        ok_count    = sum(1 for l in last_lines if "SUCCESS" in l)

        m1, m2, m3 = st.columns(3)
        m1.metric("✅ Successes", ok_count)
        m2.metric("⚠️ Warnings", warn_count)
        m3.metric("❌ Errors", error_count)

        st.code(log_text, language="text")
    else:
        st.warning("No log file yet — generate a question first to create it.")

    st.markdown("""<div style='color:#4B5563;font-size:0.78rem;text-align:center;padding-top:1rem;'>
    Log file: <code>logs/gemini.log</code> · Auto-updates on each API call
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("🔒 Lock Admin Console", use_container_width=True, type="secondary"):
        st.session_state["api_status_authorized"] = False
        st.rerun()

else:
    st.markdown("---")
    st.markdown("### 🔐 Admin Console Login")
    st.caption("Verify your administrative credentials to unlock the API key details and live system log files.")
    
    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        with st.form("admin_login_form", clear_on_submit=True):
            admin_email = st.text_input("📧 Admin Email", placeholder="admin@domain.com")
            admin_pass = st.text_input("🔒 Admin Password", type="password")
            submitted = st.form_submit_button("🔓 Unlock Developer Details", use_container_width=True)
            
            if submitted:
                if admin_email.strip() == "shyamran2202@gmail.com" and admin_pass == "Shyam@12345":
                    st.session_state["api_status_authorized"] = True
                    st.success("Access Granted! Loading diagnostics...")
                    import time; time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Invalid credentials. Access Denied.")
