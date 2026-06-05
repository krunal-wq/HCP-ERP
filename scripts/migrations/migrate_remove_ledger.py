# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
migrate_remove_ledger.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
suppliers table se ledger_name column remove karo.
Run: python migrate_remove_ledger.py
"""
from index import app
from models import db
from sqlalchemy import text, inspect

with app.app_context():
    inspector = inspect(db.engine)
    cols = [c['name'] for c in inspector.get_columns('suppliers')]
    if 'ledger_name' in cols:
        try:
            db.session.execute(text("ALTER TABLE suppliers DROP COLUMN ledger_name"))
            db.session.commit()
            print("âœ… ledger_name column removed!")
        except Exception as e:
            db.session.rollback()
            print(f"âŒ Error: {e}")
    else:
        print("âœ”ï¸  ledger_name already removed")
    print("\nðŸŽ‰ Done!")


