"""
Page 5 — Settings
Watchlist management: add/remove products, classify as own store, trigger scraper.
"""

import streamlit as st

st.set_page_config(page_title="Settings · WB Tracker", page_icon="⚙️", layout="wide")

from utils import (
    inject_css, check_password, section_header,
    extract_sku, add_tracked_item, remove_tracked_item,
    set_own_store_flag, load_tracked_items
)
from scraper import run_scraper

inject_css()
if not check_password():
    st.stop()

st.sidebar.markdown("### 📊 WB Tracker")
st.sidebar.page_link("dashboard.py",                    label="🏠 Home")
st.sidebar.page_link("pages/1_🏠_Overview.py",          label="📊 Overview")
st.sidebar.page_link("pages/2_🏆_Leaderboard.py",       label="🏆 Leaderboard")
st.sidebar.page_link("pages/3_📈_Trends.py",            label="📈 Trends")
st.sidebar.page_link("pages/4_🔍_Product.py",           label="🔍 Product Detail")
st.sidebar.page_link("pages/5_⚙️_Settings.py",          label="⚙️ Settings")

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">⚙️ Settings & Watchlist</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Manage tracked products, classify which are yours vs competitors, '
    'and trigger the live scraper.</div>',
    unsafe_allow_html=True
)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION A — Add new product
# ─────────────────────────────────────────────────────────────────────────────
section_header("➕", "Track a New Product")

with st.form("add_product_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
    with col1:
        input_val = st.text_input(
            "SKU or Wildberries URL",
            placeholder="e.g. 173854692  or  https://www.wildberries.ru/catalog/173854692/detail.aspx"
        )
    with col2:
        cat = st.selectbox(
            "Category",
            options=["T-shirts", "Longsleeves", "Underwear", "Shirts", "Hoodies", "Other"]
        )
    with col3:
        is_own = st.checkbox("My Store", value=False,
                             help="Check this if this SKU belongs to your own store.")
    with col4:
        st.markdown("<div style='margin-top:1.6rem;'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button("Track ➕", use_container_width=True, type="primary")

    if submitted:
        sku = extract_sku(input_val)
        if not sku:
            st.error("❌ Could not extract a valid SKU from the input. Please paste a Wildberries URL or enter a numeric SKU.")
        else:
            ok, v1, v2 = add_tracked_item(sku, cat, is_own=is_own)
            if ok:
                st.success(f"✅ Now tracking **{v2}** — *{v1}* (SKU: {sku})")
                st.rerun()
            else:
                st.error(f"❌ Error adding SKU {sku}: {v1}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION B — Active watchlist management
# ─────────────────────────────────────────────────────────────────────────────
section_header("📋", "Active Watchlist")

items = load_tracked_items()

if not items:
    st.info("📭 No products tracked yet. Add your first product above.")
else:
    # Column headers
    hcol = st.columns([1.2, 2.5, 1.5, 1.2, 1.2, 1])
    hcol[0].markdown("**SKU**")
    hcol[1].markdown("**Product Name**")
    hcol[2].markdown("**Brand**")
    hcol[3].markdown("**Category**")
    hcol[4].markdown("**Our Store?**")
    hcol[5].markdown("**Action**")

    st.divider()

    for sku, name, brand, category, is_own in items:
        cols = st.columns([1.2, 2.5, 1.5, 1.2, 1.2, 1])
        cols[0].code(sku)
        cols[1].write(name[:45] + ("…" if len(name) > 45 else ""))
        cols[2].write(brand)
        cols[3].write(category)

        # Toggle own-store flag inline
        new_val = cols[4].checkbox(
            "Own",
            value=bool(is_own),
            key=f"own_{sku}",
            label_visibility="collapsed",
        )
        if new_val != bool(is_own):
            set_own_store_flag(sku, new_val)
            st.rerun()

        # Remove button
        if cols[5].button("🗑️", key=f"del_{sku}", help=f"Remove SKU {sku}"):
            if remove_tracked_item(sku):
                st.success(f"Removed SKU {sku}")
                st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION C — Scraper control
# ─────────────────────────────────────────────────────────────────────────────
section_header("🔄", "Scraper Control")

st.markdown("""
The scraper fetches live data from the Wildberries API for every tracked SKU and saves a daily snapshot.
Run it manually here, or set up a cron job to run `scraper.py` daily.
""")

col_btn, col_info = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Run Scraper Now", type="primary", use_container_width=True):
        with st.spinner("Running scraper… this may take a minute."):
            try:
                run_scraper()
                st.success("✅ Scraper completed successfully! Refresh any chart page to see updated data.")
            except Exception as e:
                st.error(f"❌ Scraper error: {e}")

with col_info:
    st.info(
        "💡 **Tip:** For automated daily tracking, add a cron job:\n\n"
        "`0 8 * * * cd /path/to/wb-tracker && python scraper.py`"
    )
