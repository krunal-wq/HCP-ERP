# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Fix Employee Types + Locations
Run: python fix_emp_types.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from index import app, db
from sqlalchemy import text

KEEP_TYPES = ['HCP OFFICE', 'HCP FACTORY STAFF', 'HCP WORKER', 'HCP CONTRACTOR', 'WFH']
KEEP_LOCS  = ['Office', 'Factory']

with app.app_context():
    with db.engine.connect() as conn:

        # â”€â”€ Employee Types â”€â”€
        print("\nâ”€â”€ Employee Types â”€â”€")
        # Delete all then re-insert in order
        conn.execute(text("DELETE FROM employee_type_master"))
        for i, name in enumerate(KEEP_TYPES):
            conn.execute(text(
                "INSERT INTO employee_type_master (name, sort_order, is_active) VALUES (:n, :s, 1)"
            ), {'n': name, 's': i})
            print(f"  âœ… {name}")

        # â”€â”€ Locations â”€â”€
        print("\nâ”€â”€ Locations â”€â”€")
        conn.execute(text("DELETE FROM employee_location_master"))
        for i, name in enumerate(KEEP_LOCS):
            conn.execute(text(
                "INSERT INTO employee_location_master (name, sort_order, is_active) VALUES (:n, :s, 1)"
            ), {'n': name, 's': i})
            print(f"  âœ… {name}")

        conn.commit()

    print("\nâœ… Done! Server restart karo.\n")


