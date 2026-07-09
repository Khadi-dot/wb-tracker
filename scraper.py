import os
import time
import requests
import datetime
from db import get_db_connection

# Realistic browser headers to prevent anti-bot detection
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
}

def fetch_product_data(sku):
    """
    Fetches product details from the Wildberries API for a given SKU.
    """
    # 1. Try Moscow/Russian parameters first (most comprehensive catalog)
    url_ru = f"https://u-card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm={sku}"
    try:
        response = requests.get(url_ru, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", {}).get("products", [])
            if products:
                return products[0]
    except Exception as e:
        print(f"Error fetching Russian data for SKU {sku}: {e}")

    # 2. Fallback to Tashkent/Uzbekistan parameters if not found in Moscow catalog
    url_uz = f"https://u-card.wb.ru/cards/v4/detail?appType=1&curr=uzs&dest=491&nm={sku}"
    try:
        response = requests.get(url_uz, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            products = data.get("data", {}).get("products", [])
            if products:
                return products[0]
            else:
                print(f"Product SKU {sku} not found in both RU and UZ catalogs.")
        else:
            print(f"Failed to fetch data for SKU {sku}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching Uzbek data for SKU {sku}: {e}")
    return None

def process_sku(cur, sku, target_date=None):
    """
    Processes a single SKU, fetches its live data, calculates estimated sales,
    and updates/inserts database records.
    """
    if target_date is None:
        target_date = datetime.date.today()

    product = fetch_product_data(sku)
    if not product:
        return False

    # Extract info
    name = product.get("name", "Unknown Product")
    brand = product.get("brand", "Unknown Brand")
    
    # Extract price from the first available size
    price = 0
    sizes = product.get("sizes", [])
    if sizes:
        price_obj = sizes[0].get("price", {})
        price = int(price_obj.get("product", 0) / 100)
        if not price:
            price = int(price_obj.get("basic", 0) / 100)

    # Use totalQuantity from the product level, falling back to sum of size stocks
    stock = product.get("totalQuantity")
    if stock is None:
        stock = 0
        for size in sizes:
            for stock_item in size.get("stocks", []):
                stock += stock_item.get("qty", 0)

    rating = product.get("reviewRating") or product.get("rating") or 0.0
    feedback_count = product.get("feedbacks") or product.get("nmFeedbacks") or 0

    # Ensure tracked_items descriptive fields are updated if they were blank
    cur.execute(
        """
        UPDATE tracked_items 
        SET name = COALESCE(NULLIF(name, ''), %s), 
            brand = COALESCE(NULLIF(brand, ''), %s) 
        WHERE sku = %s
        """,
        (name, brand, sku)
    )

    # Get yesterday's (or most recent prior) stock level to compute daily sales
    cur.execute(
        """
        SELECT stock 
        FROM daily_snapshots 
        WHERE sku = %s AND recorded_date < %s 
        ORDER BY recorded_date DESC 
        LIMIT 1
        """,
        (sku, target_date)
    )
    prev_row = cur.fetchone()

    estimated_sales = 0
    if prev_row is not None:
        prev_stock = prev_row[0]
        # Sales Calculation Logic:
        # If Stock(Today) < Stock(Yesterday), estimated_sales = Stock(Yesterday) - Stock(Today)
        # If Stock(Today) >= Stock(Yesterday), estimated_sales = 0
        if stock < prev_stock:
            estimated_sales = prev_stock - stock
        else:
            estimated_sales = 0

    # Upsert daily snapshot
    cur.execute(
        """
        INSERT INTO daily_snapshots (sku, recorded_date, price, stock, rating, feedback_count, estimated_sales)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (sku, recorded_date)
        DO UPDATE SET
            price = EXCLUDED.price,
            stock = EXCLUDED.stock,
            rating = EXCLUDED.rating,
            feedback_count = EXCLUDED.feedback_count,
            estimated_sales = EXCLUDED.estimated_sales;
        """,
        (sku, target_date, price, stock, rating, feedback_count, estimated_sales)
    )
    
    print(f"SKU: {sku} | Brand: {brand} | Price: {price} RUB | Stock: {stock} | "
          f"Rating: {rating} | Feedbacks: {feedback_count} | Est. Sales: {estimated_sales}")
    return True

def run_scraper():
    """
    Scrapes all tracked items stored in the database.
    """
    print(f"Scraper started at {datetime.datetime.now().isoformat()}")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT sku FROM tracked_items")
            skus = [row[0] for row in cur.fetchall()]

        if not skus:
            print("No tracked items found in database. Exiting scraper.")
            return

        print(f"Found {len(skus)} items to scrape.")
        success_count = 0
        
        for i, sku in enumerate(skus):
            # Enforce 3 seconds cooldown between lookups
            if i > 0:
                print("Waiting 3 seconds...")
                time.sleep(3)
                
            try:
                # Wrap each SKU in its own transaction block
                with conn:
                    with conn.cursor() as cur:
                        if process_sku(cur, sku):
                            success_count += 1
            except Exception as e:
                print(f"Error processing SKU {sku}: {e}")

        print(f"Scraper finished. Successfully updated {success_count}/{len(skus)} products.")
    finally:
        conn.close()

if __name__ == "__main__":
    run_scraper()
