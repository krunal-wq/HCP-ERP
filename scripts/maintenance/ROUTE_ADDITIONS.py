# --- path bootstrap (added during restructure): run this script from project root ---
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
# -------------------------------------------------------------------------------------
"""
HOW TO ADD wa_share PAGE ROUTE â€” append to npd_daily_report_routes.py
or npd_whatsapp_routes.py

Add this route anywhere in npd_daily_report_routes.py:
"""

# â”€â”€ Add this route to npd_daily_report_routes.py â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# @npd_report_bp.route('/wa-share')
# @login_required
# def wa_share_page():
#     return render_template('npd/daily_report/wa_share.html',
#                            _pg='npd_wa_share', _mod='npd')


# â”€â”€ Add to base.html NPD sidebar section â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
"""
<a class="nav-a {% if _pg == 'npd_wa_share' %}active{% endif %}"
   href="/npd/wa-share">
    <span class="nav-ic">ðŸ“±</span>
    <span class="nav-txt">WA Report Share</span>
</a>
"""


# â”€â”€ Or add a button in existing dashboard.html â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
"""
Existing dashboard ke header mein yeh button add karo:

<a href="/npd/wa-share"
   class="btn-wa"
   style="display:inline-flex;align-items:center;gap:.45rem;
          background:#25d366;color:#fff;border-radius:8px;
          padding:.45rem .95rem;font-size:.8rem;font-weight:700;
          text-decoration:none;">
  ðŸ“‹ Detail Report Share
</a>
"""

# â”€â”€ Import npd_wa_web_report.py in index.py â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
"""
Add to index.py (after npd_daily_report_routes import):

import routes.npd_wa_web_report   # registers /npd/api/wa-detail-report on npd_report_bp
"""


