"""
loan_routes.py - Employee Loan / Advance module (zero-interest EMI).

  GET  /hr/loans                -> list (har loan ka paid/remaining) + add form
  POST /hr/loans/add            -> naya loan
  GET  /hr/loans/<id>           -> detail (full EMI schedule)
  POST /hr/loans/close/<id>     -> loan band karo (status=closed)
  POST /hr/loans/delete/<id>    -> delete

Har mahine ka EMI salary slip ke 'Loan EMI' deduction me aata hai
(salary_routes me wired). paid/remaining EMI schedule se compute hote hai.
"""
import calendar
from datetime import datetime, date

from flask import (Blueprint, render_template, request, redirect, url_for, flash)
from flask_login import login_required, current_user

from models import db, Employee
from models.hr_finance import EmployeeLoan
from models.payroll import SalarySlip

loan_bp = Blueprint('loan', __name__)


def _role_ok():
    return current_user.is_authenticated and \
           (current_user.role or '').lower() in ('admin', 'hr', 'manager')


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def _processed_months(employee_id):
    """Jin mahino ki salary process ho chuki hai (SalarySlip bani hai), sorted."""
    rows = SalarySlip.query.filter_by(employee_id=employee_id) \
                           .with_entities(SalarySlip.year, SalarySlip.month).all()
    return sorted({(int(r[0]), int(r[1])) for r in rows})


def _loan_progress(loan, processed_months, upto=None):
    """Sirf PROCESSED mahino me EMI count karo (start se, chronological).
    upto=(y,m) ho to us mahine tak hi (slip ke liye).
    Returns (paid, remaining, paid_by_month)."""
    principal = _f(loan.principal)
    emi = _f(loan.emi_amount)
    remaining = principal
    pbm = {}
    if (loan.status or '') == 'closed':
        return principal, 0.0, pbm
    if emi <= 0:
        return 0.0, remaining, pbm
    start = (loan.start_year, loan.start_month)
    for ym in processed_months:
        if ym < start:
            continue
        if upto is not None and ym > upto:
            break
        if remaining <= 0:
            break
        pay = round(min(emi, remaining), 2)
        pbm[ym] = pay
        remaining = round(remaining - pay, 2)
    paid = round(principal - remaining, 2)
    return paid, remaining, pbm


@loan_bp.route('/hr/loans')
@login_required
def loan_screen():
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')

    today = date.today()
    q = (request.args.get('q') or '').strip().lower()

    loans = EmployeeLoan.query.order_by(EmployeeLoan.status.asc(),
                                        EmployeeLoan.id.desc()).all()
    if q:
        loans = [l for l in loans
                 if l.employee and (q in (l.employee.full_name or '').lower()
                                    or q in (l.employee.employee_code or '').lower())]

    rows = []
    for l in loans:
        pm = _processed_months(l.employee_id)
        paid, remaining, _ = _loan_progress(l, pm)
        rows.append(dict(
            loan=l,
            paid=paid,
            remaining=remaining,
            total_months=l.total_months,
            paid_months=sum(1 for ym in pm if ym >= (l.start_year, l.start_month)),
            start_label=f'{calendar.month_abbr[l.start_month]} {l.start_year}',
        ))

    employees = [e for e in Employee.query.filter_by(status='active')
                                          .order_by(Employee.first_name).all()
                 if 'CONTRACTOR' not in (e.employee_type or '').upper()
                 and not getattr(e, 'is_contractor', False)
                 and (e.employee_code or e.employee_id or '').upper() != 'ADMIN']

    return render_template(
        'hr/loans/index.html',
        rows=rows, employees=employees,
        today=today.isoformat(),
        cur_year=today.year, cur_month=today.month,
        years=list(range(today.year - 1, today.year + 3)),
        months=[(i, calendar.month_name[i]) for i in range(1, 13)],
        active_page='hr_loans',
    )


@loan_bp.route('/hr/loans/add', methods=['POST'])
@login_required
def loan_add():
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')

    emp_id    = request.form.get('employee_id', type=int)
    ldate     = (request.form.get('loan_date') or '').strip()
    principal = _f(request.form.get('principal'))
    emi       = _f(request.form.get('emi_amount'))
    sy        = request.form.get('start_year', type=int)
    sm        = request.form.get('start_month', type=int)
    reason    = (request.form.get('reason') or '').strip()

    if not emp_id or not ldate or principal <= 0 or emi <= 0 or not sy or not sm:
        flash('Employee, loan date, principal, EMI aur start month zaroori hai.', 'warning')
        return redirect(url_for('loan.loan_screen'))
    if emi > principal:
        flash('EMI principal se zyada nahi ho sakta.', 'warning')
        return redirect(url_for('loan.loan_screen'))

    emp = Employee.query.get(emp_id)
    if emp is None:
        flash('Employee nahi mila.', 'warning')
        return redirect(url_for('loan.loan_screen'))
    if 'CONTRACTOR' in (emp.employee_type or '').upper() or getattr(emp, 'is_contractor', False):
        flash('Contractor employee ke liye loan allowed nahi hai.', 'warning')
        return redirect(url_for('loan.loan_screen'))

    d = datetime.strptime(ldate, '%Y-%m-%d').date()
    db.session.add(EmployeeLoan(
        employee_id=emp_id, loan_date=d, principal=principal, emi_amount=emi,
        start_year=sy, start_month=sm, reason=reason, status='active',
        created_by=getattr(current_user, 'id', None),
    ))
    db.session.commit()
    flash('Loan add ho gaya.', 'success')
    return redirect(url_for('loan.loan_screen'))


@loan_bp.route('/hr/loans/<int:lid>')
@login_required
def loan_detail(lid):
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    loan = EmployeeLoan.query.get_or_404(lid)
    today = date.today()

    pm = _processed_months(loan.employee_id)
    paid_total, remaining_total, pbm = _loan_progress(loan, pm)
    emi = _f(loan.emi_amount)
    principal = _f(loan.principal)

    schedule = []
    cum = 0.0
    # ---- PAID: jin processed mahino me EMI cut hua ----
    for ym in sorted(pbm.keys()):
        cum = round(cum + pbm[ym], 2)
        schedule.append(dict(
            label=f'{calendar.month_abbr[ym[1]]} {ym[0]}',
            emi=pbm[ym], paid_cum=cum,
            remaining=round(principal - cum, 2), done=True,
        ))
    # ---- PENDING: aage ka estimate ----
    if loan.status != 'closed' and emi > 0:
        rem = round(principal - cum, 2)
        if pbm:
            ly, lm = max(pbm.keys())
            ny, nm = (ly, lm + 1) if lm < 12 else (ly + 1, 1)
        else:
            ny, nm = loan.start_year, loan.start_month
        guard = 0
        while rem > 0 and guard < 120:
            pay = round(min(emi, rem), 2)
            cum = round(cum + pay, 2)
            rem = round(rem - pay, 2)
            schedule.append(dict(
                label=f'{calendar.month_abbr[nm]} {ny}',
                emi=pay, paid_cum=cum, remaining=rem, done=False,
            ))
            nm += 1
            if nm > 12:
                nm = 1; ny += 1
            guard += 1

    return render_template(
        'hr/loans/detail.html',
        loan=loan, schedule=schedule,
        paid_now=paid_total, remaining_now=remaining_total,
        active_page='hr_loans',
    )


@loan_bp.route('/hr/loans/close/<int:lid>', methods=['POST'])
@login_required
def loan_close(lid):
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    loan = EmployeeLoan.query.get_or_404(lid)
    loan.status = 'closed'
    db.session.commit()
    flash('Loan closed.', 'success')
    return redirect(url_for('loan.loan_screen'))


@loan_bp.route('/hr/loans/delete/<int:lid>', methods=['POST'])
@login_required
def loan_delete(lid):
    if not _role_ok():
        flash('Access denied.', 'error')
        return redirect('/')
    loan = EmployeeLoan.query.get_or_404(lid)
    db.session.delete(loan)
    db.session.commit()
    flash('Loan delete ho gaya.', 'success')
    return redirect(url_for('loan.loan_screen'))


# ---- Helper for salary slip: ek employee ka is mahine ka total EMI ----
def loan_emi_for(employee_id, year, month):
    loans = EmployeeLoan.query.filter_by(employee_id=employee_id,
                                         status='active').all()
    if not loans:
        return 0.0
    pm = _processed_months(employee_id)
    if (year, month) not in pm:
        pm = sorted(set(pm) | {(year, month)})   # is slip ka mahina include
    total = 0.0
    for l in loans:
        _, _, pbm = _loan_progress(l, pm, upto=(year, month))
        total += pbm.get((year, month), 0.0)
    return round(total, 2)
