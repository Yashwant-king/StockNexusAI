"""
Database module for StockNexus AI.
Handles all PostgreSQL (Supabase) connections and CRUD operations.
Falls back to CSV mode if DATABASE_URL is not set.
"""

import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv() # Force load .env so local tokens work properly

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
    """Add a new item to the inventory or update if it exists."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Check if it already exists
            cur.execute("SELECT id, quantity_stock FROM inventory WHERE product_id = %s;", (str(product_id),))
            existing = cur.fetchone()
            
            if existing:
                cur.execute("""
                    UPDATE inventory 
                    SET product_name=%s, quantity_stock=%s, minimum_stock_level=%s, total_revenue=%s, expiry_date=%s
                    WHERE product_id=%s;
                """, (str(product_name), int(quantity_stock), int(minimum_stock_level), float(total_revenue), str(expiry_date), str(product_id)))
            else:
                cur.execute("""
                    INSERT INTO inventory (product_id, product_name, quantity_stock, minimum_stock_level, total_revenue, expiry_date)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (str(product_id), str(product_name), int(quantity_stock), int(minimum_stock_level), float(total_revenue), str(expiry_date)))
                
            conn.commit()
            cur.close()
            conn.close()
            print(f"✅ DB: Added/Updated {product_name} successfully")
            return True
        except Exception as e:
            print(f"❌ DB add item error: {e}. Falling back to CSV...")

    # CSV fallback (always runs if DB fails or is not configured)
    try:
        os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
        df = pd.read_csv(CSV_PATH) if os.path.exists(CSV_PATH) else pd.DataFrame(columns=COLUMNS)
        
        idx = df.index[df['product_id'].astype(str) == str(product_id)]
        if not idx.empty:
            df.loc[idx, 'product_name'] = str(product_name)
            df.loc[idx, 'quantity_stock'] = int(quantity_stock)
            df.loc[idx, 'minimum_stock_level'] = int(minimum_stock_level)
            df.loc[idx, 'total_revenue'] = float(total_revenue)
            df.loc[idx, 'expiry_date'] = str(expiry_date)
        else:
            new_row = pd.DataFrame([{
                'product_id': str(product_id), 'product_name': str(product_name),
                'quantity_stock': int(quantity_stock), 'minimum_stock_level': int(minimum_stock_level),
                'total_revenue': float(total_revenue), 'expiry_date': str(expiry_date)
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


# ═══════════════════════════════════════════════
# KHATA (CREDIT BOOK) SYSTEM
# ═══════════════════════════════════════════════

KHATA_CUSTOMERS_CSV = 'data_set/khata_customers.csv'
KHATA_TRANSACTIONS_CSV = 'data_set/khata_transactions.csv'


def init_khata_db():
    """Create khata tables if using database."""
    if not DATABASE_URL:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS khata_customers (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS khata_transactions (
                id SERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                type VARCHAR(10) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                note VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Add the new CRM Columns (Safe for existing tables)
        cur.execute("ALTER TABLE khata_customers ADD COLUMN IF NOT EXISTS email VARCHAR(255);")
        cur.execute("ALTER TABLE khata_customers ADD COLUMN IF NOT EXISTS address VARCHAR(500);")
        cur.execute("ALTER TABLE khata_customers ADD COLUMN IF NOT EXISTS loyalty_points INTEGER DEFAULT 0;")
        
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Khata tables initialized!")
    except Exception as e:
        print(f"❌ Khata DB init error: {e}")


def get_all_customers():
    """Get all customers with their balance."""
    customers = []

    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT c.id, c.name, c.phone, c.created_at,
                    COALESCE(SUM(CASE WHEN t.type='udhar' THEN t.amount ELSE 0 END), 0) as total_udhar,
                    COALESCE(SUM(CASE WHEN t.type='payment' THEN t.amount ELSE 0 END), 0) as total_paid
                FROM khata_customers c
                LEFT JOIN khata_transactions t ON t.customer_id = c.id
                GROUP BY c.id, c.name, c.phone, c.created_at
                ORDER BY c.name;
            """)
            rows = cur.fetchall()
            cur.close()
            conn.close()
            for r in rows:
                customers.append({
                    'id': r['id'], 'name': r['name'], 'phone': r['phone'] or '',
                    'total_udhar': float(r['total_udhar']),
                    'total_paid': float(r['total_paid']),
                    'balance': float(r['total_udhar']) - float(r['total_paid']),
                    'created_at': r['created_at']
                })
            return customers
        except Exception as e:
            print(f"❌ DB get customers error: {e}")

    # CSV fallback
    try:
        if not os.path.exists(KHATA_CUSTOMERS_CSV):
            return []
        cust_df = pd.read_csv(KHATA_CUSTOMERS_CSV)
        trans_df = pd.read_csv(KHATA_TRANSACTIONS_CSV) if os.path.exists(KHATA_TRANSACTIONS_CSV) else pd.DataFrame(columns=['id','customer_id','type','amount','note','created_at'])
        for _, c in cust_df.iterrows():
            ct = trans_df[trans_df['customer_id'] == c['id']]
            total_udhar = ct[ct['type'] == 'udhar']['amount'].astype(float).sum() if len(ct) > 0 else 0
            total_paid = ct[ct['type'] == 'payment']['amount'].astype(float).sum() if len(ct) > 0 else 0
            customers.append({
                'id': int(c['id']), 'name': c['name'], 'phone': str(c.get('phone', '')),
                'total_udhar': total_udhar, 'total_paid': total_paid,
                'balance': total_udhar - total_paid
            })
    except Exception as e:
        print(f"CSV khata read error: {e}")
    return customers


def add_customer(name, phone):
    """Add a new customer."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO khata_customers (name, phone) VALUES (%s, %s) RETURNING id;", (name, phone))
            new_id = cur.fetchone()['id']
            conn.commit()
            cur.close()
            conn.close()
            return new_id
        except Exception as e:
            print(f"❌ DB add customer error: {e}")

    # CSV fallback
    try:
        os.makedirs('data_set', exist_ok=True)
        if os.path.exists(KHATA_CUSTOMERS_CSV):
            df = pd.read_csv(KHATA_CUSTOMERS_CSV)
            new_id = int(df['id'].max()) + 1 if len(df) > 0 else 1
        else:
            df = pd.DataFrame(columns=['id', 'name', 'phone', 'created_at'])
            new_id = 1
        from datetime import datetime
        new_row = pd.DataFrame([{'id': new_id, 'name': name, 'phone': phone, 'created_at': datetime.now().isoformat()}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(KHATA_CUSTOMERS_CSV, index=False)
        return new_id
    except Exception as e:
        print(f"CSV add customer error: {e}")
        return None


def add_transaction(customer_id, txn_type, amount, note=''):
    """Add udhar or payment transaction."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO khata_transactions (customer_id, type, amount, note) VALUES (%s, %s, %s, %s);",
                        (customer_id, txn_type, amount, note))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ DB add transaction error: {e}")

    # CSV fallback
    try:
        os.makedirs('data_set', exist_ok=True)
        if os.path.exists(KHATA_TRANSACTIONS_CSV):
            df = pd.read_csv(KHATA_TRANSACTIONS_CSV)
            new_id = int(df['id'].max()) + 1 if len(df) > 0 else 1
        else:
            df = pd.DataFrame(columns=['id', 'customer_id', 'type', 'amount', 'note', 'created_at'])
            new_id = 1
        from datetime import datetime
        new_row = pd.DataFrame([{'id': new_id, 'customer_id': int(customer_id), 'type': txn_type, 'amount': float(amount), 'note': note, 'created_at': datetime.now().isoformat()}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(KHATA_TRANSACTIONS_CSV, index=False)
        return True
    except Exception as e:
        print(f"CSV add transaction error: {e}")
        return False


def get_customer_transactions(customer_id):
    """Get all transactions for a customer."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM khata_transactions WHERE customer_id = %s ORDER BY created_at DESC;", (customer_id,))
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"❌ DB get transactions error: {e}")

    # CSV fallback
    try:
        if not os.path.exists(KHATA_TRANSACTIONS_CSV):
            return []
        df = pd.read_csv(KHATA_TRANSACTIONS_CSV)
        ct = df[df['customer_id'] == int(customer_id)].sort_values('created_at', ascending=False)
        return ct.to_dict('records')
    except Exception as e:
        print(f"CSV get transactions error: {e}")
        return []


def delete_customer(customer_id):
    """Delete a customer and their transactions."""
    deleted = False
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM khata_transactions WHERE customer_id = %s;", (customer_id,))
            cur.execute("DELETE FROM khata_customers WHERE id = %s;", (customer_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ DB delete customer error: {e}")

    # CSV fallback
    try:
        if os.path.exists(KHATA_CUSTOMERS_CSV):
            df = pd.read_csv(KHATA_CUSTOMERS_CSV)
            df = df[df['id'] != int(customer_id)]
            df.to_csv(KHATA_CUSTOMERS_CSV, index=False)
            deleted = True
        if os.path.exists(KHATA_TRANSACTIONS_CSV):
            df = pd.read_csv(KHATA_TRANSACTIONS_CSV)
            df = df[df['customer_id'] != int(customer_id)]
            df.to_csv(KHATA_TRANSACTIONS_CSV, index=False)
    except Exception as e:
        print(f"CSV delete customer error: {e}")
    return deleted

# ═══════════════════════════════════════════════
# EXPENSES TRACKING SYSTEM
# ═══════════════════════════════════════════════

EXPENSES_CSV = 'data_set/expenses.csv'

def init_expense_db():
    """Create expenses table if using database."""
    if not DATABASE_URL:
        return
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                description VARCHAR(255) NOT NULL,
                amount DECIMAL(12,2) NOT NULL,
                date VARCHAR(20),
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Expense table initialized!")
    except Exception as e:
        print(f"❌ Expense DB init error: {e}")

def get_all_expenses():
    """Get all expenses."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM expenses ORDER BY id DESC;")
            rows = cur.fetchall()
            cur.close()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"❌ DB get expenses error: {e}")

    # CSV fallback
    try:
        if not os.path.exists(EXPENSES_CSV):
            return []
        df = pd.read_csv(EXPENSES_CSV)
        return df.sort_values(by='id', ascending=False).to_dict('records')
    except Exception as e:
        print(f"CSV get expenses error: {e}")
    return []

def add_expense(description, amount, date):
    """Add a new expense."""
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO expenses (description, amount, date) VALUES (%s, %s, %s);",
                        (description, amount, date))
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ DB add expense error: {e}")

    # CSV fallback
    try:
        os.makedirs('data_set', exist_ok=True)
        if os.path.exists(EXPENSES_CSV):
            df = pd.read_csv(EXPENSES_CSV)
            new_id = int(df['id'].max()) + 1 if len(df) > 0 else 1
        else:
            df = pd.DataFrame(columns=['id', 'description', 'amount', 'date', 'created_at'])
            new_id = 1
        from datetime import datetime
        new_row = pd.DataFrame([{'id': new_id, 'description': str(description), 'amount': float(amount), 'date': str(date), 'created_at': datetime.now().isoformat()}])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(EXPENSES_CSV, index=False)
        return True
    except Exception as e:
        print(f"CSV add expense error: {e}")
        return False

def delete_expense(expense_id):
    """Delete an expense."""
    deleted = False
    if use_db():
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM expenses WHERE id = %s;", (expense_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"❌ DB delete expense error: {e}")

    # CSV fallback
    try:
        if os.path.exists(EXPENSES_CSV):
            df = pd.read_csv(EXPENSES_CSV)
            df = df[df['id'] != int(expense_id)]
            df.to_csv(EXPENSES_CSV, index=False)
            deleted = True
    except Exception as e:
        print(f"CSV delete expense error: {e}")
    return deleted
