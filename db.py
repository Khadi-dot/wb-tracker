import os
import psycopg2
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

IS_SQLITE = False

class SQLiteCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, sql, params=None):
        if params is not None:
            # Replace %s with ? for SQLite placeholders
            sql = sql.replace('%s', '?')
            self.cursor.execute(sql, params)
        else:
            self.cursor.execute(sql)
            
    def fetchone(self):
        return self.cursor.fetchone()
        
    def fetchall(self):
        return self.cursor.fetchall()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cursor.close()

class DBConnectionWrapper:
    def __init__(self, conn, is_sqlite):
        self.conn = conn
        self.is_sqlite = is_sqlite
        
    def cursor(self):
        cursor = self.conn.cursor()
        if self.is_sqlite:
            return SQLiteCursorWrapper(cursor)
        return cursor
        
    def commit(self):
        self.conn.commit()
        
    def rollback(self):
        self.conn.rollback()
        
    def close(self):
        self.conn.close()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()

def get_db_connection():
    """
    Establishes and returns a connection to the database.
    Falls back to SQLite if no PostgreSQL environment variables are configured.
    """
    global IS_SQLITE
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pg_host = os.environ.get("PGHOST")
        pg_user = os.environ.get("PGUSER")
        pg_password = os.environ.get("PGPASSWORD")
        pg_database = os.environ.get("PGDATABASE")
        pg_port = os.environ.get("PGPORT", "5432")
        if pg_host and pg_user and pg_password and pg_database:
            db_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
            
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        if db_url.startswith("postgresql://"):
            IS_SQLITE = False
            conn = psycopg2.connect(db_url)
            return DBConnectionWrapper(conn, is_sqlite=False)
            
    # Fallback to local SQLite
    IS_SQLITE = True
    db_dir = Path(__file__).resolve().parent / "data"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "wb_tracker.db"
    conn = sqlite3.connect(str(db_path))
    return DBConnectionWrapper(conn, is_sqlite=True)

def seed_products(cur, is_sqlite):
    """
    Seeds database from wb_details.json if available.
    """
    import json
    json_path = Path(__file__).resolve().parent.parent / "wb_details.json"
    if not json_path.exists():
        return
        
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        for seller_info, products in data.items():
            is_own = "Ours" in seller_info or "4002144" in seller_info
            category = "Other" if "HOME STYLE" in seller_info else "T-shirts"
            brand_name = seller_info.split("(")[1].replace(")", "").strip() if "(" in seller_info else "Unknown Brand"
            
            for p in products:
                sku = str(p.get("id"))
                name = p.get("name", "Unknown Product")
                brand = p.get("brand") or brand_name
                
                # Insert tracked item
                sql_item = """
                    INSERT INTO tracked_items (sku, name, brand, category, is_own_store)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (sku) DO UPDATE SET
                        name = EXCLUDED.name,
                        brand = EXCLUDED.brand,
                        category = EXCLUDED.category,
                        is_own_store = EXCLUDED.is_own_store
                """
                cur.execute(sql_item, (sku, name, brand, category, is_own))
                
                # Insert daily snapshot
                sizes = p.get("sizes", [])
                price = 0
                if sizes:
                    price_obj = sizes[0].get("price", {})
                    price = int(price_obj.get("product", 0) / 100)
                    if not price:
                        price = int(price_obj.get("basic", 0) / 100)
                        
                stock = p.get("totalQuantity")
                if stock is None:
                    stock = 0
                    for size in sizes:
                        for stock_item in size.get("stocks", []):
                            stock += stock_item.get("qty", 0)
                            
                rating = p.get("reviewRating") or p.get("rating") or 0.0
                feedback_count = p.get("feedbacks") or p.get("nmFeedbacks") or 0
                
                # We seed as of today's date
                if is_sqlite:
                    sql_snap = """
                        INSERT INTO daily_snapshots (sku, recorded_date, price, stock, rating, feedback_count, estimated_sales)
                        VALUES (?, date('now'), ?, ?, ?, ?, 0)
                        ON CONFLICT (sku, recorded_date) DO UPDATE SET
                            price = excluded.price,
                            stock = excluded.stock,
                            rating = excluded.rating,
                            feedback_count = excluded.feedback_count
                    """
                else:
                    sql_snap = """
                        INSERT INTO daily_snapshots (sku, recorded_date, price, stock, rating, feedback_count, estimated_sales)
                        VALUES (%s, CURRENT_DATE, %s, %s, %s, %s, 0)
                        ON CONFLICT (sku, recorded_date) DO UPDATE SET
                            price = EXCLUDED.price,
                            stock = EXCLUDED.stock,
                            rating = EXCLUDED.rating,
                            feedback_count = EXCLUDED.feedback_count
                    """
                cur.execute(sql_snap, (sku, price, stock, rating, feedback_count))
    except Exception as e:
        print(f"Error seeding database: {e}")

def init_db():
    """
    Initializes the database by creating the required tables if they do not exist.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create tracked_items table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tracked_items (
                    sku VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255),
                    brand VARCHAR(100),
                    category VARCHAR(50),
                    is_own_store BOOLEAN DEFAULT FALSE
                );
            """)

            # Migration: add is_own_store column if it doesn't exist
            if not IS_SQLITE:
                cur.execute("""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name='tracked_items' AND column_name='is_own_store'
                        ) THEN
                            ALTER TABLE tracked_items ADD COLUMN is_own_store BOOLEAN DEFAULT FALSE;
                        END IF;
                    END$$;
                """)
            else:
                cur.execute("PRAGMA table_info(tracked_items)")
                cols = [row[1] for row in cur.fetchall()]
                if 'is_own_store' not in cols:
                    cur.execute("ALTER TABLE tracked_items ADD COLUMN is_own_store BOOLEAN DEFAULT FALSE")
            
            # Create daily_snapshots table
            if IS_SQLITE:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS daily_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sku VARCHAR(50) REFERENCES tracked_items(sku) ON DELETE CASCADE,
                        recorded_date DATE DEFAULT CURRENT_DATE,
                        price INT,
                        stock INT,
                        rating NUMERIC(3,2),
                        feedback_count INT,
                        estimated_sales INT DEFAULT 0,
                        UNIQUE(sku, recorded_date)
                    );
                """)
            else:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS daily_snapshots (
                        id SERIAL PRIMARY KEY,
                        sku VARCHAR(50) REFERENCES tracked_items(sku) ON DELETE CASCADE,
                        recorded_date DATE DEFAULT CURRENT_DATE,
                        price INT,
                        stock INT,
                        rating NUMERIC(3,2),
                        feedback_count INT,
                        estimated_sales INT DEFAULT 0,
                        UNIQUE(sku, recorded_date)
                    );
                """)
            
            # Seed our scraped data
            seed_products(cur, IS_SQLITE)
            
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    print("Initializing database tables...")
    init_db()
    print("Database initialized successfully.")
