"""
Database module for StockNexus AI.
Handles all PostgreSQL (Supabase) connections and CRUD operations.
Falls back to CSV mode if DATABASE_URL is not set.
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get('DATABASE_URL')
CSV_PATH = 'data_set/data.csv'
COLUMNS = ['product_id', 'product_name', 'quantity_stock', 'minimum_stock_level', 'total_revenue', 'expiry_date']


def get_connection():
    """Get a PostgreSQL database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """Create the inventory table if it doesn't exist."""
    if not DATABASE_URL:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                product_id VARCHAR(100),
                product_name VARCHAR(255) NOT NULL,
                quantity_stock INTEGER DEFAULT 0,
                minimum_stock_level INTEGER DEFAULT 0,
                total_revenue DECIMAL(12, 2) DEFAULT 0.0,
                expiry_date VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"❌ Database init error: {str(e)}")


def use_db():
    """Returns True if database is configured, otherwise False (use CSV)."""
    return DATABASE_URL is not None and DATABASE_URL.strip() != ''


def get_all_items():
    """Get all inventory items as a Pandas DataFrame."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date, created_at FROM inventory ORDER BY id;")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            if rows:
                return pd.DataFrame([dict(r) for r in rows])
            else:
                return pd.DataFrame(columns=COLUMNS)
        except Exception as e:
            print(f"DB read error: {e}. Falling back to CSV.")

    # CSV fallback
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        return df
    return pd.DataFrame(columns=COLUMNS)


def get_last_updated():
    """Get the timestamp of the most recently added inventory item."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT MAX(created_at) as last_updated FROM inventory;")
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and row['last_updated']:
                return row['last_updated'].strftime('%d %b %Y, %I:%M %p')
            return None
        except Exception as e:
            print(f"DB last_updated error: {e}")
            return None

    # CSV fallback — use file modification time
    if os.path.exists(CSV_PATH):
        import datetime
        mtime = os.path.getmtime(CSV_PATH)
        return datetime.datetime.fromtimestamp(mtime).strftime('%d %b %Y, %I:%M %p')
    return None


def add_item(product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date):
    """Add a new item to the inventory."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO inventory (product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date))
            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ DB: Added {product_name} successfully")
            return True
        except Exception as e:
            print(f"❌ DB add item error: {e}. Falling back to CSV...")

    # CSV fallback (always runs if DB fails or is not configured)
    try:
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df = pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame(columns=COLUMNS)
        new_row = pd.DataFrame([{
            'product_id': product_id, 'product_name': product_name,
            'quantity_stock': quantity_stock, 'minimum_stock_level': minimum_stock_level,
            'total_revenue': total_revenue, 'expiry_date': expiry_date
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_PATH, index=False)
        return True
    except Exception as e:
        print(f"CSV add item error: {e}")
        return False


def delete_item(item_id):
    """Delete an item by its database ID."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM inventory WHERE id = %s;", (item_id,))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"DB delete error: {e}")
            return False
    return False


def update_item(item_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date):
    """Update an existing item by its database ID."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE inventory 
                SET product_name=%s, quantity_stock=%s, minimum_stock_level=%s, total_revenue=%s, expiry_date=%s
                WHERE id=%s;
            """, (product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date, item_id))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"DB update error: {e}")
            return False
    return False


def bulk_upload_from_df(df):
    """Replace all inventory data from a DataFrame (used during CSV upload)."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            # Clear existing data
            cur.execute("DELETE FROM inventory;")
            # Insert all rows from dataframe
            for _, row in df.iterrows():
                cur.execute("""
                    INSERT INTO inventory (product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (
                    str(row.get('product_id', '')),
                    str(row.get('product_name', '')),
                    int(row.get('quantity_stock', 0)),
                    int(row.get('minimum_stock_level', 0)),
                    float(row.get('total_revenue', 0)),
                    str(row.get('expiry_date', ''))
                ))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ DB bulk upload error: {e}. Falling back to CSV...")

    # CSV fallback
    try:
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df.to_csv(CSV_PATH, index=False)
        return True
    except Exception as e:
        print(f"CSV bulk upload error: {e}")
        return False
