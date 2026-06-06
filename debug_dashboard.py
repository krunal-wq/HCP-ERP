# ═══════════════════════════════════════════════════════════════
#  DASHBOARD DEBUG SCRIPT
#  Kaise chalana hai (project root se):
#      cd D:\HCP-ERP
#      python debug_dashboard.py
#  Jo bhi output aaye pura copy karke bhej do.
# ═══════════════════════════════════════════════════════════════
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, date
from flask import Flask

app = Flask(__name__)
try:
    from core.config import Config
    app.config.from_object(Config)
    print('[1] Config loaded  ->', app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1])
except Exception as e:
    print('[1] CONFIG FAIL:', e); sys.exit(1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
try:
    from models.base import db
except Exception:
    from models import db
db.init_app(app)

from models.employee import Employee
from models.attendance import Attendance

# ── Check: naya route file laga hai ya nahi ──
try:
    rf = open(os.path.join('modules', 'hr', 'routes', 'attendance_routes.py'),
              encoding='utf-8-sig').read()
    if 'sel_date_str = request.args.get' in rf and "a = {" in rf:
        print('[2] attendance_routes.py  -> NAYA VERSION laga hai ✓')
    else:
        print('[2] attendance_routes.py  -> ⚠️ PURANA VERSION hai! File replace nahi hui.')
except Exception as e:
    print('[2] routes file read fail:', e)

SEL = date(2026, 5, 2)

with app.app_context():
    # ── Employees ──
    total_all = Employee.query.count()
    print(f'[3] employees table total rows           = {total_all}')

    by_status = db.session.query(Employee.status, db.func.count(Employee.id)) \
                          .group_by(Employee.status).all()
    print(f'[4] status wise breakup                  = {dict(by_status)}')

    by_del = db.session.query(Employee.is_deleted, db.func.count(Employee.id)) \
                       .group_by(Employee.is_deleted).all()
    print(f'[5] is_deleted wise breakup              = {dict(by_del)}')

    test_n = Employee.query.filter(Employee.employee_code.like('TEST-%')).count()
    print(f'[6] TEST- wale employees                 = {test_n}')

    # Exact dashboard filter
    dash_emps = Employee.query.filter(
        Employee.status == 'active',
        db.or_(Employee.is_deleted.is_(False), Employee.is_deleted.is_(None)),
    ).all()
    print(f'[7] DASHBOARD QUERY result (active+not-deleted) = {len(dash_emps)}')

    # ── Attendance on selected date ──
    att_rows = Attendance.query.filter_by(attendance_date=SEL).all()
    print(f'[8] attendance rows on {SEL}        = {len(att_rows)}')
    if att_rows:
        st = {}
        for r in att_rows:
            st[r.status] = st.get(r.status, 0) + 1
        print(f'    status breakup                       = {st}')
        print(f'    sample codes                         = {[r.employee_code for r in att_rows[:5]]}')

    # ── Join check: kitne dashboard-employees ko att row mili ──
    att_map = {r.employee_code: r for r in att_rows}
    matched = sum(1 for e in dash_emps
                  if att_map.get(e.employee_code) or att_map.get(e.employee_id))
    print(f'[9] dash-employees jinko att row mili    = {matched} / {len(dash_emps)}')
    if dash_emps[:3]:
        print(f'    sample emp codes                     = '
              f'{[(e.employee_code, e.status, e.is_deleted) for e in dash_emps[:3]]}')

    # ── Leave table exist check ──
    try:
        from models.hr_rules import HRLeaveApplication
        ln = HRLeaveApplication.query.count()
        print(f'[10] hr_leave_applications rows          = {ln}')
    except Exception as e:
        print(f'[10] ⚠️ hr_leave_applications FAIL: {type(e).__name__}: {str(e)[:120]}')
        print('     (Ye fail hua to dashboard route crash hota hai — isi wajah se data nahi aata)')

print('\nDone. Pura output copy karke bhejo.')
