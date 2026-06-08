# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
diagnose_item_type_access.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Check karta hai ki user ko Item Types kyu nahi dikh rahe:
1. Material Types table me data hai ya nahi (active count)
2. Sab users ke roles list karta hai (case + whitespace check)
3. Permission table me 'material' module ke sub_perms dikhata hai

Run: python diagnose_item_type_access.py
"""
from index import app
from models import db
from sqlalchemy import text

with app.app_context():
    print("=" * 70)
    print("ðŸ” ITEM TYPE ACCESS DIAGNOSIS")
    print("=" * 70)

    # â”€â”€ 1. material_types table check â”€â”€
    print("\nðŸ“¦ Material Types in DB:")
    try:
        rows = db.session.execute(text(
            "SELECT id, type_name, abbreviation, is_active, "
            "COALESCE(is_deleted,0) AS del FROM material_types ORDER BY sort_order, id"
        )).fetchall()
        if not rows:
            print("  âŒ EMPTY! material_types me ek bhi row nahi hai.")
            print("     Fix: python migrate.py (ya manually seed karo)")
        else:
            print(f"  Total: {len(rows)} types\n")
            print(f"  {'ID':<4} {'Name':<20} {'Abbr':<6} {'Active':<8} {'Deleted':<8}")
            print("  " + "-" * 50)
            active_count = 0
            for r in rows:
                act = 'âœ…' if r[3] else 'âŒ'
                deleted = 'ðŸ—‘ï¸' if r[4] else 'â€”'
                if r[3] and not r[4]:
                    active_count += 1
                print(f"  {r[0]:<4} {r[1]:<20} {r[2] or '':<6} {act:<8} {deleted:<8}")
            print(f"\n  Visible (active + not deleted): {active_count}")
            if active_count == 0:
                print("  âŒ Sab types inactive/deleted hain. Admin panel se activate karo.")
    except Exception as e:
        print(f"  âš ï¸  Error: {e}")

    # â”€â”€ 2. User roles check â”€â”€
    print("\nðŸ‘¤ All Users & Roles:")
    try:
        users = db.session.execute(text(
            "SELECT id, username, role, is_active FROM users ORDER BY id"
        )).fetchall()
        print(f"  {'ID':<4} {'Username':<25} {'Role (raw)':<25} {'Active':<8}")
        print("  " + "-" * 65)
        for u in users:
            role_repr = repr(u[2])    # repr dikhata hai whitespace / case clearly
            act = 'âœ…' if u[3] else 'âŒ'
            flag = ''
            r_clean = (u[2] or '').strip().lower()
            if r_clean == 'admin' and u[2] != 'admin':
                flag = '  âš ï¸  CASE/WHITESPACE ISSUE!'
            print(f"  {u[0]:<4} {u[1]:<25} {role_repr:<25} {act:<8}{flag}")
    except Exception as e:
        print(f"  âš ï¸  Error: {e}")

    # â”€â”€ 3. Permissions check â”€â”€
    print("\nðŸ” 'material' module permissions:")
    try:
        perms = db.session.execute(text(
            "SELECT user_id, can_view, can_add, can_edit, can_delete, sub_perms "
            "FROM permissions WHERE module='material'"
        )).fetchall()
        if not perms:
            print("  (No rows for module='material')")
        else:
            for p in perms:
                print(f"  user_id={p[0]}  view={p[1]} add={p[2]} edit={p[3]} delete={p[4]}")
                if p[5]:
                    print(f"     sub_perms = {p[5]}")
    except Exception as e:
        print(f"  âš ï¸  Error: {e}")

    print("\n" + "=" * 70)
    print("ðŸ’¡ NEXT STEPS:")
    print("  - Agar material_types EMPTY hai â†’ migrate.py run karo")
    print("  - Agar role 'admin' nahi hai (e.g. 'Admin', ' admin') â†’ updated material_routes.py")
    print("    me _allowed_types ab case-insensitive hai, ya DB me role fix karo:")
    print("    UPDATE users SET role='admin' WHERE id=<your_id>;")
    print("  - Agar role kuch aur hai (e.g. 'user') â†’ admin se login karke")
    print("    Permissions panel me jaake type_rm/pm/fg sub-perms ON karo")
    print("=" * 70)


