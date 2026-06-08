# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
add_image_column.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
materials table mein image_path column add karo.
Run: python add_image_column.py
"""
from index import app
from models import db
from sqlalchemy import text

with app.app_context():
    try:
        db.session.execute(text(
            "ALTER TABLE materials ADD COLUMN image_path VARCHAR(500) NULL"
        ))
        db.session.commit()
        print("âœ… image_path column added to materials table!")
    except Exception as e:
        db.session.rollback()
        print(f"â„¹ï¸  Note: {e}")
        print("   (Column might already exist â€” that's OK)")
    
    # Create upload directory
    import os
    os.makedirs('static/uploads/materials', exist_ok=True)
    print("âœ… static/uploads/materials/ directory ready")
    print("\nðŸŽ‰ Done! PM/FG items mein ab Product Image upload kar sakte hain.")


