"""
Page 3 — Trends
Dedicated chart workspace: stock dynamics, price fluctuations, daily sales, price-vs-sales bubble.
"""

import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Trends · WB Tracker", page_icon="📈", layout="wide")

from utils import (
    inject_css, check_password, section_header,
    load_timeline, CHART_LAYOUT
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
st.markdown('<div class="page-title">📈 Market Trends</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Visualise price movements, stock dynamics, and estimated daily sales '
    'across all tracked products over time.</div>',
    unsafe_allow_html=True
)

# ── Controls row ──────────────────────────────────────────────────────────────
col_d, col_p = st.columns([1, 2])
with col_d:
    day_window = st.radio(
        "Date window",
        options=[7, 14, 30],
        format_func=lambda x: f"Last {x} days",
        horizontal=True,
        index=2,
    )

df = load_timeline(days=day_window)

if df.empty:
    st.info("ℹ️ No historical data yet. Run the scraper in ⚙️ Settings to collect snapshots.")
    st.stop()

# Build product labels
df["label"] = df.apply(
    lambda r: f"{'[Ours] ' if r['is_own_store'] else ''}{r['brand']} ({r['sku']})", axis=1
)

# Product filter
with col_p:
    all_labels = sorted(df["label"].unique().tolist())
    sel_labels = st.multiselect(
        "Filter products (leave empty = show all)",
        options=all_labels,
        default=[],
    )

if sel_labels:
    df = df[df["label"].isin(sel_labels)]

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Stock Dynamics
# TAB 2: Price Fluctuations
# TAB 3: Daily Sales
# TAB 4: Price vs Sales Bubble
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📦 Stock Dynamics",
    "💸 Price Fluctuations",
    "📊 Daily Sales",
    "🫧 Price vs Sales Bubble",
])

with tab1:
    section_header("📦", "Stock Level Trends")
    st.caption("Falling lines = sales happening. A line hitting 0 = competitor out-of-stock opportunity.")
    fig = px.line(
        df, x="recorded_date", y="stock", color="label",
        hover_name="name",
        labels={"stock": "Stock Qty", "recorded_date": "Date"},
    )
    fig.update_layout(**CHART_LAYOUT, title="Stock Levels Over Time")
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(239,68,68,0.5)",
                  annotation_text="Out of stock", annotation_position="bottom right")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    section_header("💸", "Price Fluctuations")
    st.caption("Track how competitors change pricing day by day.")
    fig2 = px.line(
        df, x="recorded_date", y="price", color="label",
        hover_name="name",
        labels={"price": "Price (₽)", "recorded_date": "Date"},
    )
    fig2.update_layout(**CHART_LAYOUT, title="Retail Price Over Time")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    section_header("📊", "Estimated Daily Sales")
    st.caption("Units sold per day, estimated from stock deltas.")
    fig3 = px.bar(
        df, x="recorded_date", y="estimated_sales", color="label",
        hover_name="name", barmode="group",
        labels={"estimated_sales": "Units Sold", "recorded_date": "Date"},
    )
    fig3.update_layout(**CHART_LAYOUT, title="Daily Estimated Units Sold")
    st.plotly_chart(fig3, use_container_width=True)

    # Also cumulative
    daily_total = (
        df.groupby("recorded_date")["estimated_sales"].sum().reset_index()
          .rename(columns={"estimated_sales": "total_units"})
    )
    fig3b = px.area(
        daily_total, x="recorded_date", y="total_units",
        labels={"total_units": "Total Units (all SKUs)", "recorded_date": "Date"},
        title="Total Market Daily Sales (all tracked SKUs combined)",
        color_discrete_sequence=["#3b82f6"],
    )
    fig3b.update_layout(**CHART_LAYOUT)
    st.plotly_chart(fig3b, use_container_width=True)

with tab4:
    section_header("🫧", "Price vs Sales Bubble Chart")
    st.caption("Bubble size = estimated daily sales. Sweet spot = high sales, competitive price.")
    fig4 = px.scatter(
        df, x="recorded_date", y="price",
        size=df["estimated_sales"].clip(lower=1),
        color="label",
        hover_name="name",
        hover_data=["sku", "stock", "price", "estimated_sales"],
        labels={"price": "Retail Price (₽)", "recorded_date": "Date"},
        size_max=40,
    )
    fig4.update_layout(**CHART_LAYOUT, title="Price Level vs. Sales Volume (bubble size = units sold)")
    st.plotly_chart(fig4, use_container_width=True)
