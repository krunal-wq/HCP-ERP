# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Run this script ONCE to add middle_name column to employees table.
Usage:  python add_middle_name_column.py
"""
import sqlite3, os

# Sabse pehle current directory mein dhundega, phir subdirs mein
def find_db():
    possible_paths = [
        os.path.join(os.path.dirname(__file__), 'erp.db'),
        os.path.join(os.path.dirname(__file__), 'instance', 'erp.db'),
        os.path.join(os.path.dirname(__file__), 'database', 'erp.db'),
        os.path.join(os.path.dirname(__file__), 'db', 'erp.db'),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

def migrate():
    db_path = find_db()

    if not db_path:
        print("âŒ erp.db file nahi mili!")
        print("ðŸ‘‰ Manually DB path batao â€” script mein DB_PATH variable set karo.")
        print("   Example: DB_PATH = r'D:\\hcperpnew\\instance\\erp.db'")
        return

    print(f"âœ… DB found: {db_path}")
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # All tables list karo
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    print(f"ðŸ“‹ Tables in DB: {tables}")

    if 'employees' not in tables:
        print("âŒ 'employees' table nahi mili!")
        print(f"ðŸ‘‰ Available tables: {tables}")
        conn.close()
        return

    # Check if column already exists
    cur.execute("PRAGMA table_info(employees)")
    cols = [row[1] for row in cur.fetchall()]

    if 'middle_name' not in cols:
        cur.execute("ALTER TABLE employees ADD COLUMN middle_name VARCHAR(100)")
        conn.commit()
        print("âœ… middle_name column added successfully.")
    else:
        print("â„¹ï¸  middle_name column already exists â€” nothing to do.")

    conn.close()

if __name__ == '__main__':
    migrate()


