"""
Page 4 — Product Detail
Per-SKU deep-dive: KPI row, price/stock/sales sparklines, raw snapshot table.
SKU is picked up from st.session_state["selected_sku"] set by Leaderboard page,
or can be manually entered via a selectbox on this page.
"""

import streamlit as st
import plotly.express as px

st.set_page_config(page_title="Product Detail · WB Tracker", page_icon="🔍", layout="wide")

from utils import (
    inject_css, check_password, kpi_card, section_header,
    load_leaderboard, load_product_timeline, stock_status, CHART_LAYOUT
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
st.markdown('<div class="page-title">🔍 Product Detail</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="page-subtitle">Full analytics for a single tracked SKU — '
    'price history, stock dynamics, and daily sales breakdown.</div>',
    unsafe_allow_html=True
)

# ── SKU picker ────────────────────────────────────────────────────────────────
df_lb = load_leaderboard(days=7)

if df_lb.empty:
    st.warning("⚠️ No tracked products. Go to ⚙️ Settings to add some.")
    st.stop()

sku_options = df_lb["sku"].tolist()
label_map   = {
    row["sku"]: f"{row['brand']} — {row['name'][:40]}... ({row['sku']})"
    for _, row in df_lb.iterrows()
}

# Default to whatever was selected in Leaderboard
default_sku = st.session_state.get("selected_sku", sku_options[0])
if default_sku not in sku_options:
    default_sku = sku_options[0]

selected_sku = st.selectbox(
    "Select product to inspect",
    options=sku_options,
    index=sku_options.index(default_sku),
    format_func=lambda x: label_map.get(x, x),
)
st.session_state["selected_sku"] = selected_sku

# ── Fetch this product's data ─────────────────────────────────────────────────
row = df_lb[df_lb["sku"] == selected_sku].iloc[0]
df_snap = load_product_timeline(selected_sku, days=90)

# ── Product header card ────────────────────────────────────────────────────────
wb_url  = f"https://www.wildberries.ru/catalog/{selected_sku}/detail.aspx"
badge   = "🏪 Our Store" if row["is_own_store"] else "⚔️ Competitor"

st.markdown(f"""
<div class="product-header">
    <div class="product-title">{row['name']}</div>
    <div class="product-meta">
        {badge} &nbsp;·&nbsp;
        <strong>{row['brand']}</strong> &nbsp;·&nbsp;
        {row['category']} &nbsp;·&nbsp;
        SKU: <code>{selected_sku}</code> &nbsp;·&nbsp;
        <a href="{wb_url}" target="_blank" style="color:#58a6ff;">🔗 View on Wildberries</a>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI row ───────────────────────────────────────────────────────────────────
section_header("📊", "7-Day Performance Summary")

cards_html = (
    '<div class="kpi-grid">'
    + kpi_card("💰", "Avg Price (7d)",        f"{int(row['avg_price']):,} ₽",   "", "blue")
    + kpi_card("📦", "Current Stock",          str(int(row['current_stock'])),
               stock_status(int(row['current_stock'])), "orange")
    + kpi_card("📈", "Est. Sales (7d)",        f"{int(row['total_sales']):,} units", "", "green")
    + kpi_card("💸", "Est. Revenue (7d)",      f"{int(row['estimated_revenue']):,} ₽", "", "purple")
    + kpi_card("⭐", "Avg Rating",             f"{float(row['avg_rating']):.2f}", "", "orange")
    + kpi_card("💬", "Total Reviews",          str(int(row['current_feedbacks'])), "", "blue")
    + '</div>'
)
st.markdown(cards_html, unsafe_allow_html=True)

# ── Charts ─────────────────────────────────────────────────────────────────────
if df_snap.empty:
    st.info("ℹ️ No historical snapshots for this product yet. Run the scraper to collect data.")
else:
    tab1, tab2, tab3 = st.tabs(["📦 Stock History", "💸 Price History", "📊 Daily Sales"])

    with tab1:
        section_header("📦", "Stock Over Time")
        fig_stock = px.area(
            df_snap, x="recorded_date", y="stock",
            labels={"stock": "Stock Qty", "recorded_date": "Date"},
            color_discrete_sequence=["#3b82f6"],
        )
        fig_stock.update_layout(**CHART_LAYOUT, title=f"Stock History — {row['brand']}")
        fig_stock.add_hline(y=0, line_dash="dot", line_color="rgba(239,68,68,0.4)",
                            annotation_text="Out of stock")
        st.plotly_chart(fig_stock, use_container_width=True)

    with tab2:
        section_header("💸", "Price Over Time")
        fig_price = px.line(
            df_snap, x="recorded_date", y="price",
            labels={"price": "Price (₽)", "recorded_date": "Date"},
            color_discrete_sequence=["#a855f7"],
            markers=True,
        )
        fig_price.update_layout(**CHART_LAYOUT, title=f"Price History — {row['brand']}")
        st.plotly_chart(fig_price, use_container_width=True)

    with tab3:
        section_header("📊", "Daily Estimated Sales")
        fig_sales = px.bar(
            df_snap, x="recorded_date", y="estimated_sales",
            labels={"estimated_sales": "Units Sold", "recorded_date": "Date"},
            color_discrete_sequence=["#00f5a0"],
        )
        fig_sales.update_layout(**CHART_LAYOUT, title=f"Daily Sales Estimate — {row['brand']}")
        st.plotly_chart(fig_sales, use_container_width=True)

    # ── Raw data expander ─────────────────────────────────────────────────────
    with st.expander("📋 View raw snapshot data"):
        st.dataframe(
            df_snap.sort_values("recorded_date", ascending=False),
            column_config={
                "recorded_date":      st.column_config.DateColumn("Date"),
                "price":              st.column_config.NumberColumn("Price", format="%d ₽"),
                "stock":              st.column_config.NumberColumn("Stock", format="%d"),
                "rating":             st.column_config.NumberColumn("Rating", format="%.2f"),
                "feedback_count":     st.column_config.NumberColumn("Reviews", format="%d"),
                "estimated_sales":    st.column_config.NumberColumn("Est. Sales", format="%d"),
                "estimated_revenue":  st.column_config.NumberColumn("Est. Revenue", format="%d ₽"),
            },
            hide_index=True,
            use_container_width=True,
        )

# ── Back link ─────────────────────────────────────────────────────────────────
st.divider()
st.page_link("pages/2_🏆_Leaderboard.py", label="← Back to Leaderboard")
