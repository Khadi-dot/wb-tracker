"""
dashboard.py — Entry point for the wb-tracker multi-page Streamlit app.

Handles:
  - Page configuration (must be the very first Streamlit call)
  - Database initialization
  - Password authentication gate
  - Redirect to the Overview page after login
"""

import streamlit as st

from db import init_db
from utils import inject_css, check_password, GLOBAL_CSS

# ── Page config (MUST be first Streamlit call) ───────────────────────────────
st.set_page_config(
    page_title="WB Tracker",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
inject_css()

# ── DB init ───────────────────────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.error(f"⚠️ Database initialization failed: {e}")
    st.stop()

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not check_password():
    st.stop()

# ── Redirect to Overview once authenticated ──────────────────────────────────
# Streamlit automatically shows the first page in /pages on navigation,
# but we render a welcome prompt here too so users aren't confused.
st.markdown("""<div style="text-align:center; padding: 5rem 0 2rem;">
<div style="font-size:3.5rem; margin-bottom:1rem;">📊</div>
<h1 style="font-size:2rem; font-weight:800; color:#f0f6fc; margin-bottom:0.5rem;">
    WB Tracker
</h1>
<p style="color:#8b949e; max-width:480px; margin:0 auto 2rem;">
    Wildberries competitor intelligence & analytics dashboard.
    Use the sidebar to navigate between pages.
</p>
</div>""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    st.page_link("pages/1_🏠_Overview.py",     label="🏠 Overview",     use_container_width=True)
with col2:
    st.page_link("pages/2_🏆_Leaderboard.py",  label="🏆 Leaderboard",  use_container_width=True)
with col3:
    st.page_link("pages/3_📈_Trends.py",       label="📈 Trends",       use_container_width=True)

col4, col5, col6 = st.columns([1, 1, 1])
with col4:
    st.page_link("pages/4_🔍_Product.py",      label="🔍 Product Detail", use_container_width=True)
with col5:
    st.page_link("pages/5_⚙️_Settings.py",     label="⚙️ Settings",     use_container_width=True)
with col6:
    st.empty()
