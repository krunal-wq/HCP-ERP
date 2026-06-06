"""
salary_routes.py — Salary Processing + Payslip PDF
Blueprint: salary_bp
  GET  /hr/salary                      → process screen (month-wise preview)
  POST /hr/salary/process              → calculate & save slips for the month
  GET  /hr/salary/slip/<emp>/<y>/<m>   → payslip PDF download (HCP format)

Calculation (attendance-linked):
  payable_days = month_days − LOP
  LOP = Absent + MIS-PUNCH (policy: salary_config key 'mp_treatment'
        = absent / half_day / present; default half_day)
  Earned = Actual × payable/month_days  (incentive full)
  Deductions = PF + ESIC + PT + TDS (employee master se)
"""
import calendar
from datetime import datetime, date
from decimal import Decimal
from io import BytesIO

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, send_file, abort)
from flask_login import login_required, current_user

from models import db, Employee
from models.payroll import SalarySlip
from models.employee import SalaryConfig
from models.hr_rules import HRLeaveApplication

salary_bp = Blueprint('salary', __name__)

COMPANY_NAME = 'HCP WELLNESS PRIVATE LIMITED'
COMPANY_ADDR = ('403, Maruti Elanza Vertex, Opp. GTPL House, B/h. Armeida,\n'
                'Sindhu Bhavan Road, Bodakdev, Ahmedabad - 380054 Gujarat, India')


# ─────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────
def _role_ok():
    return current_user.is_authenticated and \
           (current_user.role or '').lower() in ('admin', 'hr', 'manager')


def _mp_treatment():
    row = SalaryConfig.query.filter_by(key='mp_treatment').first()
    v = (row.value if row else 'half_day').strip().lower()
    return v if v in ('absent', 'half_day', 'present') else 'half_day'


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _month_leaves(year, month, month_start, month_end):
    """Employee-wise PL/CL/SL taken (month ke andar clipped days)."""
    apps = HRLeaveApplication.query.filter(
        HRLeaveApplication.status == 'approved',
        HRLeaveApplication.from_date <= month_end,
        HRLeaveApplication.to_date >= month_start,
    ).all()
    out = {}
    for l in apps:
        f = max(l.from_date, month_start)
        t = min(l.to_date, month_end)
        d = (t - f).days + 1
        if l.half_day and l.from_date == l.to_date:
            d = 0.5
        rec = out.setdefault(l.employee_id, {'PL': 0.0, 'CL': 0.0, 'SL': 0.0})
        rec[l.leave_type if l.leave_type in rec else 'PL'] += d
    return out


def _ensure_structure(emp):
    """Agar salary structure (basic etc.) missing hai lekin gross set hai,
    to ERP ka existing HCP auto-apply chala do."""
    if _f(emp.salary_basic) > 0 or _f(emp.salary_gross) <= 0:
        return False
    try:
        from modules.hr.routes.hr_routes import _apply_hcp_structure
        return bool(_apply_hcp_structure(emp))
    except Exception:
        return False


def _late_rules_map():
    from models.attendance import LateShiftRule
    return {r.employee_type: r for r in
            LateShiftRule.query.filter_by(is_active=True).all()}


def _late_info(rule, days):
    """Late days count + penalty (type ke slabs se).
    Returns (late_count, penalty_amount)."""
    if rule is None:
        return 0, 0.0
    band_end, r1, r2, r3 = '10:59', 120.0, 250.0, 250.0
    for s in rule.penalty_rules:
        if not s.is_active:
            continue
        if s.time_to:
            band_end = s.time_to
            if s.from_count <= 3 <= (s.to_count or 999):
                r1 = float(s.penalty_amount)
            if s.from_count >= 4:
                r2 = float(s.penalty_amount)
        else:
            r3 = float(s.penalty_amount)
    band_n = after_n = 0
    for dd in days:
        it = dd.get('in_t')
        if it and it > rule.late_after:
            if it <= band_end:
                band_n += 1
            else:
                after_n += 1
    penalty = min(band_n, 3) * r1 + max(band_n - 3, 0) * r2 + after_n * r3
    return band_n + after_n, round(penalty, 2)


def _compute_salary(emp, cnt, month_days, mp_treat, leaves, late=(0, 0.0)):
    """Ek employee ka pura calculation. cnt = monthly status counts."""
    _ensure_structure(emp)
    ab = cnt.get('AB', 0)
    mp = cnt.get('MP', 0)
    hd = cnt.get('HD', 0)
    if mp_treat == 'absent':
        mp_lop = mp
    elif mp_treat == 'present':
        mp_lop = 0
    else:
        mp_lop = mp * 0.5
    lop = ab + mp_lop + hd * 0.5
    lop = min(lop, month_days)
    payable = month_days - lop
    factor = (payable / month_days) if month_days else 0

    basic, hra  = _f(emp.salary_basic), _f(emp.salary_hra)
    conv        = _f(emp.salary_conveyance)
    medical     = _f(emp.salary_medical_allow)
    special     = _f(emp.salary_special_allow)
    incentive   = _f(emp.salary_incentive)

    e = lambda v: round(v * factor, 2)
    earned = dict(basic=e(basic), hra=e(hra), conv=e(conv),
                  medical=e(medical), special=e(special))
    total_actual = round(basic + hra + conv + medical + special, 2)

    # ── WOP / HLP = off-day par kaam → extra day ka paisa ──
    wop = cnt.get('WOP', 0)
    hlp = cnt.get('HLP', 0)
    per_day = (total_actual / month_days) if month_days else 0
    extra_pay = round(per_day * (wop + hlp), 2)

    total_earned = round(sum(earned.values()) + incentive + extra_pay, 2)

    pf   = _f(emp.salary_pf_employee)
    esic = _f(emp.salary_esic_employee)
    pt   = _f(emp.salary_professional_tax) if payable > 0 else 0
    tds  = _f(emp.salary_tds)
    late_n, late_pen = late
    if total_earned <= 0:
        # structure/gross hi nahi (jaise contractor) — penalty se negative mat banao
        late_pen = 0.0
    total_ded = round(pf + esic + pt + tds + late_pen, 2)
    net = round(total_earned - total_ded)

    lv = leaves.get(emp.id, {'PL': 0, 'CL': 0, 'SL': 0})
    return dict(
        month_days=month_days,
        present=cnt.get('P', 0), half=hd,
        absent=ab, mispunch=mp,
        weekoff=cnt.get('WO', 0), holiday=cnt.get('HOL', 0),
        leave=cnt.get('LV', 0), lop=round(lop, 1), payable=round(payable, 1),
        late_n=late_n, late_pen=late_pen,
        wop=wop, hlp=hlp, extra_pay=extra_pay,
        lv_pl=lv['PL'], lv_cl=lv['CL'], lv_sl=lv['SL'],
        basic=basic, hra=hra, conv=conv, medical=medical, special=special,
        earned=earned, incentive=incentive,
        total_actual=total_actual, total_earned=total_earned,
        pf=pf, esic=esic, pt=pt, tds=tds, late=late_pen,
        total_ded=total_ded, net=net,
    )


def _payroll_rows(emp_rows):
    """Salary list se Contractors aur Admin account hatao."""
    out = []
    for er in emp_rows:
        emp = er['emp']
        etype = (emp.employee_type or '').upper()
        code  = (emp.employee_code or emp.employee_id or '').upper()
        if 'CONTRACTOR' in etype:
            continue
        if getattr(emp, 'is_contractor', False):
            continue
        if code == 'ADMIN':
            continue
        out.append(er)
    return out


def _get_month_data(year, month, emp_type, search_q):
    """Attendance monthly builder reuse — same data, same logic."""
    from modules.hr.routes.attendance_routes import _build_monthly_data
    return _build_monthly_data(year, month, emp_type, search_q)


# ─────────────────────────────────────────────────────────────────
#  GET /hr/salary — Process screen
# ─────────────────────────────────────────────────────────────────
@salary_bp.route('/hr/salary')
@login_required
def salary_process_screen():
    if not _role_ok():
        flash('Access denied: Salary permission nahi hai.', 'error')
        return redirect('/')

    today = date.today()
    # default = pichla complete month
    d_y, d_m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    try:
        year  = int(request.args.get('year',  d_y))
        month = int(request.args.get('month', d_m))
    except ValueError:
        year, month = d_y, d_m
    if not (1 <= month <= 12):
        year, month = d_y, d_m
    emp_type = (request.args.get('emp_type') or '').strip()
    search_q = (request.args.get('q') or '').strip().lower()

    month_days  = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end   = date(year, month, month_days)
    mp_treat    = _mp_treatment()

    md     = _get_month_data(year, month, emp_type, search_q)
    leaves = _month_leaves(year, month, month_start, month_end)

    existing = {s.employee_id: s for s in SalarySlip.query.filter_by(
        year=year, month=month).all()}

    lrules = _late_rules_map()
    rows, mp_total = [], 0
    for er in _payroll_rows(md['emp_rows']):
        emp = er['emp']
        late = _late_info(lrules.get(emp.employee_type or ''), er['days'])
        calc = _compute_salary(emp, er['cnt'], month_days, mp_treat, leaves, late)
        mp_total += calc['mispunch']
        rows.append(dict(emp=emp, c=calc, slip=existing.get(emp.id)))

    return render_template('hr/salary/process.html',
        rows=rows, year=year, month=month,
        month_name=calendar.month_name[month],
        emp_types=[t for t in md['emp_types'] if 'CONTRACTOR' not in t.upper()],
        emp_type=emp_type, search_q=search_q,
        mp_total=mp_total, mp_treat=mp_treat,
        processed_count=len(existing),
        years=list(range(today.year - 2, today.year + 1)),
        active_page='hr_salary')


# ─────────────────────────────────────────────────────────────────
#  POST /hr/salary/process — calculate & save
# ─────────────────────────────────────────────────────────────────
@salary_bp.route('/hr/salary/process', methods=['POST'])
@login_required
def salary_process():
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    try:
        year  = int(request.form.get('year'))
        month = int(request.form.get('month'))
    except (TypeError, ValueError):
        flash('Invalid month.', 'error')
        return redirect(url_for('salary.salary_process_screen'))
    emp_type = (request.form.get('emp_type') or '').strip()
    search_q = (request.form.get('q') or '').strip().lower()

    month_days  = calendar.monthrange(year, month)[1]
    month_start = date(year, month, 1)
    month_end   = date(year, month, month_days)
    mp_treat    = _mp_treatment()

    md     = _get_month_data(year, month, emp_type, search_q)
    leaves = _month_leaves(year, month, month_start, month_end)
    existing = {s.employee_id: s for s in SalarySlip.query.filter_by(
        year=year, month=month).all()}

    lrules = _late_rules_map()
    n_new = n_upd = 0
    for er in _payroll_rows(md['emp_rows']):
        emp = er['emp']
        late = _late_info(lrules.get(emp.employee_type or ''), er['days'])
        c = _compute_salary(emp, er['cnt'], month_days, mp_treat, leaves, late)
        slip = existing.get(emp.id)
        if slip is None:
            slip = SalarySlip(employee_id=emp.id, year=year, month=month,
                              created_by=current_user.id)
            db.session.add(slip)
            n_new += 1
        else:
            n_upd += 1
        slip.month_days    = month_days
        slip.present_days  = c['present'];  slip.half_days     = c['half']
        slip.absent_days   = c['absent'];   slip.mispunch_days = c['mispunch']
        slip.weekoff_days  = c['weekoff'];  slip.holiday_days  = c['holiday']
        slip.leave_days    = c['leave'];    slip.lop_days      = c['lop']
        slip.late_days     = c['late_n'];   slip.ded_late      = c['late_pen']
        slip.wop_days      = c['wop'];      slip.hlp_days      = c['hlp']
        slip.extra_earned  = c['extra_pay']
        slip.worked_days   = c['payable']
        slip.leave_taken_pl = c['lv_pl']; slip.leave_taken_cl = c['lv_cl']
        slip.leave_taken_sl = c['lv_sl']
        slip.basic_actual   = c['basic'];   slip.basic_earned   = c['earned']['basic']
        slip.hra_actual     = c['hra'];     slip.hra_earned     = c['earned']['hra']
        slip.conv_actual    = c['conv'];    slip.conv_earned    = c['earned']['conv']
        slip.medical_actual = c['medical']; slip.medical_earned = c['earned']['medical']
        slip.special_actual = c['special']; slip.special_earned = c['earned']['special']
        slip.incentive_earned = c['incentive']
        slip.total_actual   = c['total_actual']
        slip.total_earned   = c['total_earned']
        slip.ded_pf  = c['pf'];  slip.ded_esic = c['esic']
        slip.ded_pt  = c['pt'];  slip.ded_tds  = c['tds']
        slip.total_deductions = c['total_ded']
        slip.net_pay = c['net']
        slip.status  = 'processed'
        slip.updated_at = datetime.now()
    db.session.commit()
    flash(f'✅ Salary processed — {n_new} new, {n_upd} updated '
          f'({calendar.month_name[month]} {year})', 'success')
    return redirect(url_for('salary.salary_process_screen',
                            year=year, month=month, emp_type=emp_type, q=search_q))


# ─────────────────────────────────────────────────────────────────
#  Number → Indian words
# ─────────────────────────────────────────────────────────────────
_ONES = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight',
         'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen',
         'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
_TENS = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy',
         'Eighty', 'Ninety']


def _two(n):
    return _ONES[n] if n < 20 else (_TENS[n // 10] + (' ' + _ONES[n % 10] if n % 10 else ''))


def _three(n):
    s = ''
    if n >= 100:
        s = _ONES[n // 100] + ' Hundred'
        if n % 100: s += ' '
    return s + _two(n % 100) if n % 100 else s


def amount_in_words(n):
    n = int(round(n))
    if n == 0: return 'Zero Only'
    parts = []
    for div, name in ((10000000, 'Crore'), (100000, 'Lakh'), (1000, 'Thousand')):
        if n >= div:
            parts.append(_three(n // div) + ' ' + name)
            n %= div
    if n:
        parts.append(_three(n))
    return ' '.join(parts) + ' Only'


# ─────────────────────────────────────────────────────────────────
#  GET /hr/salary/slip/<emp_id>/<year>/<month> — Payslip PDF
# ─────────────────────────────────────────────────────────────────
@salary_bp.route('/hr/salary/slip/<int:emp_id>/<int:year>/<int:month>')
@login_required
def salary_slip_pdf(emp_id, year, month):
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    slip = SalarySlip.query.filter_by(employee_id=emp_id, year=year,
                                      month=month).first()
    if slip is None:
        flash('Slip abhi process nahi hui — pehle Process Salary karo.', 'warning')
        return redirect(url_for('salary.salary_process_screen',
                                year=year, month=month))
    emp = slip.employee or Employee.query.get_or_404(emp_id)

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                    Paragraph, Spacer)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER

    ORANGE = colors.HexColor('#F4B084')
    BLUE   = colors.HexColor('#1F4E79')

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    W = doc.width
    S = []

    st_co   = ParagraphStyle('co',  fontName='Helvetica-Bold', fontSize=11,
                             textColor=BLUE, alignment=TA_RIGHT)
    st_addr = ParagraphStyle('ad',  fontName='Helvetica-Bold', fontSize=7,
                             textColor=colors.HexColor('#C55A11'),
                             alignment=TA_RIGHT, leading=9)
    # ── Logo (static/images/icons/hcp-logo.png) — missing ho to text fallback ──
    import os
    from flask import current_app
    logo_path = os.path.join(current_app.root_path, 'static', 'images',
                             'icons', 'hcp-logo.png')
    logo_done = False
    if os.path.exists(logo_path):
        try:
            from reportlab.platypus import Image as RLImage
            from reportlab.lib.utils import ImageReader
            iw, ih = ImageReader(logo_path).getSize()
            h = 14 * mm
            w = h * iw / ih
            img = RLImage(logo_path, width=w, height=h)
            img.hAlign = 'RIGHT'
            S.append(img)
            S.append(Spacer(1, 2))
            logo_done = True
        except Exception:
            logo_done = False
    if not logo_done:
        st_logo = ParagraphStyle('lg', fontName='Helvetica-Bold', fontSize=24,
                                 textColor=BLUE, alignment=TA_RIGHT,
                                 leading=26, spaceAfter=4)
        S.append(Paragraph('hcp', st_logo))
    S.append(Paragraph(COMPANY_NAME, st_co))
    S.append(Paragraph(COMPANY_ADDR.replace('\n', '<br/>'), st_addr))
    S.append(Spacer(1, 4))

    mname = calendar.month_name[month]
    tt = Table([[f'Pay Slip for the Period of {mname} {year}']], colWidths=[W])
    tt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ORANGE),
        ('FONTNAME',   (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0, 0), (-1, -1), 10),
        ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
        ('BOX',        (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    S.append(tt)

    fmt = lambda v: f'{_f(v):,.2f}' if _f(v) else '-'
    doj = emp.date_of_joining.strftime('%d.%m.%Y') if emp.date_of_joining else '-'
    lv_bal = (f"PL - {_f(emp.paid_leave_balance):g}  "
              f"CL - {_f(emp.casual_leave_balance):g}  "
              f"SL - {_f(emp.sick_leave_balance):g}")
    lv_taken = (f"PL - {_f(slip.leave_taken_pl):g}  "
                f"CL - {_f(slip.leave_taken_cl):g}  "
                f"SL - {_f(slip.leave_taken_sl):g}")
    info = [
        ['Employee Name', ':', emp.full_name,            'Bank Name',     ':', emp.bank_name or '-'],
        ['Employee ID',   ':', emp.employee_id or emp.employee_code or '-',
                                                          'Account Number', ':', emp.bank_account_number or '-'],
        ['Date of Joining', ':', doj,                     'Branch Name',   ':', emp.bank_branch or '-'],
        ['Location',      ':', emp.location or '-',       'IFSC Code',     ':', emp.bank_ifsc or '-'],
        ['Department',    ':', emp.department or '-',     'Worked Days',   ':', f"{_f(slip.worked_days):g}"],
        ['Designation',   ':', emp.designation or '-',    'Loss of Pay',   ':', f"{_f(slip.lop_days):g}"],
        ['Leave Balance', ':', lv_bal,                    'Leave Taken',   ':', lv_taken],
    ]
    ti = Table(info, colWidths=[W*0.17, W*0.03, W*0.30, W*0.17, W*0.03, W*0.30])
    ti.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8.2),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('ALIGN',    (2, 0), (2, -1), 'CENTER'),
        ('ALIGN',    (5, 0), (5, -1), 'CENTER'),
        ('BOX',      (0, 0), (-1, -1), 1, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 2.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
    ]))
    S.append(ti)
    S.append(Spacer(1, 5))

    earn_rows = [
        ('Basic Pay',            slip.basic_actual,   slip.basic_earned),
        ('House Rent Allowance', slip.hra_actual,     slip.hra_earned),
        ('Conveyance Allowance', slip.conv_actual,    slip.conv_earned),
        ('Medical Allowance',    slip.medical_actual, slip.medical_earned),
        ('Special Allowance',    slip.special_actual, slip.special_earned),
        ('Other Incentive',      None,                slip.incentive_earned),
        ('Extra Days (WO/Holiday)', None,             getattr(slip, 'extra_earned', 0)),
        ('Arrears (If Any)',     None,                slip.arrears_earned),
    ]
    ded_rows = [
        ('PF (Employee)',    slip.ded_pf),
        ('ESIC (Employee)',  slip.ded_esic),
        ('Professional Tax', slip.ded_pt),
        ('TDS',              slip.ded_tds),
        ('Late Coming Penalty', getattr(slip, 'ded_late', 0)),
        ('Advance',          slip.ded_advance),
        ('Others',           slip.ded_others),
        ('LWF',              slip.ded_lwf),
    ]
    body = [['Earnings', 'Actual', 'Earned', 'Deductions', 'Amount']]
    for i in range(8):
        en, ea, ee = earn_rows[i]
        dn, da = ded_rows[i]
        body.append([en,
                     fmt(ea) if ea is not None else '',
                     fmt(ee) if ee is not None else '',
                     dn, fmt(da)])
    body.append(['Total Earnings', f'{_f(slip.total_actual):,.2f}',
                 f'{_f(slip.total_earned):,.2f}', 'Total Deductions',
                 f'{_f(slip.total_deductions):,.2f}'])
    te = Table(body, colWidths=[W*0.26, W*0.13, W*0.13, W*0.26, W*0.22])
    te.setStyle(TableStyle([
        ('FONTSIZE',  (0, 0), (-1, -1), 8.2),
        ('FONTNAME',  (0, 0), (-1, 0),  'Helvetica-Bold'),
        ('FONTNAME',  (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN',     (1, 0), (2, -1), 'RIGHT'),
        ('ALIGN',     (4, 0), (4, -1), 'RIGHT'),
        ('BOX',       (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0),  0.8, colors.black),
        ('LINEABOVE', (0, -1), (-1, -1), 0.8, colors.black),
        ('LINEAFTER', (2, 0), (2, -1), 0.8, colors.black),
        ('LINEAFTER', (0, 0), (0, -1), 0.4, colors.grey),
        ('LINEAFTER', (1, 0), (1, -1), 0.4, colors.grey),
        ('LINEAFTER', (3, 0), (3, -1), 0.4, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2.2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.2),
    ]))
    S.append(te)

    net = int(round(_f(slip.net_pay)))
    tn = Table([
        ['Net Pay (Rounded)', f'{net:,}'],
        [f'(in Words)  {amount_in_words(net)}', ''],
    ], colWidths=[W*0.70, W*0.30])
    tn.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.6),
        ('ALIGN',    (1, 0), (1, 0), 'RIGHT'),
        ('BOX',      (0, 0), (-1, -1), 1, colors.black),
        ('SPAN',     (0, 1), (1, 1)),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    S.append(tn)
    S.append(Spacer(1, 22))
    st_foot = ParagraphStyle('ft', fontName='Helvetica-BoldOblique',
                             fontSize=8, alignment=TA_CENTER)
    S.append(Paragraph(
        '** This is a system generated payslip does not require any signature and seal.**',
        st_foot))

    doc.build(S)
    buf.seek(0)
    fname = f"Payslip_{(emp.employee_code or emp.id)}_{mname}_{year}.pdf"
    return send_file(buf, as_attachment=True, download_name=fname,
                     mimetype='application/pdf')
