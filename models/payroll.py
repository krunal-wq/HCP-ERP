"""
payroll.py — Salary processing models
Table: salary_slips — har employee ka monthly processed slip
"""
from datetime import datetime
from .base import db


class SalarySlip(db.Model):
    """Monthly processed salary slip — attendance-linked."""
    __tablename__ = 'salary_slips'

    id            = db.Column(db.Integer, primary_key=True)
    employee_id   = db.Column(db.Integer, db.ForeignKey('employees.id'),
                              nullable=False, index=True)
    year          = db.Column(db.Integer, nullable=False)
    month         = db.Column(db.Integer, nullable=False)

    # ── Attendance snapshot ──
    month_days    = db.Column(db.Integer, default=0)
    present_days  = db.Column(db.Numeric(5, 1), default=0)   # P + WOP
    half_days     = db.Column(db.Integer, default=0)
    absent_days   = db.Column(db.Integer, default=0)
    mispunch_days = db.Column(db.Integer, default=0)
    weekoff_days  = db.Column(db.Integer, default=0)
    holiday_days  = db.Column(db.Integer, default=0)
    leave_days    = db.Column(db.Numeric(5, 1), default=0)
    late_days     = db.Column(db.Integer, default=0)         # late aane ke din
    wop_days      = db.Column(db.Integer, default=0)          # week off par kaam
    hlp_days      = db.Column(db.Integer, default=0)          # holiday par kaam
    lop_days      = db.Column(db.Numeric(5, 1), default=0)   # Loss of Pay
    worked_days   = db.Column(db.Numeric(5, 1), default=0)   # payable days
    leave_taken_pl = db.Column(db.Numeric(4, 1), default=0)
    leave_taken_cl = db.Column(db.Numeric(4, 1), default=0)
    leave_taken_sl = db.Column(db.Numeric(4, 1), default=0)

    # ── Earnings (Actual / Earned) ──
    basic_actual     = db.Column(db.Numeric(12, 2), default=0)
    basic_earned     = db.Column(db.Numeric(12, 2), default=0)
    hra_actual       = db.Column(db.Numeric(12, 2), default=0)
    hra_earned       = db.Column(db.Numeric(12, 2), default=0)
    conv_actual      = db.Column(db.Numeric(12, 2), default=0)
    conv_earned      = db.Column(db.Numeric(12, 2), default=0)
    medical_actual   = db.Column(db.Numeric(12, 2), default=0)
    medical_earned   = db.Column(db.Numeric(12, 2), default=0)
    special_actual   = db.Column(db.Numeric(12, 2), default=0)
    special_earned   = db.Column(db.Numeric(12, 2), default=0)
    incentive_earned = db.Column(db.Numeric(12, 2), default=0)
    extra_earned     = db.Column(db.Numeric(12, 2), default=0)  # WOP+HLP extra day pay
    arrears_earned   = db.Column(db.Numeric(12, 2), default=0)
    total_actual     = db.Column(db.Numeric(12, 2), default=0)
    total_earned     = db.Column(db.Numeric(12, 2), default=0)

    # ── Deductions ──
    ded_pf      = db.Column(db.Numeric(12, 2), default=0)
    ded_esic    = db.Column(db.Numeric(12, 2), default=0)
    ded_pt      = db.Column(db.Numeric(12, 2), default=0)
    ded_tds     = db.Column(db.Numeric(12, 2), default=0)
    ded_advance = db.Column(db.Numeric(12, 2), default=0)
    ded_others  = db.Column(db.Numeric(12, 2), default=0)
    ded_lwf     = db.Column(db.Numeric(12, 2), default=0)
    ded_late    = db.Column(db.Numeric(12, 2), default=0)    # late coming penalty
    total_deductions = db.Column(db.Numeric(12, 2), default=0)

    net_pay     = db.Column(db.Numeric(12, 2), default=0)   # rounded

    status      = db.Column(db.String(20), default='processed')  # processed / paid
    remarks     = db.Column(db.String(255))
    created_by  = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.now)
    updated_at  = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    employee = db.relationship('Employee', lazy='joined')

    __table_args__ = (db.UniqueConstraint('employee_id', 'year', 'month',
                                          name='uq_slip_emp_month'),)

    def __repr__(self):
        return f'<SalarySlip emp={self.employee_id} {self.month}/{self.year} net={self.net_pay}>'
