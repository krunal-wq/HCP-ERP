# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
migrate_supplier_addresses.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
suppliers table mein addresses JSON column add karo.
Run: python migrate_supplier_addresses.py
"""
from index import app
from models import db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)
    try:
        cols = [c['name'] for c in inspector.get_columns('suppliers')]
        if 'addresses' not in cols:
            db.session.execute(text("ALTER TABLE suppliers ADD COLUMN addresses TEXT NULL"))
            db.session.commit()
            print("âœ… addresses column added!")
        else:
            print("âœ”ï¸  addresses already exists")
    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
    print("\nðŸŽ‰ Done!")


