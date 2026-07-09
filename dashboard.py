import os
import re
import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_db_connection, init_db
from scraper import fetch_product_data, process_sku

# Page configuration
st.set_page_config(
    page_title="Wildberries Textile Tracker",
    page_icon="👕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom premium styling
st.markdown("""
    <style>
        /* Base typography & aesthetics */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        /* Metric summary card styles */
        .metric-container {
            display: flex;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .metric-card {
            flex: 1;
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
        }
        
        .metric-card-own {
            border-left: 5px solid #ff4b4b;
        }
        
        .metric-card-comp {
            border-left: 5px solid #00f0ff;
        }
        
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #8b949e;
            margin-bottom: 0.5rem;
        }
        
        .metric-val {
            font-size: 1.8rem;
            font-weight: 700;
            color: #f0f6fc;
        }
        
        .metric-sub {
            font-size: 0.75rem;
            color: #58a6ff;
            margin-top: 0.25rem;
        }
    </style>
""", unsafe_allow_html=True)

# Ensure database is initialized
try:
    init_db()
except Exception as e:
    st.error(f"Database initialization failed: {e}")

# Helper functions
def extract_sku(input_str):
    """
    Extracts numerical SKU from a raw SKU string or Wildberries URL.
    """
    input_str = input_str.strip()
    if input_str.isdigit():
        return input_str
    
    # Example URL: https://www.wildberries.ru/catalog/173854692/detail.aspx
    match = re.search(r'catalog/(\d+)', input_str)
    if match:
        return match.group(1)
    return None

def add_tracked_item(sku, category):
    """
    Adds a new item to tracked_items, performs initial scrape, and saves to database.
    """
    # Fetch metadata live from API
    with st.spinner("Fetching product info from Wildberries API..."):
        product_data = fetch_product_data(sku)
        
    name = product_data.get("name", "Unknown Product") if product_data else "Unknown Product"
    brand = product_data.get("brand", "Unknown Brand") if product_data else "Unknown Brand"
    
    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                # Add to watchlist
                cur.execute(
                    """
                    INSERT INTO tracked_items (sku, name, brand, category) 
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE 
                    SET category = EXCLUDED.category;
                    """,
                    (sku, name, brand, category)
                )
                # Perform immediate crawl for initial snapshot
                if product_data:
                    process_sku(cur, sku)
        return True, name, brand
    except Exception as e:
        return False, str(e), ""
    finally:
        conn.close()

def remove_tracked_item(sku):
    """
    Removes item from database (snapshots will be deleted via CASCADE constraints).
    """
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

# Password Security Verification
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown("<h2 style='text-align: center;'>🔐 Wildberries Textile Competitor Tracker</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #8b949e;'>Enter your master password to access the private analytics portal.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        password_input = st.text_input("Master Password", type="password", label_visibility="collapsed")
        access_button = st.button("Unlock Portal", use_container_width=True)
        
        expected_pass = os.environ.get("DASHBOARD_PASSWORD", "admin123")
        
        if access_button:
            if password_input == expected_pass:
                st.session_state["authenticated"] = True
                st.success("Access authorized!")
                st.rerun()
            else:
                st.error("Access denied. Incorrect master password.")
                
    return False

# Main Execution Flow
if check_password():
    # Sidebar Control Panel
    st.sidebar.title("🛠️ Tracker Control Panel")
    
    # 1. Processing Form to Track New Items
    st.sidebar.subheader("Track New Textile Item")
    with st.sidebar.form(key="add_item_form", clear_on_submit=True):
        input_value = st.text_input("SKU or WB Product URL", placeholder="e.g. 173854692")
        category_selection = st.selectbox(
            "Category Selection",
            options=['T-shirts', 'Longsleeves', 'Underwear', 'Shirts']
        )
        submit_btn = st.form_submit_form_button = st.form_submit_button("Track Item")
        
        if submit_btn:
            extracted = extract_sku(input_value)
            if not extracted:
                st.sidebar.error("Invalid SKU or URL format.")
            else:
                success, val1, val2 = add_tracked_item(extracted, category_selection)
                if success:
                    st.sidebar.success(f"Successfully tracking: {val2} ({val1})")
                    st.rerun()
                else:
                    st.sidebar.error(f"Error: {val1}")

    # 2. Interactive list of tracked items with deletion
    st.sidebar.subheader("Active Watchlist")
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT sku, name, brand, category FROM tracked_items ORDER BY category, brand")
            tracked_items_list = cur.fetchall()
    except Exception as e:
        st.error(f"Failed to query tracked items: {e}")
        tracked_items_list = []
    finally:
        conn.close()
        
    if not tracked_items_list:
        st.sidebar.info("Watchlist is currently empty.")
    else:
        for sku, name, brand, category in tracked_items_list:
            label = f"[{category}] {brand} ({sku})"
            with st.sidebar.expander(label):
                st.write(f"**Name:** {name}")
                if st.button("🗑️ Remove from Watchlist", key=f"del_{sku}", use_container_width=True):
                    if remove_tracked_item(sku):
                        st.sidebar.success(f"Removed SKU {sku}")
                        st.rerun()

    # 3. Manual Scraper Runner Trigger
    st.sidebar.subheader("System Maintenance")
    if st.sidebar.button("🔄 Trigger Live Scraper Run", use_container_width=True):
        with st.spinner("Executing scraper pipeline..."):
            try:
                from scraper import run_scraper
                run_scraper()
                st.sidebar.success("Scraper executed successfully!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Scraper runtime error: {e}")

    # MAIN ANALYTICS WORKSPACE
    st.title("📊 MPSTATS Competitor Intelligence Node")
    st.markdown("Automated market tracking for private label textile products on Wildberries.")

    if not tracked_items_list:
        st.warning("⚠️ No products are currently being tracked. Add competitor or store products in the sidebar to populate the dashboard.")
    else:
        # Load Data
        conn = get_db_connection()
        try:
            # 7-day query including estimated revenue
            leaderboard_query = """
                SELECT 
                    t.sku, 
                    t.name, 
                    t.brand, 
                    t.category,
                    COALESCE(SUM(s.estimated_sales), 0) as total_sales,
                    COALESCE(ROUND(AVG(s.price), 0), 0) as avg_price,
                    COALESCE(SUM(s.estimated_sales * s.price), 0) as estimated_revenue,
                    COALESCE((SELECT stock FROM daily_snapshots WHERE sku = t.sku ORDER BY recorded_date DESC LIMIT 1), 0) as current_stock,
                    COALESCE(ROUND(AVG(s.rating), 2), 0.00) as avg_rating,
                    COALESCE((SELECT feedback_count FROM daily_snapshots WHERE sku = t.sku ORDER BY recorded_date DESC LIMIT 1), 0) as current_feedbacks
                FROM tracked_items t
                LEFT JOIN daily_snapshots s ON t.sku = s.sku AND s.recorded_date >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY t.sku, t.name, t.brand, t.category
                ORDER BY total_sales DESC;
            """
            df_leaderboard = pd.read_sql(leaderboard_query, conn)
            
            # Timeline query including revenue
            timeline_query = """
                SELECT 
                    s.recorded_date,
                    t.sku,
                    t.name,
                    t.brand,
                    t.category,
                    s.price,
                    s.stock,
                    s.estimated_sales,
                    (s.estimated_sales * s.price) as estimated_revenue
                FROM daily_snapshots s
                JOIN tracked_items t ON s.sku = t.sku
                WHERE s.recorded_date >= CURRENT_DATE - INTERVAL '30 days'
                ORDER BY s.recorded_date ASC;
            """
            df_timeline = pd.read_sql(timeline_query, conn)
        except Exception as e:
            st.error(f"Database query error: {e}")
            df_leaderboard = pd.DataFrame()
            df_timeline = pd.DataFrame()
        finally:
            conn.close()

        if df_leaderboard.empty:
            st.info("ℹ️ No snapshot data has been collected yet. Please trigger a live scraper run from the sidebar to populate tracking snapshots.")
        else:
            # Store Identification Setting in main space
            st.markdown("### 🏬 Store Classification")
            skus_available = df_leaderboard["sku"].tolist()
            brand_map = {row["sku"]: f"{row['brand']} - {row['name'][:30]}... ({row['sku']})" for _, row in df_leaderboard.iterrows()}
            
            # Allow user to designate which SKUs belong to their own store
            own_skus = st.multiselect(
                "Select Your Store's SKUs (all others will be classified as Competitors):",
                options=skus_available,
                format_func=lambda x: brand_map.get(x, x),
                key="own_skus_selector"
            )
            
            # Add classification labels
            df_leaderboard["Type"] = df_leaderboard["sku"].apply(lambda x: "Our Store" if x in own_skus else "Competitor")
            
            # Calculate metrics
            total_sales = df_leaderboard["total_sales"].sum()
            total_revenue = df_leaderboard["estimated_revenue"].sum()
            our_sales = df_leaderboard[df_leaderboard["Type"] == "Our Store"]["total_sales"].sum()
            our_revenue = df_leaderboard[df_leaderboard["Type"] == "Our Store"]["estimated_revenue"].sum()
            
            # Top Brand calculation
            brand_performance = df_leaderboard.groupby("brand")["total_sales"].sum().reset_index()
            if not brand_performance.empty:
                top_brand_row = brand_performance.sort_values("total_sales", ascending=False).iloc[0]
                top_brand_name = top_brand_row["brand"]
                top_brand_sales = top_brand_row["total_sales"]
            else:
                top_brand_name = "N/A"
                top_brand_sales = 0

            # Market share share percentage
            market_share_pct = (our_sales / total_sales * 100) if total_sales > 0 else 0.0
            
            st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-card metric-card-own">
                        <div class="metric-title">Our Store Revenue</div>
                        <div class="metric-val">{our_revenue:,.0f} RUB</div>
                        <div class="metric-sub">{our_sales:,} units sold ({market_share_pct:.1f}% share)</div>
                    </div>
                    <div class="metric-card metric-card-comp">
                        <div class="metric-title">Market Size (7d)</div>
                        <div class="metric-val">{total_revenue:,.0f} RUB</div>
                        <div class="metric-sub">{total_sales:,} total units sold across {len(df_leaderboard)} items</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-title">Top Selling Brand</div>
                        <div class="metric-val">{top_brand_name}</div>
                        <div class="metric-sub">{top_brand_sales:,} units sold (7d)</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # Category filters
            st.subheader("🏆 7-Day Performance Leaderboard")
            categories = ['All'] + list(df_leaderboard["category"].unique())
            selected_cat = st.selectbox("Filter Leaderboard by Category:", options=categories)
            
            df_filtered = df_leaderboard.copy()
            if selected_cat != 'All':
                df_filtered = df_filtered[df_filtered["category"] == selected_cat]
                
            # Add dynamic stock warnings
            def get_stock_status(stock):
                if stock == 0:
                    return "🔴 Out of Stock"
                elif stock < 10:
                    return "🟡 Low Stock"
                else:
                    return "🟢 Healthy"
            
            df_filtered["Stock Status"] = df_filtered["current_stock"].apply(get_stock_status)
            df_filtered["sku_link"] = df_filtered["sku"].apply(lambda x: f"https://www.wildberries.uz/catalog/{x}/detail.aspx")
            
            # Render styled dataframe
            def highlight_own(row):
                return ['background-color: rgba(255, 75, 75, 0.12)' if row.Type == 'Our Store' else '' for _ in row]
                
            st.dataframe(
                df_filtered.style.apply(highlight_own, axis=1),
                column_config={
                    "sku_link": st.column_config.LinkColumn("Product Page", display_text="🔗 View on WB"),
                    "sku": st.column_config.TextColumn("SKU"),
                    "name": st.column_config.TextColumn("Product Name"),
                    "brand": st.column_config.TextColumn("Brand"),
                    "category": st.column_config.TextColumn("Category"),
                    "total_sales": st.column_config.NumberColumn("Est. Sales (7d)", format="%d"),
                    "avg_price": st.column_config.NumberColumn("Avg Price (7d)", format="%d RUB"),
                    "estimated_revenue": st.column_config.NumberColumn("Est. Revenue (7d)", format="%d RUB"),
                    "current_stock": st.column_config.NumberColumn("Stock qty", format="%d"),
                    "Stock Status": st.column_config.TextColumn("Stock Status"),
                    "avg_rating": st.column_config.NumberColumn("Rating", format="%.2f ⭐"),
                    "current_feedbacks": st.column_config.NumberColumn("Reviews", format="%d"),
                    "Type": st.column_config.TextColumn("Classification")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Charts Workspace
            st.subheader("📈 MPSTATS Visual Analytics Workspace")
            
            if not df_timeline.empty:
                # Merge Store Classification into timeline df
                df_timeline["Type"] = df_timeline["sku"].apply(lambda x: "Our Store" if x in own_skus else "Competitor")
                df_timeline["label"] = df_timeline.apply(lambda r: f"[{r['Type']}] {r['brand']} ({r['sku']})", axis=1)
                
                # Format Dates
                df_timeline["recorded_date"] = pd.to_datetime(df_timeline["recorded_date"])
                
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📊 Brand & Category Share",
                    "📦 Stock Dynamics (Out of Stock alert)",
                    "💸 Pricing vs. Sales Dynamics",
                    "📅 Performance Trends over Time"
                ])
                
                with tab1:
                    col1, col2 = st.columns(2)
                    with col1:
                        # Brand Share by Revenue
                        brand_rev = df_timeline.groupby("brand")["estimated_revenue"].sum().reset_index()
                        fig_brand_rev = px.pie(
                            brand_rev,
                            values="estimated_revenue",
                            names="brand",
                            title="Brand Market Share (by Revenue in RUB)",
                            color_discrete_sequence=px.colors.qualitative.Pastel
                        )
                        fig_brand_rev.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig_brand_rev, use_container_width=True)
                        
                    with col2:
                        # Category Share by Revenue
                        cat_rev = df_timeline.groupby("category")["estimated_revenue"].sum().reset_index()
                        fig_cat_rev = px.pie(
                            cat_rev,
                            values="estimated_revenue",
                            names="category",
                            title="Category Sales Distribution (by Revenue in RUB)",
                            color_discrete_sequence=px.colors.qualitative.Safe
                        )
                        fig_cat_rev.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig_cat_rev, use_container_width=True)
                        
                with tab2:
                    # Stock Dynamics over Time
                    fig_stock = px.line(
                        df_timeline,
                        x="recorded_date",
                        y="stock",
                        color="label",
                        hover_name="name",
                        title="Stock Level Trends (Detect competitor out-of-stock events!)",
                        labels={"stock": "Inventory Stock Qty", "recorded_date": "Date"}
                    )
                    fig_stock.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis_gridcolor="rgba(255,255,255,0.05)",
                        yaxis_gridcolor="rgba(255,255,255,0.05)"
                    )
                    st.plotly_chart(fig_stock, use_container_width=True)
                    
                with tab3:
                    # Scatter Plot Price vs Sales
                    fig_scatter = px.scatter(
                        df_timeline,
                        x="recorded_date",
                        y="price",
                        size="estimated_sales",
                        color="label",
                        hover_name="name",
                        hover_data=["sku", "stock", "price", "estimated_sales"],
                        title="Retail Price Levels mapped against Estimated Sales Volume (Bubble Size)",
                        labels={
                            "price": "Retail Price (RUB)",
                            "recorded_date": "Timeline",
                            "estimated_sales": "Daily Sales Vol"
                        },
                        size_max=35
                    )
                    fig_scatter.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        xaxis_gridcolor="rgba(255,255,255,0.05)",
                        yaxis_gridcolor="rgba(255,255,255,0.05)"
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)
                    
                with tab4:
                    col1, col2 = st.columns(2)
                    with col1:
                        # Price Line Chart
                        fig_price_trend = px.line(
                            df_timeline,
                            x="recorded_date",
                            y="price",
                            color="label",
                            hover_name="name",
                            title="Daily Price Fluctuations",
                            labels={"price": "Retail Price (RUB)", "recorded_date": "Date"}
                        )
                        fig_price_trend.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis_gridcolor="rgba(255,255,255,0.05)",
                            yaxis_gridcolor="rgba(255,255,255,0.05)"
                        )
                        st.plotly_chart(fig_price_trend, use_container_width=True)
                        
                    with col2:
                        # Daily Sales Bar Chart
                        fig_sales_trend = px.bar(
                            df_timeline,
                            x="recorded_date",
                            y="estimated_sales",
                            color="label",
                            hover_name="name",
                            title="Estimated Daily Units Sold",
                            labels={"estimated_sales": "Units Sold", "recorded_date": "Date"},
                            barmode="group"
                        )
                        fig_sales_trend.update_layout(
                            template="plotly_dark",
                            paper_bgcolor="rgba(0,0,0,0)",
                            plot_bgcolor="rgba(0,0,0,0)",
                            xaxis_gridcolor="rgba(255,255,255,0.05)",
                            yaxis_gridcolor="rgba(255,255,255,0.05)"
                        )
                        st.plotly_chart(fig_sales_trend, use_container_width=True)
            else:
                st.info("ℹ️ No historical snapshot timeline coordinates to map. Try executing a manual scraper run from the sidebar panel.")
