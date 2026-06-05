# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
remove_supplier_columns.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Materials table se supplier_name aur supplier_code columns drop karo.
Run: python remove_supplier_columns.py
"""
from index import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        # MySQL / MariaDB
        db.session.execute(text("ALTER TABLE materials DROP COLUMN IF EXISTS supplier_name"))
        db.session.execute(text("ALTER TABLE materials DROP COLUMN IF EXISTS supplier_code"))
        db.session.commit()
        print("âœ… supplier_name aur supplier_code columns successfully dropped!")
    except Exception as e:
        db.session.rollback()
        print(f"âš ï¸  Error (columns already removed ya nahi mili): {e}")
    
    # Verify
    try:
        cols = db.session.execute(text("SHOW COLUMNS FROM materials")).fetchall()
        col_names = [c[0] for c in cols]
        if 'supplier_name' not in col_names and 'supplier_code' not in col_names:
            print("âœ… Verified: Supplier columns removed from DB")
        else:
            print("âš ï¸  Columns still present â€” manually drop karo")
    except:
        pass


