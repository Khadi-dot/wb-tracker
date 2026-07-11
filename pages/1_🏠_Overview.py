"""
Page 1 — Overview
High-level market pulse: KPI cards, top 3 movers, out-of-stock alerts, market share donut.
"""

import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Overview · WB Tracker", page_icon="🏠", layout="wide")

from utils import (
    inject_css, check_password, kpi_card, section_header,
    load_leaderboard, load_timeline, stock_status, CHART_LAYOUT
)

inject_css()

if not check_password():
    st.stop()

# ── Sidebar shared nav hint ────────────────────────────────────────────────────
st.sidebar.markdown("### 📊 WB Tracker")
st.sidebar.page_link("dashboard.py",                    label="🏠 Home")
st.sidebar.page_link("pages/1_🏠_Overview.py",          label="📊 Overview")
st.sidebar.page_link("pages/2_🏆_Leaderboard.py",       label="🏆 Leaderboard")
st.sidebar.page_link("pages/3_📈_Trends.py",            label="📈 Trends")
st.sidebar.page_link("pages/4_🔍_Product.py",           label="🔍 Product Detail")
st.sidebar.page_link("pages/5_⚙️_Settings.py",          label="⚙️ Settings")

# ── Page header ────────────────────────────────────────────────────────────────
st.markdown('<div class="page-title">🏠 Market Overview</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">High-level pulse of your tracked Wildberries market — '
    'updated with the latest scraped snapshot.</div>',
    unsafe_allow_html=True
)

# ── Load data ─────────────────────────────────────────────────────────────────
df_lb = load_leaderboard(days=7)
df_tl = load_timeline(days=30)

if df_lb.empty:
    st.warning(
        "⚠️ No tracked products yet. Go to **⚙️ Settings** to add products to your watchlist."
    )
    st.stop()

# ── KPI cards row ─────────────────────────────────────────────────────────────
total_sales   = int(df_lb["total_sales"].sum())
total_revenue = int(df_lb["estimated_revenue"].sum())
own_df        = df_lb[df_lb["is_own_store"] == True]
own_sales     = int(own_df["total_sales"].sum())
own_revenue   = int(own_df["estimated_revenue"].sum())
market_share  = (own_sales / total_sales * 100) if total_sales > 0 else 0.0
tracked_count = len(df_lb)
oos_count     = int((df_lb["current_stock"] == 0).sum())

brand_top = (
    df_lb.groupby("brand")["total_sales"].sum()
         .sort_values(ascending=False)
         .index[0]
    if total_sales > 0 else "N/A"
)

section_header("📈", "7-Day Market Pulse")

cards_html = (
    '<div class="kpi-grid">'
    + kpi_card("💰", "Market Revenue (7d)",  f"{total_revenue:,} ₽",
               f"{total_sales:,} units across {tracked_count} SKUs", "green")
    + kpi_card("🏪", "Our Store Revenue (7d)", f"{own_revenue:,} ₽",
               f"{own_sales:,} units · {market_share:.1f}% market share", "purple")
    + kpi_card("🏅", "Top Brand", brand_top,
               "by 7-day sales volume", "orange")
    + kpi_card("📦", "Tracked SKUs", str(tracked_count),
               f"{oos_count} out of stock right now", "blue")
    + kpi_card("🔴", "Out-of-Stock", str(oos_count),
               "competitor slots you can capture", "red")
    + '</div>'
)
st.markdown(cards_html, unsafe_allow_html=True)

# ── Out-of-stock alert strip ─────────────────────────────────────────────────
oos_df = df_lb[df_lb["current_stock"] == 0]
if not oos_df.empty:
    names = ", ".join(oos_df["brand"].tolist()[:5])
    if len(oos_df) > 5:
        names += f" +{len(oos_df)-5} more"
    st.markdown(
        f'<div class="alert-strip">🚨 <strong>Out-of-Stock Alert:</strong> {names}</div>',
        unsafe_allow_html=True
    )

# ── Top 3 podium ──────────────────────────────────────────────────────────────
section_header("🏆", "This Week's Top Performers")

top3 = df_lb.head(3)
medals = ["🥇", "🥈", "🥉"]
rank_cls = ["rank-1", "rank-2", "rank-3"]

if len(top3) > 0:
    cols = st.columns(min(3, len(top3)))
    for i, (_, row) in enumerate(top3.iterrows()):
        rev = int(row["estimated_revenue"])
        sales = int(row["total_sales"])
        with cols[i]:
            st.markdown(f"""<div class="podium-card {rank_cls[i]}">
<div class="podium-rank">{medals[i]}</div>
<div class="podium-name" title="{row['name']}">{row['name'][:32]}{'…' if len(row['name'])>32 else ''}</div>
<div class="podium-brand">{row['brand']} · {row['category']}</div>
<div class="podium-stat">{rev:,} ₽</div>
<div class="podium-sub">{sales:,} units · SKU {row['sku']}</div>
</div>""", unsafe_allow_html=True)
            st.page_link(
                "pages/4_🔍_Product.py",
                label="View Details →",
                use_container_width=True,
            )

# ── Market share donut ─────────────────────────────────────────────────────────
if not df_tl.empty and total_revenue > 0:
    section_header("🍩", "Market Share at a Glance")
    col_a, col_b = st.columns(2)

    with col_a:
        share_data = df_lb.groupby("is_own_store")["estimated_revenue"].sum().reset_index()
        share_data["Type"] = share_data["is_own_store"].map({True: "Our Store", False: "Competitors"})
        fig_share = px.pie(
            share_data, values="estimated_revenue", names="Type",
            title="Our Store vs Competitors (Revenue Share)",
            color_discrete_map={"Our Store": "#a855f7", "Competitors": "#3b82f6"},
            hole=0.55
        )
        fig_share.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_share, use_container_width=True)

    with col_b:
        cat_rev = df_lb.groupby("category")["estimated_revenue"].sum().reset_index()
        fig_cat = px.pie(
            cat_rev, values="estimated_revenue", names="category",
            title="Category Distribution (Revenue Share)",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hole=0.55
        )
        fig_cat.update_layout(**CHART_LAYOUT)
        st.plotly_chart(fig_cat, use_container_width=True)

# ── Quick dive prompts ────────────────────────────────────────────────────────
section_header("🔭", "Dive Deeper")
c1, c2, c3 = st.columns(3)
with c1:
    st.page_link("pages/2_🏆_Leaderboard.py", label="🏆 Full Leaderboard & Rankings", use_container_width=True)
with c2:
    st.page_link("pages/3_📈_Trends.py",       label="📈 Price & Stock Trends",        use_container_width=True)
with c3:
    st.page_link("pages/5_⚙️_Settings.py",     label="⚙️ Manage Watchlist",            use_container_width=True)
