# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
from index import app
from models import db
from sqlalchemy import text, inspect
with app.app_context():
    cols = [c['name'] for c in inspect(db.engine).get_columns('materials')]
    new_cols = {
        'corrugation_ply': "VARCHAR(20) DEFAULT ''",
        'dim_length': "DECIMAL(10,2) NULL",
        'dim_width':  "DECIMAL(10,2) NULL",
        'dim_height': "DECIMAL(10,2) NULL",
        'pm_attribute': "VARCHAR(300) DEFAULT ''",
    }
    for col, defn in new_cols.items():
        if col not in cols:
            db.session.execute(text(f"ALTER TABLE materials ADD COLUMN {col} {defn}"))
            db.session.commit()
            print(f"âœ… {col} added")
        else:
            print(f"âœ”ï¸  {col} exists")
    print("\nðŸŽ‰ Done!")


