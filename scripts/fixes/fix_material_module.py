# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
fix_material_module.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Material module ko DB mein register karo taaki permissions panel mein show ho.
Run: python fix_material_module.py
"""

from index import app          # â† app.py nahi, index.py hai
from models import db, Module  # â† Module model yahan hai

with app.app_context():

    # â”€â”€ 1. Module table mein 'material' add karo â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    existing = Module.query.filter_by(name='material').first()
    if existing:
        print(f"âœ… 'material' module already exists (id={existing.id})")
    else:
        m = Module(
            name        = 'material',
            label       = 'Item Master',
            icon        = 'ðŸ“¦',
            url_prefix  = '/material',
            sort_order  = 19,
            is_active   = True,
        )
        db.session.add(m)
        db.session.commit()
        print(f"âœ… 'material' module registered successfully! (id={m.id})")

    # â”€â”€ 2. Verify â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    mat = Module.query.filter_by(name='material').first()
    print(f"\nModule details:")
    print(f"  id        : {mat.id}")
    print(f"  name      : {mat.name}")
    print(f"  label     : {mat.label}")
    print(f"  is_active : {mat.is_active}")

    print("\nðŸŽ‰ Done! Ab /admin/acp permissions panel mein")
    print("   'Procurement â€” Item Master' section dikhega.")
    print("\n   Agar nahi dikha to browser mein visit karo:")
    print("   http://127.0.0.1:5000/seed-modules")


