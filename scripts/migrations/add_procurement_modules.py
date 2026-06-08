# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
add_procurement_modules.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Procurement module hierarchy DB mein setup karo.

Structure:
  Procurement (top-level parent)
  â””â”€â”€ Purchase (child of Procurement)
      â”œâ”€â”€ Raw Material     â†’ /material?item_type=RM
      â”œâ”€â”€ Packing Material â†’ /material?item_type=PM
      â””â”€â”€ Finish Goods     â†’ /material?item_type=FG

Purana standalone 'material' module deactivate ho jaayega.

Run: python add_procurement_modules.py
"""

from index import app
from models import db
from models.permission import Module

with app.app_context():

    print("ðŸ”§ Procurement Module Hierarchy Setup...")

    # â”€â”€ 1. Procurement (top-level parent) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    proc = Module.query.filter_by(name='procurement').first()
    if not proc:
        proc = Module(
            name       = 'procurement',
            label      = 'Procurement',
            icon       = 'ðŸ›’',
            url_prefix = '',
            sort_order = 19,
            is_active  = True,
            parent_id  = None,
        )
        db.session.add(proc)
        db.session.flush()
        print(f"  âœ… Created 'procurement' module (id={proc.id})")
    else:
        proc.is_active  = True
        proc.parent_id  = None
        proc.sort_order = 19
        proc.label      = 'Procurement'
        proc.icon       = 'ðŸ›’'
        print(f"  âœ”ï¸  'procurement' already exists (id={proc.id}) â€” updated")

    # â”€â”€ 2. Purchase (child of Procurement) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    purchase = Module.query.filter_by(name='purchase').first()
    if not purchase:
        purchase = Module(
            name       = 'purchase',
            label      = 'Purchase',
            icon       = 'ðŸ›ï¸',
            url_prefix = '',
            sort_order = 20,
            is_active  = True,
            parent_id  = proc.id,
        )
        db.session.add(purchase)
        db.session.flush()
        print(f"  âœ… Created 'purchase' module (id={purchase.id})")
    else:
        purchase.parent_id  = proc.id
        purchase.is_active  = True
        purchase.sort_order = 20
        purchase.label      = 'Purchase'
        purchase.icon       = 'ðŸ›ï¸'
        print(f"  âœ”ï¸  'purchase' already exists (id={purchase.id}) â€” updated")

    # â”€â”€ 3. Raw Material (grandchild) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    rm = Module.query.filter_by(name='purchase_rm').first()
    if not rm:
        rm = Module(
            name       = 'purchase_rm',
            label      = 'Raw Material',
            icon       = 'ðŸ§ª',
            url_prefix = '/material?item_type=RM',
            sort_order = 21,
            is_active  = True,
            parent_id  = purchase.id,
        )
        db.session.add(rm)
        print(f"  âœ… Created 'purchase_rm' module")
    else:
        rm.parent_id  = purchase.id
        rm.is_active  = True
        rm.url_prefix = '/material?item_type=RM'
        print(f"  âœ”ï¸  'purchase_rm' already exists â€” updated")

    # â”€â”€ 4. Packing Material (grandchild) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    pm = Module.query.filter_by(name='purchase_pm').first()
    if not pm:
        pm = Module(
            name       = 'purchase_pm',
            label      = 'Packing Material',
            icon       = 'ðŸ“¦',
            url_prefix = '/material?item_type=PM',
            sort_order = 22,
            is_active  = True,
            parent_id  = purchase.id,
        )
        db.session.add(pm)
        print(f"  âœ… Created 'purchase_pm' module")
    else:
        pm.parent_id  = purchase.id
        pm.is_active  = True
        pm.url_prefix = '/material?item_type=PM'
        print(f"  âœ”ï¸  'purchase_pm' already exists â€” updated")

    # â”€â”€ 5. Finish Goods (grandchild) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    fg = Module.query.filter_by(name='purchase_fg').first()
    if not fg:
        fg = Module(
            name       = 'purchase_fg',
            label      = 'Finish Goods',
            icon       = 'âœ…',
            url_prefix = '/material?item_type=FG',
            sort_order = 23,
            is_active  = True,
            parent_id  = purchase.id,
        )
        db.session.add(fg)
        print(f"  âœ… Created 'purchase_fg' module")
    else:
        fg.parent_id  = purchase.id
        fg.is_active  = True
        fg.url_prefix = '/material?item_type=FG'
        print(f"  âœ”ï¸  'purchase_fg' already exists â€” updated")

    # â”€â”€ 6. Purana standalone 'material' module deactivate karo â”€â”€â”€â”€â”€â”€â”€
    old_material = Module.query.filter_by(name='material').first()
    if old_material:
        old_material.is_active = False
        print(f"  ðŸ”• Deactivated old standalone 'material' module (id={old_material.id})")
    
    db.session.commit()

    print("\nðŸŽ‰ Done! Procurement hierarchy setup complete.")
    print("   Sidebar mein dikhega:")
    print("   PROCUREMENT")
    print("   â””â”€â”€ ðŸ›ï¸ Purchase")
    print("       â”œâ”€â”€ ðŸ§ª Raw Material     â†’ /material?item_type=RM")
    print("       â”œâ”€â”€ ðŸ“¦ Packing Material â†’ /material?item_type=PM")
    print("       â””â”€â”€ âœ… Finish Goods     â†’ /material?item_type=FG")
    print("\n   Note: Raw Material click karne par Item Type automatically")
    print("   'Raw Material' set ho jaayega â€” koi selection nahi hoga.")


