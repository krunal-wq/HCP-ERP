"""
challan_routes.py - Employee Challan (fine) module.

  GET  /hr/challan                 -> list (month filter) + add form
  POST /hr/challan/add             -> naya challan
  POST /hr/challan/delete/<id>     -> delete

Month-end pe employee ke saare challan ka total salary slip ke
'Other Deduction' me automatically add ho jata hai (salary_routes me wired).
"""
import calendar
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect, url_for, flash)
from flask_login import login_required, current_user

from models import db, Employee
from models.hr_finance import EmployeeChallan

challan_bp = Blueprint('challan', __name__)


def _role_ok():
    return current_user.is_authenticated and \
           (current_user.role or '').lower() in ('admin', 'hr', 'manager')


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


@challan_bp.route('/hr/challan')
@login_required
def challan_screen():
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')

    today = date.today()
    year  = int(request.args.get('year')  or today.year)
    month = int(request.args.get('month') or today.month)
    q     = (request.args.get('q') or '').strip()

    days = calendar.monthrange(year, month)[1]
    m_start = date(year, month, 1)
    m_end   = date(year, month, days)

    rows_q = EmployeeChallan.query.filter(
        EmployeeChallan.challan_date >= m_start,
        EmployeeChallan.challan_date <= m_end,
    )
    challans = rows_q.order_by(EmployeeChallan.challan_date.desc(),
                               EmployeeChallan.id.desc()).all()
    if q:
        ql = q.lower()
        challans = [c for c in challans
                    if c.employee and (ql in (c.employee.full_name or '').lower()
                                       or ql in (c.employee.employee_code or '').lower())]

    total = round(sum(_f(c.amount) for c in challans), 2)

    employees = Employee.query.filter_by(status='active') \
                              .order_by(Employee.first_name).all()

    return render_template(
        'hr/challan/index.html',
        challans=challans, total=total, employees=employees,
        year=year, month=month, q=q,
        month_name=calendar.month_name[month],
        today=today.isoformat(),
        years=list(range(today.year - 2, today.year + 2)),
        months=[(i, calendar.month_name[i]) for i in range(1, 13)],
        active_page='hr_challan',
    )


@challan_bp.route('/hr/challan/add', methods=['POST'])
@login_required
def challan_add():
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')

    emp_id = request.form.get('employee_id', type=int)
    cdate  = request.form.get('challan_date', '').strip()
    amount = _f(request.form.get('amount'))
    reason = (request.form.get('reason') or '').strip()

    if not emp_id or not cdate or amount <= 0:
        flash('Employee, date aur valid amount zaroori hai.', 'warning')
        return redirect(url_for('challan.challan_screen'))

    d = datetime.strptime(cdate, '%Y-%m-%d').date()
    db.session.add(EmployeeChallan(
        employee_id=emp_id, challan_date=d, amount=amount, reason=reason,
        created_by=getattr(current_user, 'id', None),
    ))
    db.session.commit()
    flash('Challan add ho gaya.', 'success')
    return redirect(url_for('challan.challan_screen', year=d.year, month=d.month))


@challan_bp.route('/hr/challan/delete/<int:cid>', methods=['POST'])
@login_required
def challan_delete(cid):
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    c = EmployeeChallan.query.get_or_404(cid)
    y, m = c.challan_date.year, c.challan_date.month
    db.session.delete(c)
    db.session.commit()
    flash('Challan delete ho gaya.', 'success')
    return redirect(url_for('challan.challan_screen', year=y, month=m))


# ---- Helper for salary slip: ek employee ka month challan total ----
def challan_total_for(employee_id, year, month):
    days = calendar.monthrange(year, month)[1]
    rows = EmployeeChallan.query.filter(
        EmployeeChallan.employee_id == employee_id,
        EmployeeChallan.challan_date >= date(year, month, 1),
        EmployeeChallan.challan_date <= date(year, month, days),
    ).all()
    return round(sum(_f(r.amount) for r in rows), 2)
