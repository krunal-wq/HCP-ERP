"""
add_epd_module.py — create the standalone 'epd' permission module if missing.

EPD was split out of the shared 'npd' module so NPD and EPD permissions are
independent. The ACP panel's EPD section (prow('epd') + toggles) only renders
once this Module row exists. Idempotent & non-destructive (adds one row).

Run:  python scripts/fixes/add_epd_module.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import index  # sets up Flask app + db (does NOT start the server)
from models import db
from models.permission import Module

with index.app.app_context():
    existing = Module.query.filter_by(name='epd').first()
    if existing:
        print(f"epd module already exists (id={existing.id}) — nothing to do.")
    else:
        m = Module(name='epd', label='EPD', icon='EPD',
                   url_prefix='/npd/epd-projects', sort_order=16,
                   parent_id=None, is_active=True)
        db.session.add(m)
        db.session.commit()
        print(f"Created 'epd' module (id={m.id}). EPD permission toggle is now live in the ACP panel.")
