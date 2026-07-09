import os
import psycopg2

def get_db_connection():
    """
    Establishes and returns a connection to the PostgreSQL database.
    Normalizes 'postgres://' to 'postgresql://' for compatibility with newer drivers.
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise ValueError(
            "DATABASE_URL environment variable is not set. "
            "Please ensure you have configured it in your environment or .env file."
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
                    category VARCHAR(50)
                );
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
