"""
Page 2 — Leaderboard
Full 7-day performance ranking table with category/type filters and per-row detail links.
"""

import streamlit as st

st.set_page_config(page_title="Leaderboard · WB Tracker", page_icon="🏆", layout="wide")

from utils import (
    inject_css, check_password, section_header,
    load_leaderboard, stock_status
)

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
st.markdown('<div class="page-title">🏆 Performance Leaderboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Ranked by estimated 7-day sales. '
    'Filter by category, type, or brand, then click a row to see its full detail page.</div>',
    unsafe_allow_html=True
)

# ── Load & prep ───────────────────────────────────────────────────────────────
df = load_leaderboard(days=7)

if df.empty:
    st.warning("⚠️ No data yet. Add products via **⚙️ Settings** and run the scraper.")
    st.stop()

df["Type"]         = df["is_own_store"].map({True: "🏪 Our Store", False: "⚔️ Competitor"})
df["Stock Status"] = df["current_stock"].apply(stock_status)
df["WB Link"]      = df["sku"].apply(lambda x: f"https://www.wildberries.ru/catalog/{x}/detail.aspx")

# ── Filters row ───────────────────────────────────────────────────────────────
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
    sel_cat = st.selectbox("Category", cats)
with col_f2:
    types = ["All", "🏪 Our Store", "⚔️ Competitor"]
    sel_type = st.selectbox("Type", types)
with col_f3:
    brands = ["All"] + sorted(df["brand"].dropna().unique().tolist())
    sel_brand = st.selectbox("Brand", brands)

# Apply filters
mask = df["sku"].notna()
if sel_cat   != "All": mask &= df["category"] == sel_cat
if sel_type  != "All": mask &= df["Type"]     == sel_type
if sel_brand != "All": mask &= df["brand"]    == sel_brand
df_filtered = df[mask].copy()

# ── Summary KPI strip ─────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Products shown",     len(df_filtered))
c2.metric("Total Est. Sales",   f"{int(df_filtered['total_sales'].sum()):,} units")
c3.metric("Total Est. Revenue", f"{int(df_filtered['estimated_revenue'].sum()):,} ₽")
c4.metric("Out-of-Stock",       int((df_filtered["current_stock"] == 0).sum()))

st.divider()

# ── Table ─────────────────────────────────────────────────────────────────────
section_header("📋", f"Results ({len(df_filtered)} items)")

# Highlight own store rows
def highlight_own(row):
    bg = "background-color: rgba(168, 85, 247, 0.1);" if row["is_own_store"] else ""
    return [bg] * len(row)

display_cols = [
    "sku", "name", "brand", "category", "Type",
    "total_sales", "avg_price", "estimated_revenue",
    "current_stock", "Stock Status", "avg_rating", "current_feedbacks",
    "WB Link"
]

st.dataframe(
    df_filtered[display_cols].style.apply(highlight_own, axis=1),
    column_config={
        "sku":                st.column_config.TextColumn("SKU"),
        "name":               st.column_config.TextColumn("Product Name"),
        "brand":              st.column_config.TextColumn("Brand"),
        "category":           st.column_config.TextColumn("Category"),
        "Type":               st.column_config.TextColumn("Type"),
        "total_sales":        st.column_config.NumberColumn("Est. Sales (7d)", format="%d"),
        "avg_price":          st.column_config.NumberColumn("Avg Price", format="%d ₽"),
        "estimated_revenue":  st.column_config.NumberColumn("Est. Revenue (7d)", format="%d ₽"),
        "current_stock":      st.column_config.NumberColumn("Stock", format="%d"),
        "Stock Status":       st.column_config.TextColumn("Status"),
        "avg_rating":         st.column_config.NumberColumn("Rating", format="%.2f ⭐"),
        "current_feedbacks":  st.column_config.NumberColumn("Reviews", format="%d"),
        "WB Link":            st.column_config.LinkColumn("WB Page", display_text="🔗 View"),
    },
    hide_index=True,
    use_container_width=True,
    height=520,
)

# ── Per-row drill-down prompt ─────────────────────────────────────────────────
st.divider()
section_header("🔍", "Drill Down into a Product")
st.caption("Select a SKU from the table above and click View Details to see its full analytics.")

sel_sku = st.selectbox(
    "Select SKU",
    options=df_filtered["sku"].tolist(),
    format_func=lambda x: f"{df_filtered.loc[df_filtered['sku']==x, 'brand'].values[0]} — "
                          f"{df_filtered.loc[df_filtered['sku']==x, 'name'].values[0][:40]} ({x})"
)

if sel_sku:
    # Store in session state so the Product page can pick it up
    if st.button("🔍 View Full Product Details →", type="primary", use_container_width=False):
        st.session_state["selected_sku"] = sel_sku
        st.switch_page("pages/4_🔍_Product.py")
