"""
utils.py — Shared helpers, CSS, and DB query functions for the wb-tracker multi-page app.
"""

import os
import re
import streamlit as st
import pandas as pd

from db import get_db_connection
from scraper import fetch_product_data, process_sku


# ─────────────────────────────────────────────
# SHARED PREMIUM CSS
# ─────────────────────────────────────────────

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── KPI Cards ── */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.kpi-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 16px 16px 0 0;
}

.kpi-card.accent-green::before  { background: linear-gradient(90deg, #00f5a0, #00d9f5); }
.kpi-card.accent-purple::before { background: linear-gradient(90deg, #a855f7, #6366f1); }
.kpi-card.accent-orange::before { background: linear-gradient(90deg, #f97316, #eab308); }
.kpi-card.accent-red::before    { background: linear-gradient(90deg, #ef4444, #f43f5e); }
.kpi-card.accent-blue::before   { background: linear-gradient(90deg, #3b82f6, #06b6d4); }

.kpi-icon {
    font-size: 1.6rem;
    margin-bottom: 0.5rem;
    display: block;
}

.kpi-label {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8b949e;
    margin-bottom: 0.4rem;
}

.kpi-value {
    font-size: 1.9rem;
    font-weight: 800;
    color: #f0f6fc;
    line-height: 1;
    margin-bottom: 0.3rem;
}

.kpi-sub {
    font-size: 0.75rem;
    color: #58a6ff;
}

/* ── Section headers ── */
.section-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin: 2rem 0 1rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}

.section-header h2 {
    font-size: 1.1rem;
    font-weight: 700;
    color: #f0f6fc;
    margin: 0;
}

/* ── Podium cards ── */
.podium-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.podium-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 1.2rem;
    text-align: center;
    position: relative;
}

.podium-card.rank-1 { border-top: 3px solid #FFD700; }
.podium-card.rank-2 { border-top: 3px solid #C0C0C0; }
.podium-card.rank-3 { border-top: 3px solid #CD7F32; }

.podium-rank {
    font-size: 1.8rem;
    margin-bottom: 0.3rem;
}

.podium-name {
    font-size: 0.82rem;
    font-weight: 600;
    color: #f0f6fc;
    margin-bottom: 0.2rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.podium-brand {
    font-size: 0.72rem;
    color: #8b949e;
    margin-bottom: 0.5rem;
}

.podium-stat {
    font-size: 1rem;
    font-weight: 700;
    color: #58a6ff;
}

.podium-sub {
    font-size: 0.7rem;
    color: #6e7681;
}

/* ── Alert strip ── */
.alert-strip {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.3);
    border-radius: 10px;
    padding: 0.8rem 1.2rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.85rem;
    color: #fca5a5;
}

/* ── Product detail card ── */
.product-header {
    background: linear-gradient(135deg, rgba(88, 166, 255, 0.08), rgba(163, 113, 247, 0.08));
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    margin-bottom: 2rem;
}

.product-title {
    font-size: 1.5rem;
    font-weight: 800;
    color: #f0f6fc;
    margin-bottom: 0.3rem;
}

.product-meta {
    font-size: 0.85rem;
    color: #8b949e;
}

/* ── Page title ── */
.page-title {
    font-size: 1.6rem;
    font-weight: 800;
    color: #f0f6fc;
    margin-bottom: 0.3rem;
}

.page-subtitle {
    font-size: 0.9rem;
    color: #8b949e;
    margin-bottom: 1.5rem;
}

/* ── Nav pills (for back button) ── */
.nav-pill {
    display: inline-block;
    background: rgba(88, 166, 255, 0.12);
    border: 1px solid rgba(88, 166, 255, 0.3);
    border-radius: 20px;
    padding: 0.3rem 0.9rem;
    font-size: 0.8rem;
    color: #58a6ff;
    text-decoration: none;
    margin-bottom: 1rem;
    cursor: pointer;
}

/* hide streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""


def inject_css():
    """Inject the global premium CSS into the Streamlit page."""
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def kpi_card(icon: str, label: str, value: str, sub: str = "", accent: str = "blue") -> str:
    """Return HTML for a KPI card."""
    return f"""<div class="kpi-card accent-{accent}">
<span class="kpi-icon">{icon}</span>
<div class="kpi-label">{label}</div>
<div class="kpi-value">{value}</div>
{'<div class="kpi-sub">' + sub + '</div>' if sub else ''}
</div>"""


def section_header(icon: str, title: str):
    """Render a styled section header."""
    st.markdown(
        f'<div class="section-header"><h2>{icon} {title}</h2></div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────

def check_password() -> bool:
    """Show password gate. Returns True if authenticated."""
    if st.session_state.get("authenticated"):
        return True

    st.markdown("""
        <div style="text-align:center; padding: 4rem 0 2rem;">
            <div style="font-size:3rem;">🔐</div>
            <h1 style="font-size:1.8rem; font-weight:800; color:#f0f6fc; margin:0.5rem 0 0.3rem;">
                Wildberries Tracker
            </h1>
            <p style="color:#8b949e; font-size:0.95rem;">
                Private analytics portal — enter your master password to continue
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Master password...")
        if st.button("Unlock →", use_container_width=True, type="primary"):
            expected = os.environ.get("DASHBOARD_PASSWORD", "admin123")
            if pwd == expected:
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


# ─────────────────────────────────────────────
# SKU HELPERS
# ─────────────────────────────────────────────

def extract_sku(input_str: str):
    """Extract numeric SKU from a raw string or Wildberries URL."""
    s = input_str.strip()
    if s.isdigit():
        return s
    match = re.search(r'catalog/(\d+)', s)
    return match.group(1) if match else None


def add_tracked_item(sku: str, category: str, is_own: bool = False):
    """Add a new product to watchlist and immediately scrape it."""
    with st.spinner("Fetching product info from Wildberries API…"):
        product_data = fetch_product_data(sku)

    name = product_data.get("name", "Unknown Product") if product_data else "Unknown Product"
    brand = product_data.get("brand", "Unknown Brand") if product_data else "Unknown Brand"

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tracked_items (sku, name, brand, category, is_own_store)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE
                    SET category = EXCLUDED.category,
                        is_own_store = EXCLUDED.is_own_store;
                    """,
                    (sku, name, brand, category, is_own)
                )
                if product_data:
                    process_sku(cur, sku)
        return True, name, brand
    except Exception as e:
        return False, str(e), ""
    finally:
        conn.close()


def remove_tracked_item(sku: str) -> bool:
    """Delete a product from tracking (cascades to snapshots)."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM tracked_items WHERE sku = %s", (sku,))
        return True
    except Exception as e:
        st.error(f"Error removing SKU {sku}: {e}")
        return False
    finally:
        conn.close()


def set_own_store_flag(sku: str, is_own: bool):
    """Toggle whether a SKU belongs to our own store."""
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE tracked_items SET is_own_store = %s WHERE sku = %s",
                    (is_own, sku)
                )
        return True
    except Exception as e:
        st.error(f"Error updating classification: {e}")
        return False
    finally:
        conn.close()


# ─────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────

def load_tracked_items() -> list:
    """Return list of (sku, name, brand, category, is_own_store) tuples."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sku, name, brand, category, is_own_store "
                "FROM tracked_items ORDER BY category, brand"
            )
            return cur.fetchall()
    except Exception:
        return []
    finally:
        conn.close()


def load_leaderboard(days: int = 7) -> pd.DataFrame:
    """Load 7-day leaderboard data from the DB."""
    conn = get_db_connection()
    try:
        is_sqlite = getattr(conn, "is_sqlite", False)
        raw_conn = getattr(conn, "conn", conn)
        
        query = f"""
            SELECT
                t.sku,
                t.name,
                t.brand,
                t.category,
                t.is_own_store,
                COALESCE(SUM(s.estimated_sales), 0)              AS total_sales,
                COALESCE(ROUND(AVG(s.price), 0), 0)              AS avg_price,
                COALESCE(SUM(s.estimated_sales * s.price), 0)    AS estimated_revenue,
                COALESCE(
                    (SELECT stock FROM daily_snapshots
                     WHERE sku = t.sku ORDER BY recorded_date DESC LIMIT 1), 0
                )                                                 AS current_stock,
                COALESCE(ROUND(AVG(s.rating), 2), 0.00)          AS avg_rating,
                COALESCE(
                    (SELECT feedback_count FROM daily_snapshots
                     WHERE sku = t.sku ORDER BY recorded_date DESC LIMIT 1), 0
                )                                                 AS current_feedbacks
            FROM tracked_items t
            LEFT JOIN daily_snapshots s
                ON t.sku = s.sku
                AND s.recorded_date >= CURRENT_DATE - INTERVAL '{days} days'
            GROUP BY t.sku, t.name, t.brand, t.category, t.is_own_store
            ORDER BY total_sales DESC;
        """
        if is_sqlite:
            query = query.replace(f"CURRENT_DATE - INTERVAL '{days} days'", f"date('now', '-{days} days')")
            
        return pd.read_sql(query, raw_conn)
    except Exception as e:
        st.error(f"DB query error (leaderboard): {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def load_timeline(days: int = 30) -> pd.DataFrame:
    """Load historical snapshot timeline from the DB."""
    conn = get_db_connection()
    try:
        is_sqlite = getattr(conn, "is_sqlite", False)
        raw_conn = getattr(conn, "conn", conn)
        
        query = f"""
            SELECT
                s.recorded_date,
                t.sku,
                t.name,
                t.brand,
                t.category,
                t.is_own_store,
                s.price,
                s.stock,
                s.estimated_sales,
                (s.estimated_sales * s.price) AS estimated_revenue
            FROM daily_snapshots s
            JOIN tracked_items t ON s.sku = t.sku
            WHERE s.recorded_date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY s.recorded_date ASC;
        """
        if is_sqlite:
            query = query.replace(f"CURRENT_DATE - INTERVAL '{days} days'", f"date('now', '-{days} days')")
            
        df = pd.read_sql(query, raw_conn)
        if not df.empty:
            df["recorded_date"] = pd.to_datetime(df["recorded_date"])
        return df
    except Exception as e:
        st.error(f"DB query error (timeline): {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def load_product_timeline(sku: str, days: int = 30) -> pd.DataFrame:
    """Load historical snapshots for a single SKU."""
    conn = get_db_connection()
    try:
        is_sqlite = getattr(conn, "is_sqlite", False)
        raw_conn = getattr(conn, "conn", conn)
        
        query = """
            SELECT
                s.recorded_date,
                s.price,
                s.stock,
                s.rating,
                s.feedback_count,
                s.estimated_sales,
                (s.estimated_sales * s.price) AS estimated_revenue
            FROM daily_snapshots s
            WHERE s.sku = %s
            ORDER BY s.recorded_date ASC;
        """
        if is_sqlite:
            query = query.replace("%s", "?")
            
        df = pd.read_sql(query, raw_conn, params=(sku,))
        if not df.empty:
            df["recorded_date"] = pd.to_datetime(df["recorded_date"])
        return df
    except Exception as e:
        st.error(f"DB query error (product timeline): {e}")
        return pd.DataFrame()
    finally:
        conn.close()


def stock_status(stock: int) -> str:
    if stock == 0:
        return "🔴 Out of Stock"
    elif stock < 10:
        return "🟡 Low Stock"
    return "🟢 Healthy"


CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis_gridcolor="rgba(255,255,255,0.05)",
    yaxis_gridcolor="rgba(255,255,255,0.05)",
    font_family="Inter",
    margin=dict(t=40, b=20, l=10, r=10),
)
