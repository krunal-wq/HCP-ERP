"""
hr_finance.py - Employee Challan (fine) + Loan/Advance models.

Tables:
  employee_challans - kisi din employee ko diya gaya challan/fine.
                      Month-end pe us mahine ke saare challan ka total
                      salary slip ke 'Other Deduction' me add hota hai.
  employee_loans    - employee loan/advance with monthly EMI (zero-interest).
                      Har mahine ka EMI salary slip ke 'Loan EMI' me deduct
                      hota hai. paid/remaining schedule se compute hota hai.
"""
from datetime import datetime
from .base import db


class EmployeeChallan(db.Model):
    """Ek din ka challan/fine - month-end Other Deduction me jud jata hai."""
    __tablename__ = 'employee_challans'

    id           = db.Column(db.Integer, primary_key=True)
    employee_id  = db.Column(db.Integer, db.ForeignKey('employees.id'),
                             nullable=False, index=True)
    challan_date = db.Column(db.Date, nullable=False, index=True)
    amount       = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    reason       = db.Column(db.String(255))
    created_by   = db.Column(db.Integer)
    created_at   = db.Column(db.DateTime, default=datetime.now)

    employee = db.relationship('Employee', lazy='joined')

    def __repr__(self):
        return f'<EmployeeChallan emp={self.employee_id} {self.challan_date} {self.amount}>'


class EmployeeLoan(db.Model):
    """Employee loan/advance. Zero-interest: principal monthly EMI me chukta.
    paid/remaining purely schedule (elapsed months) se compute hota hai."""
    __tablename__ = 'employee_loans'

    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'),
                            nullable=False, index=True)
    loan_date   = db.Column(db.Date, nullable=False)
    principal   = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    emi_amount  = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    start_year  = db.Column(db.Integer, nullable=False)   # EMI kis mahine se shuru
    start_month = db.Column(db.Integer, nullable=False)
    reason      = db.Column(db.String(255))
    status      = db.Column(db.String(20), default='active')   # active / closed
    created_by  = db.Column(db.Integer)
    created_at  = db.Column(db.DateTime, default=datetime.now)

    employee = db.relationship('Employee', lazy='joined')

    # ---- EMI schedule helpers (interest-free, principal / emi) ----
    def _idx(self, year, month):
        """start_month se (year,month) tak kitne EMI elapse hue. <0 => abhi shuru nahi."""
        return (year - self.start_year) * 12 + (month - self.start_month)

    def emi_for(self, year, month):
        """Is (year,month) ka EMI. Last installment chhota ho sakta hai.
        0 agar closed / schedule ke bahar / fully paid."""
        if (self.status or '') == 'closed':
            return 0.0
        emi = float(self.emi_amount or 0)
        if emi <= 0:
            return 0.0
        idx = self._idx(year, month)
        if idx < 0:
            return 0.0
        principal = float(self.principal or 0)
        paid_before = min(emi * idx, principal)
        remaining = round(principal - paid_before, 2)
        if remaining <= 0:
            return 0.0
        return round(min(emi, remaining), 2)

    def paid_upto(self, year, month):
        """(year,month) ke end tak total chukaya (us mahine sahit)."""
        if (self.status or '') == 'closed':
            return float(self.principal or 0)
        emi = float(self.emi_amount or 0)
        idx = self._idx(year, month)
        if emi <= 0 or idx < 0:
            return 0.0
        return round(min(emi * (idx + 1), float(self.principal or 0)), 2)

    def remaining_upto(self, year, month):
        """(year,month) ke end tak baaki amount."""
        return round(float(self.principal or 0) - self.paid_upto(year, month), 2)

    @property
    def total_months(self):
        """Approx kitne mahine lagenge (last partial bhi count)."""
        emi = float(self.emi_amount or 0)
        if emi <= 0:
            return 0
        import math
        return math.ceil(float(self.principal or 0) / emi)

    def __repr__(self):
        return f'<EmployeeLoan emp={self.employee_id} principal={self.principal} emi={self.emi_amount}>'
