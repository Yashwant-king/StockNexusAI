"""
StockNexus AI - Database Connection Test Script
Tests both PostgreSQL (Supabase) and CSV fallback modes.
"""
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("  StockNexus AI - Database Connection Test")
print("=" * 60)

# --- Step 1: Check DATABASE_URL ---
DATABASE_URL = os.environ.get('DATABASE_URL')
print(f"\n[1] DATABASE_URL configured: {'YES' if DATABASE_URL else 'NO (will use CSV fallback)'}")
if DATABASE_URL:
    masked = DATABASE_URL[:20] + "..." + DATABASE_URL[-15:] if len(DATABASE_URL) > 40 else "***"
    print(f"    -> Connection string: {masked}")

# --- Step 2: Test psycopg2 import ---
print(f"\n[2] Testing psycopg2 import...")
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    print(f"    [OK] psycopg2 version: {psycopg2.__version__}")
except ImportError as e:
    print(f"    [FAIL] psycopg2 not installed: {e}")
    print(f"    -> Fix: pip install psycopg2-binary")

# --- Step 3: Test database module import ---
print(f"\n[3] Testing database module import...")
try:
    import database as db
    print(f"    [OK] database.py imported successfully")
    print(f"    -> use_db() = {db.use_db()}")
except Exception as e:
    print(f"    [FAIL] Failed to import database.py: {e}")
    sys.exit(1)

# --- Step 4: Test DB connection (if configured) ---
if DATABASE_URL:
    print(f"\n[4] Testing PostgreSQL connection...")
    try:
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"    [OK] Connected to PostgreSQL!")
        print(f"    -> Server: {version.get('version', 'unknown') if isinstance(version, dict) else version}")
        
        # Check tables
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' ORDER BY table_name;
        """)
        tables = [row['table_name'] if isinstance(row, dict) else row[0] for row in cur.fetchall()]
        print(f"    -> Tables found: {', '.join(tables) if tables else 'None'}")
        
        # Check row counts
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) as cnt FROM {table};")
                cnt = cur.fetchone()
                count = cnt['cnt'] if isinstance(cnt, dict) else cnt[0]
                print(f"       - {table}: {count} rows")
            except:
                pass
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"    [FAIL] PostgreSQL connection FAILED: {e}")
else:
    print(f"\n[4] SKIP - No DATABASE_URL set, skipping PostgreSQL test")

# --- Step 5: Test init_db ---
print(f"\n[5] Testing init_db()...")
try:
    db.init_db()
    print(f"    [OK] init_db() completed")
except Exception as e:
    print(f"    [FAIL] init_db() failed: {e}")

# --- Step 6: Test init_khata_db ---
print(f"\n[6] Testing init_khata_db()...")
try:
    db.init_khata_db()
    print(f"    [OK] init_khata_db() completed")
except Exception as e:
    print(f"    [FAIL] init_khata_db() failed: {e}")

# --- Step 7: Test init_expense_db ---
print(f"\n[7] Testing init_expense_db()...")
try:
    db.init_expense_db()
    print(f"    [OK] init_expense_db() completed")
except Exception as e:
    print(f"    [FAIL] init_expense_db() failed: {e}")

# --- Step 8: Test get_all_items ---
print(f"\n[8] Testing get_all_items()...")
try:
    df = db.get_all_items()
    if df is not None and not df.empty:
        print(f"    [OK] Retrieved {len(df)} items")
        print(f"    -> Columns: {list(df.columns)}")
        print(f"    -> First item: {df.iloc[0].to_dict()}")
    else:
        print(f"    [WARN] No items found (empty inventory)")
except Exception as e:
    print(f"    [FAIL] get_all_items() failed: {e}")

# --- Step 9: Test CSV fallback ---
print(f"\n[9] Testing CSV fallback...")
CSV_PATH = 'data_set/data.csv'
if os.path.exists(CSV_PATH):
    import pandas as pd
    csv_df = pd.read_csv(CSV_PATH)
    print(f"    [OK] CSV exists: {CSV_PATH} ({len(csv_df)} rows)")
    print(f"    -> Columns: {list(csv_df.columns)}")
else:
    alt_csvs = ['grocery_inventory.csv', 'sample_inventory.csv']
    found = False
    for csv_file in alt_csvs:
        if os.path.exists(csv_file):
            import pandas as pd
            csv_df = pd.read_csv(csv_file)
            print(f"    [OK] Found alternate CSV: {csv_file} ({len(csv_df)} rows)")
            print(f"    -> Columns: {list(csv_df.columns)}")
            found = True
            break
    if not found:
        print(f"    [WARN] No CSV data files found (data_set/data.csv missing)")

# --- Step 10: Test Khata & Expenses ---
print(f"\n[10] Testing Khata & Expenses...")
try:
    customers = db.get_all_customers()
    print(f"    [OK] Khata customers: {len(customers)}")
except Exception as e:
    print(f"    [FAIL] get_all_customers() failed: {e}")

try:
    expenses = db.get_all_expenses()
    print(f"    [OK] Expenses: {len(expenses)}")
except Exception as e:
    print(f"    [FAIL] get_all_expenses() failed: {e}")

# --- Summary ---
print(f"\n{'=' * 60}")
mode = "PostgreSQL (Supabase)" if db.use_db() else "CSV Fallback"
print(f"  ACTIVE MODE: {mode}")
if not db.use_db():
    print(f"\n  To enable Supabase PostgreSQL, create a .env file with:")
    print(f"  DATABASE_URL=postgresql://user:password@host:port/dbname")
    print(f"\n  Currently the app will work fine using CSV files as storage.")
print(f"{'=' * 60}")
