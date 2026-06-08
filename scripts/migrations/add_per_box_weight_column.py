# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
add_per_box_weight_column.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Materials table mein 'per_box_weight' column add karo (FG ke liye).
Per box weight = ek full box ka total weight (in KG).

Run: python add_per_box_weight_column.py
"""
from index import app
from models import db
from sqlalchemy import text

COLUMNS = [
    ("per_box_weight",     "DECIMAL(10,3) DEFAULT 0"),
    ("per_box_weight_uom", "VARCHAR(30)   DEFAULT 'KG'"),
]

with app.app_context():
    print("ðŸ”§ Adding per_box_weight column to materials table...\n")
    for col, col_def in COLUMNS:
        try:
            db.session.execute(text(f"ALTER TABLE materials ADD COLUMN {col} {col_def}"))
            db.session.commit()
            print(f"  âœ… Added: {col}")
        except Exception as e:
            db.session.rollback()
            err = str(e).lower()
            if 'duplicate' in err or 'already exists' in err:
                print(f"  âœ”ï¸  Already exists: {col}")
            else:
                print(f"  âš ï¸  {col}: {e}")

    print("\nðŸŽ‰ Done! Ab FG item master mein Per Box Weight field available hai.")


