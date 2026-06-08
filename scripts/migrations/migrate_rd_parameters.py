# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
Migration: Add RDTestParameter table for Test Parameter Master
Run: python migrate_rd_parameters.py
"""

from app import app, db  # adjust import as per your project structure

# â”€â”€ Model Definition â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from datetime import datetime

class RDTestParameter(db.Model):
    __tablename__ = 'rd_test_parameters'

    id           = Column(Integer, primary_key=True)
    name         = Column(String(120), nullable=False)          # e.g. "Appearance"
    default_val  = Column(String(200), default='')              # default result value
    unit         = Column(String(50),  default='')              # e.g. "cP", "mPaÂ·s"
    sort_order   = Column(Integer,     default=0)               # display order
    is_active    = Column(Boolean,     default=True)            # soft-disable
    created_at   = Column(DateTime,    default=datetime.utcnow)
    updated_at   = Column(DateTime,    default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id':          self.id,
            'name':        self.name,
            'default_val': self.default_val or '',
            'unit':        self.unit or '',
            'sort_order':  self.sort_order,
            'is_active':   self.is_active,
        }

# â”€â”€ Default seed data â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
DEFAULT_PARAMETERS = [
    {'name': 'Appearance',    'default_val': '',               'unit': '',      'sort_order': 1},
    {'name': 'Color',         'default_val': '',               'unit': '',      'sort_order': 2},
    {'name': 'Odour',         'default_val': '',               'unit': '',      'sort_order': 3},
    {'name': 'Transparency',  'default_val': '',               'unit': '',      'sort_order': 4},
    {'name': 'pH',            'default_val': '',               'unit': '',      'sort_order': 5},
    {'name': 'Viscosity',     'default_val': '',               'unit': 'cP',    'sort_order': 6},
    {'name': 'Spindle No.',   'default_val': '',               'unit': '',      'sort_order': 7},
    {'name': 'RPM',           'default_val': '',               'unit': 'rpm',   'sort_order': 8},
]

# â”€â”€ Migration runner â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def run_migration():
    with app.app_context():
        # 1. Create table if not exists
        db.create_all()
        print("âœ… Table 'rd_test_parameters' created (or already exists)")

        # 2. Seed default parameters only if table is empty
        existing = RDTestParameter.query.count()
        if existing == 0:
            for p in DEFAULT_PARAMETERS:
                db.session.add(RDTestParameter(**p))
            db.session.commit()
            print(f"âœ… Seeded {len(DEFAULT_PARAMETERS)} default parameters")
        else:
            print(f"â„¹ï¸  Table already has {existing} parameters â€” skipping seed")

        # 3. Show current state
        params = RDTestParameter.query.order_by(RDTestParameter.sort_order).all()
        print("\nðŸ“‹ Current Parameters:")
        for p in params:
            status = "âœ…" if p.is_active else "âŒ"
            print(f"  {status} [{p.sort_order}] {p.name:<20} unit={p.unit or 'â€”':<8} default={p.default_val or 'â€”'}")

if __name__ == '__main__':
    run_migration()


