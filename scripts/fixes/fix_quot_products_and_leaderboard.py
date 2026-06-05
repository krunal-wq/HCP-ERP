# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
fix_quot_products_and_leaderboard.py
=====================================
Adds the two CRM modules that show as "âš ï¸ Module DB mein nahi hai" on the
permissions panel:

    â€¢ crm_quot_products  â†’ "Quot. Product List"
    â€¢ crm_leaderboard    â†’ "Leaderboard"

These two modules use a SINGLE on/off toggle (just `can_view`) â€” there are
no sub-permissions and no Add/Edit/Delete grid for them. Admin toggles
ON  â†’ user sees the menu item.
Admin toggles OFF â†’ menu item is hidden.

What this script does
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
1. Inserts the two Module rows (parent = 'crm') if missing.
2. Inserts default RolePermission rows for every role we know about.
   admin â†’ can_view=True ; everyone else â†’ can_view=False
   (matches the existing fix_missing_modules.py defaults but tightens
   non-admin roles to start hidden, so the permissions panel can drive
   visibility per-user).
3. Seeds UserPermission rows:
     â€¢ Admin users â†’ can_view=True   (so the module is visible day-one)
     â€¢ Non-admin users â†’ can_view=False  (so the toggle exists and admin
       can flip it ON per-user from the ACP panel â€” without the row,
       get_perm() returns no-access AND the toggle has no record to flip)

Idempotent: every step checks for existing rows and skips them. Safe to
re-run any number of times.

Usage
â”€â”€â”€â”€â”€
    python fix_quot_products_and_leaderboard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# â”€â”€â”€ Tiny ANSI helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[94m"; E = "\033[0m"
def ok(m):   print(f"  {G}âœ… {m}{E}")
def warn(m): print(f"  {Y}âš ï¸  {m}{E}")
def err(m):  print(f"  {R}âŒ {m}{E}")
def info(m): print(f"  {B}â„¹ï¸  {m}{E}")

# â”€â”€â”€ Imports â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from index import app
from models.base import db
from models.permission import Module, RolePermission, UserPermission
from models.user import User

# â”€â”€â”€ Modules to seed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
TARGET_MODULES = [
    {
        'name':       'crm_quot_products',
        'label':      'Quot. Product List',
        'icon':       'ðŸ“‹',
        'url_prefix': '/crm/quotations/products',
        'sort_order': 7,
    },
    {
        'name':       'crm_leaderboard',
        'label':      'Leaderboard',
        'icon':       'ðŸ†',
        'url_prefix': '/crm/leaderboard',
        'sort_order': 8,
    },
]

# Roles we set defaults for. admin â†’ ON, baaki sab â†’ OFF (admin enables
# from ACP panel per-user as needed).
ROLE_DEFAULTS = {
    'admin':   True,
    'manager': False,
    'sales':   False,
    'user':    False,
    'hr':      False,
    'viewer':  False,
}

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def seed_modules():
    """Step 1: ensure the two Module rows exist under parent 'crm'."""
    crm = Module.query.filter_by(name='crm').first()
    if not crm:
        err("Parent module 'crm' DB mein nahi mila â€” pehle migrate.py run karo.")
        sys.exit(1)

    seeded = []
    for cfg in TARGET_MODULES:
        existing = Module.query.filter_by(name=cfg['name']).first()
        if existing:
            warn(f"Module '{cfg['name']}' already exists (id={existing.id}) â€” skip")
            seeded.append(existing)
            continue

        mod = Module(
            name       = cfg['name'],
            label      = cfg['label'],
            icon       = cfg['icon'],
            url_prefix = cfg['url_prefix'],
            sort_order = cfg['sort_order'],
            parent_id  = crm.id,
            is_active  = True,
        )
        db.session.add(mod)
        db.session.flush()
        seeded.append(mod)
        ok(f"Module added â†’ '{cfg['name']}' (id={mod.id}, label='{cfg['label']}')")

    db.session.commit()
    return seeded


def seed_role_perms(modules):
    """Step 2: default role-level permissions. View-only toggle â€” no
    Add/Edit/Delete/Export/Import for these modules."""
    print()
    info("Setting default RolePermissions (admin=ON, others=OFF)...")
    for mod in modules:
        for role, default_view in ROLE_DEFAULTS.items():
            existing = RolePermission.query.filter_by(
                role=role, module_id=mod.id
            ).first()
            if existing:
                continue
            rp = RolePermission(
                role       = role,
                module_id  = mod.id,
                can_view   = default_view,
                can_add    = False,
                can_edit   = False,
                can_delete = False,
                can_export = False,
                can_import = False,
            )
            db.session.add(rp)
        ok(f"RolePermissions seeded for '{mod.name}'")
    db.session.commit()


def seed_user_perms(modules):
    """Step 3: per-user rows.

    For each user that already exists in the system we add a
    UserPermission row for these modules â€” because get_perm() falls back
    to "no access" when no UserPermission row is present (non-admin).
    Without a row, the ACP toggle has nothing to flip, so admin can't
    enable visibility per-user. With a row pre-seeded, the toggle works
    as expected.

      â€¢ Admin users  â†’ can_view=True  (visible immediately)
      â€¢ Non-admin    â†’ can_view=False (admin enables per-user via panel)
    """
    print()
    info("Seeding UserPermission rows...")
    users = User.query.all()
    for user in users:
        is_admin = (user.role == 'admin')
        default_view = is_admin
        for mod in modules:
            existing = UserPermission.query.filter_by(
                user_id=user.id, module_id=mod.id
            ).first()
            if existing:
                continue
            up = UserPermission(
                user_id    = user.id,
                module_id  = mod.id,
                can_view   = default_view,
                can_add    = False,
                can_edit   = False,
                can_delete = False,
                can_export = False,
                can_import = False,
            )
            # No sub-permissions for these modules â€” single toggle only.
            up.set_sub_permissions({})
            db.session.add(up)
        marker = "ON " if is_admin else "OFF"
        ok(f"User '{user.username}' (role={user.role}) â†’ can_view={marker}")
    db.session.commit()


def verify(modules):
    print()
    print(f"  {G}=== Final Verification ==={E}")
    for cfg in TARGET_MODULES:
        mod = Module.query.filter_by(name=cfg['name']).first()
        if not mod:
            err(f"'{cfg['name']}' â€” NOT FOUND in DB!")
            continue
        rp_total  = RolePermission.query.filter_by(module_id=mod.id).count()
        up_total  = UserPermission.query.filter_by(module_id=mod.id).count()
        up_on     = UserPermission.query.filter_by(
                        module_id=mod.id, can_view=True
                    ).count()
        ok(f"'{mod.name}' id={mod.id} | role-perms={rp_total} | user-perms={up_total} (ON={up_on})")


def main():
    with app.app_context():
        print(f"\n{B}â”â”â” Seeding Quot. Product List + Leaderboard â”â”â”{E}\n")
        modules = seed_modules()
        seed_role_perms(modules)
        seed_user_perms(modules)
        verify(modules)

    print()
    print(f"{G}  âœ… Done.{E}")
    print(f"{G}     â€¢ Permissions panel par toggle ab dikhega (warning gone).{E}")
    print(f"{G}     â€¢ Admin users â†’ menu mein turant visible.{E}")
    print(f"{G}     â€¢ Non-admin users â†’ toggle OFF default â€” admin selectively ON kar sakta hai.{E}")
    print(f"{G}     â€¢ Re-run safe (idempotent).{E}\n")


if __name__ == '__main__':
    main()


