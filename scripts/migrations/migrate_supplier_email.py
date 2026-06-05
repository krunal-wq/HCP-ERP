# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
from index import app
from models import db
from sqlalchemy import text, inspect
with app.app_context():
    cols = [c['name'] for c in inspect(db.engine).get_columns('suppliers')]
    if 'email_list' not in cols:
        db.session.execute(text("ALTER TABLE suppliers ADD COLUMN email_list TEXT NULL"))
        db.session.commit()
        print("âœ… email_list column added!")
    else:
        print("âœ”ï¸  Already exists")


