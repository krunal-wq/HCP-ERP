# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
reset_quot_template.py
Run: python reset_quot_template.py
Quotation email template DB se delete karta hai â€” 
next mail send par fresh template auto-create hogi.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from index import app
from models import db, EmailTemplate

with app.app_context():
    t = EmailTemplate.query.filter_by(code='quotation').first()
    if t:
        db.session.delete(t)
        db.session.commit()
        print("âœ… Quotation template deleted â€” fresh template will be created on next mail send")
    else:
        print("â„¹ï¸ No quotation template found in DB")


