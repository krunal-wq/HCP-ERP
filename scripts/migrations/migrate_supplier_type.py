# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""Expand supplier_type column to VARCHAR(20) to support 'RM,PM'"""
from index import app
from models import db
from sqlalchemy import text
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE suppliers MODIFY COLUMN supplier_type VARCHAR(20) DEFAULT 'RM'"))
        db.session.commit()
        print("âœ… supplier_type column expanded!")
    except Exception as e:
        db.session.rollback()
        print(f"Note: {e}")
    print("ðŸŽ‰ Done!")


