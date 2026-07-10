import os
import psycopg2
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    Normalizes 'postgres://' to 'postgresql://' for compatibility with newer drivers.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        # Fallback to individual PostgreSQL variables if DATABASE_URL is not provided
        pg_host = os.environ.get("PGHOST")
        pg_user = os.environ.get("PGUSER")
        pg_password = os.environ.get("PGPASSWORD")
        pg_database = os.environ.get("PGDATABASE")
        pg_port = os.environ.get("PGPORT", "5432")
        if pg_host and pg_user and pg_password and pg_database:
            db_url = f"postgresql://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_database}"
        else:
            raise ValueError(
                "DATABASE_URL or individual PG connection variables (PGHOST, PGUSER, PGPASSWORD, PGDATABASE) "
                "are not set. Please ensure you have configured them in your environment."
            )
    
    # Core Fix: Automatically format connection strings starting with 'postgres://'
    # into 'postgresql://' to maintain compatibility with modern drivers.
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    return psycopg2.connect(db_url)

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

            # Migration: add is_own_store column if it doesn't exist yet (for existing DBs)
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
            
            # Create daily_snapshots table
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
