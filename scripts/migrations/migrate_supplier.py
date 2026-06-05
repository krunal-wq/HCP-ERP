# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
migrate_supplier.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Suppliers table create karo.
Run: python migrate_supplier.py
"""
from index import app
from models import db

with app.app_context():
    db.create_all()
    print("âœ… suppliers table created!")
    print("ðŸŽ‰ Done! Server restart karo.")


