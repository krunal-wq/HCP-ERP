# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
add_npd_fee_paid_at_column.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
NPD projects table mein `npd_fee_paid_at` column add karo. Yeh us moment
ka timestamp store karta hai jab user ne NPD form me "NPD Fee Received"
checkbox tick kiya (unchecked â†’ checked). Iska use /npd/fees-report
page karta hai from-date / to-date filter ke liye.

Existing rows jin me `npd_fee_paid=1` hai un me backfill ho jaata hai
created_at se â€” taaki purani entries report me bhi dikhein.

Run:
    python add_npd_fee_paid_at_column.py
"""
from index import app
from models import db
from sqlalchemy import text

with app.app_context():
    print("ðŸ”§ Adding npd_fee_paid_at column to npd_projects table...\n")

    # â”€â”€ Add the column â”€â”€
    try:
        db.session.execute(text(
            "ALTER TABLE npd_projects ADD COLUMN npd_fee_paid_at DATETIME NULL"
        ))
        db.session.commit()
        print("  âœ… Added column: npd_fee_paid_at")
    except Exception as e:
        db.session.rollback()
        err = str(e).lower()
        if 'duplicate' in err or 'already exists' in err:
            print("  âœ”ï¸  Column already exists: npd_fee_paid_at")
        else:
            print(f"  âš ï¸  Error adding column: {e}")

    # â”€â”€ Backfill existing rows where fee is already paid â”€â”€
    # Use created_at as a sensible default. Without this, all old paid
    # rows would have NULL fee_paid_at and silently disappear from the
    # date-range report.
    try:
        result = db.session.execute(text("""
            UPDATE npd_projects
               SET npd_fee_paid_at = created_at
             WHERE npd_fee_paid = 1
               AND npd_fee_paid_at IS NULL
        """))
        db.session.commit()
        try:
            count = result.rowcount
        except Exception:
            count = '?'
        print(f"  âœ… Backfilled {count} existing paid row(s) with created_at")
    except Exception as e:
        db.session.rollback()
        print(f"  âš ï¸  Backfill failed: {e}")

    print("\nðŸŽ‰ Done. NPD Fees Report available at /npd/fees-report")


