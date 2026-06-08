# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
reset_all_milestone_status.py
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Saare projects me saare MilestoneMaster rows ka status reset karta hai
as clean slate. Useful jab legacy/test data ke pending status fields
galat set hain aur fresh start chahiye.

Kya reset hoga har row me:
  status        â†’ 'pending'
  approved_by   â†’ NULL
  approved_at   â†’ NULL
  completed_at  â†’ NULL
  reject_reason â†’ NULL
  target_date   â†’ NULL (optional â€” default ON; --keep-dates se preserve hoga)

Kya PRESERVE rahega:
  is_selected, title, milestone_type, sort_order
  notes, attachments (user-entered data)
  assigned_to
  MilestoneLog entries (audit trail)

Run:
    python reset_all_milestone_status.py                  # dry-run
    python reset_all_milestone_status.py --apply          # actually save
    python reset_all_milestone_status.py --apply --keep-dates
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from index import app, db
from models.npd import NPDProject, MilestoneMaster

APPLY      = '--apply'      in sys.argv
KEEP_DATES = '--keep-dates' in sys.argv


def main():
    with app.app_context():
        mode = "APPLY" if APPLY else "DRY-RUN"
        print(f"\n{'='*70}")
        print(f"  RESET ALL MILESTONE STATUS â†’ pending   [{mode}]")
        if KEEP_DATES:
            print(f"  (target_date preserve hoga)")
        print(f"{'='*70}\n")

        rows = MilestoneMaster.query.order_by(
            MilestoneMaster.project_id, MilestoneMaster.sort_order
        ).all()

        if not rows:
            print("   Koi milestone rows nahi mili.")
            return

        # Project code lookup for friendly output
        pids = {r.project_id for r in rows}
        projects = {p.id: p for p in NPDProject.query.filter(NPDProject.id.in_(pids)).all()}

        changed   = 0
        unchanged = 0
        per_project = {}

        for r in rows:
            needs_change = False
            changes = []

            if r.status and r.status != 'pending':
                changes.append(f"status='{r.status}'â†’'pending'")
                needs_change = True
            if r.approved_by is not None:
                changes.append("approved_byâ†’NULL")
                needs_change = True
            if r.approved_at is not None:
                changes.append("approved_atâ†’NULL")
                needs_change = True
            if r.completed_at is not None:
                changes.append("completed_atâ†’NULL")
                needs_change = True
            if r.reject_reason:
                changes.append("reject_reasonâ†’NULL")
                needs_change = True
            if not KEEP_DATES and r.target_date is not None:
                changes.append("target_dateâ†’NULL")
                needs_change = True

            if not needs_change:
                unchanged += 1
                continue

            pcode = projects.get(r.project_id)
            pcode = pcode.code if pcode else f'proj#{r.project_id}'
            print(f"  {pcode:<10} id={r.id:<4} {r.milestone_type:<22} â€” {', '.join(changes)}")

            if APPLY:
                r.status        = 'pending'
                r.approved_by   = None
                r.approved_at   = None
                r.completed_at  = None
                r.reject_reason = None
                if not KEEP_DATES:
                    r.target_date = None

            changed += 1
            per_project[r.project_id] = per_project.get(r.project_id, 0) + 1

        if APPLY:
            db.session.commit()

        print(f"\n{'='*70}")
        print(f"  SUMMARY")
        print(f"{'='*70}")
        print(f"  Total rows scanned:    {len(rows)}")
        print(f"  Rows to reset:         {changed}")
        print(f"  Already pending/clean: {unchanged}")
        if per_project:
            print(f"  Per-project breakdown:")
            for pid, cnt in sorted(per_project.items()):
                p = projects.get(pid)
                pcode = p.code if p else f'proj#{pid}'
                print(f"     {pcode:<10} â€” {cnt} row(s)")

        if APPLY:
            print(f"\n  âœ… Changes committed. App refresh karo.")
        else:
            print(f"\n  â„¹ï¸  Dry-run only. Re-run with --apply to save.")
        print()


if __name__ == '__main__':
    main()


