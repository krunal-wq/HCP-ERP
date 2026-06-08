# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
fix_milestones.py â€” Milestone templates aur existing project milestones fix karo
Run: python fix_milestones.py

Kya karta hai:
1. npd_milestone_templates table â€” extra milestones delete, sirf correct 8 rakhega
2. milestone_masters table â€” existing projects ke extra milestone rows deactivate karega
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

G = "\033[92m"; Y = "\033[93m"; R = "\033[91m"; B = "\033[1m"; E = "\033[0m"
def ok(m):   print(f"  {G}âœ… {m}{E}")
def warn(m): print(f"  {Y}âš ï¸  {m}{E}")
def err(m):  print(f"  {R}âŒ {m}{E}")

# â”€â”€ Load DB config â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
try:
    from config import Config
    import pymysql
    from urllib.parse import unquote_plus
    url = Config.SQLALCHEMY_DATABASE_URI
    m = re.match(r'mysql\+pymysql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', url)
    if not m:
        err("config.py mein DATABASE_URI sahi nahi hai")
        sys.exit(1)
    DB_USER, DB_PASS_ENC, DB_HOST, DB_PORT, DB_NAME = m.groups()
    DB_PASS = unquote_plus(DB_PASS_ENC)
    DB_PORT = int(DB_PORT or 3306)
except Exception as e:
    err(f"Config load failed: {e}")
    sys.exit(1)

con = pymysql.connect(
    host=DB_HOST, port=DB_PORT,
    user=DB_USER, password=DB_PASS,
    database=DB_NAME, charset='utf8mb4'
)
cur = con.cursor()

print(f"\n{'='*60}")
print(f"  {B}MILESTONE FIX SCRIPT{E}")
print(f"{'='*60}\n")

# â”€â”€ Correct 8 milestones â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CORRECT = [
    # (milestone_type,   title,                                icon,  sort)
    ('bom',              'BOM',                                'ðŸ“„',  1),
    ('ingredients',      'Ingredients List & Marketing Sheet', 'ðŸ“‹',  2),
    ('quotation',        'Quotation',                          'ðŸ’°',  3),
    ('packing_material', 'Packing Material',                   'ðŸ“¦',  4),
    ('artwork',          'Artwork / Design',                   'ðŸŽ¨',  5),
    ('artwork_qc',       'Artwork QC Approval',                'âœ…',  6),
    ('fda',              'FDA',                                'ðŸ›ï¸', 7),
    ('barcode',          'Barcode',                            'ðŸ”¢',  8),
]
CORRECT_TYPES = {r[0] for r in CORRECT}

# â”€â”€ STEP 1: Fix npd_milestone_templates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"  {B}STEP 1: npd_milestone_templates fix kar raha hai...{E}")
try:
    # Delete all extra types
    cur.execute("SELECT milestone_type, title FROM npd_milestone_templates ORDER BY sort_order")
    existing = cur.fetchall()
    print(f"  Current templates ({len(existing)}):")
    for mtype, title in existing:
        status = "âœ… KEEP" if mtype in CORRECT_TYPES else "âŒ DELETE"
        print(f"     {status} â€” {mtype}: {title}")

    # Delete extras
    extra_types = [mtype for mtype, _ in existing if mtype not in CORRECT_TYPES]
    if extra_types:
        placeholders = ','.join(['%s'] * len(extra_types))
        cur.execute(f"DELETE FROM npd_milestone_templates WHERE milestone_type IN ({placeholders})", extra_types)
        con.commit()
        ok(f"{len(extra_types)} extra templates deleted")
    else:
        ok("No extra templates found")

    # Insert missing correct ones
    for mtype, title, icon, sort in CORRECT:
        cur.execute("SELECT id FROM npd_milestone_templates WHERE milestone_type=%s", (mtype,))
        row = cur.fetchone()
        if row:
            # Update title, icon, sort_order, is_active
            cur.execute(
                "UPDATE npd_milestone_templates SET title=%s, icon=%s, sort_order=%s, is_active=1 WHERE milestone_type=%s",
                (title, icon, sort, mtype)
            )
            ok(f"Updated: {mtype} â€” {title}")
        else:
            cur.execute(
                "INSERT INTO npd_milestone_templates (milestone_type, title, icon, applies_to, default_selected, is_mandatory, sort_order, is_active, created_by) VALUES (%s,%s,%s,'both',1,0,%s,1,1)",
                (mtype, title, icon, sort)
            )
            ok(f"Inserted: {mtype} â€” {title}")
    con.commit()

except Exception as e:
    err(f"Step 1 failed: {e}")

# â”€â”€ STEP 2: Fix milestone_masters â€” deselect extra types â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
print(f"\n  {B}STEP 2: milestone_masters table â€” extra milestones deselect kar raha hai...{E}")
try:
    cur.execute("SHOW TABLES LIKE 'milestone_masters'")
    if not cur.fetchone():
        warn("milestone_masters table nahi mila â€” skip")
    else:
        placeholders = ','.join(['%s'] * len(CORRECT_TYPES))
        cur.execute(
            f"SELECT COUNT(*) FROM milestone_masters WHERE milestone_type NOT IN ({placeholders}) AND is_selected=1",
            list(CORRECT_TYPES)
        )
        count = cur.fetchone()[0]
        if count > 0:
            cur.execute(
                f"UPDATE milestone_masters SET is_selected=0 WHERE milestone_type NOT IN ({placeholders})",
                list(CORRECT_TYPES)
            )
            con.commit()
            ok(f"{count} extra milestone rows deselected from existing projects")
        else:
            ok("No extra selected milestones in projects")
except Exception as e:
    err(f"Step 2 failed: {e}")

cur.close()
con.close()

print(f"\n{'='*60}")
print(f"  {G}{B}âœ… FIX COMPLETE!{E}")
print(f"{'='*60}")
print(f"\n  Ab server restart karo: {B}python index.py{E}\n")


