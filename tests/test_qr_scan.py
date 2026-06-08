from tests.test_base import BaseTestCase
from models import Employee, Attendance, RawPunchLog
from index import db
from datetime import datetime, timedelta, date

class TestQRScan(BaseTestCase):
    def test_qr_scan_page_loads(self):
        # The kiosk page should load without authentication
        response = self.client.get('/hr/attendance/qr-scan')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'QR Scanner', response.data)

    def test_qr_lookup_only(self):
        # Look up employee code, lookup_only=True
        # This should return employee details but NOT register a punch
        response = self.client.post('/hr/attendance/qr-lookup', data=dict(
            code='EMP001',
            lookup_only='true'
        ))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['employee']['code'], 'EMP001')
        self.assertEqual(data['employee']['name'], 'QA Test Tester')
        self.assertEqual(data['action'], None)
        
        # Verify no punches were created in DB
        self.assertEqual(RawPunchLog.query.count(), 0)
        self.assertEqual(Attendance.query.count(), 0)

    def test_qr_lookup_nonexistent_employee(self):
        response = self.client.post('/hr/attendance/qr-lookup', data=dict(
            code='NONEXISTENT'
        ))
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['success'])
        self.assertIn('Employee nahi mila', data['error'])

    def test_qr_first_punch_in(self):
        # First punch today should register as 'in' and create a MIS-PUNCH attendance row
        response = self.client.post('/hr/attendance/qr-lookup', data=dict(
            code='EMP001'
        ))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['action'], 'in')
        self.assertIsNotNone(data['action_at'])
        self.assertEqual(data['attendance']['status'], 'MIS-PUNCH') # only 1 punch, so mis-punch
        
        # Verify database
        punches = RawPunchLog.query.filter_by(employee_code='EMP001').all()
        self.assertEqual(len(punches), 1)
        self.assertEqual(punches[0].punch_direction, 'IN')
        
        att = Attendance.query.filter_by(employee_code='EMP001', attendance_date=date.today()).first()
        self.assertIsNotNone(att)
        self.assertEqual(att.status, 'MIS-PUNCH')
        self.assertIsNotNone(att.punch_in)
        self.assertIsNone(att.punch_out)

    def test_qr_punch_cooldown(self):
        # Scan employee code
        self.client.post('/hr/attendance/qr-lookup', data=dict(code='EMP001'))
        
        # Scan again immediately (within 30 seconds cooldown)
        response = self.client.post('/hr/attendance/qr-lookup', data=dict(code='EMP001'))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        # Should result in 'cooldown' and not insert a new punch
        self.assertEqual(data['action'], 'cooldown')
        self.assertEqual(RawPunchLog.query.count(), 1) # Still 1 punch

    def test_qr_punch_in_and_out(self):
        # 1. Punch In
        self.client.post('/hr/attendance/qr-lookup', data=dict(code='EMP001'))
        
        # Get the first punch log and shift it 5 hours back in time to bypass cooldown
        # and test working hours computation
        punch_in_log = RawPunchLog.query.first()
        self.assertIsNotNone(punch_in_log)
        
        five_hours_ago = datetime.now() - timedelta(hours=5)
        punch_in_log.log_date = five_hours_ago
        
        # Also update the Attendance record punch_in time
        att = Attendance.query.filter_by(employee_code='EMP001').first()
        att.punch_in = five_hours_ago
        db.session.commit()
        
        # 2. Punch Out (this is 5 hours later)
        response = self.client.post('/hr/attendance/qr-lookup', data=dict(code='EMP001'))
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        
        self.assertEqual(data['action'], 'out')
        self.assertEqual(data['attendance']['status'], 'Present') # 5 hours > 4 hours = Present
        self.assertEqual(data['attendance']['total_hours'], '5h 0m') # 5 hours working
        
        # Verify db
        self.assertEqual(RawPunchLog.query.count(), 2)
        db_att = Attendance.query.filter_by(employee_code='EMP001').first()
        self.assertEqual(db_att.status, 'Present')
        self.assertEqual(db_att.total_hours, 5.0)
        self.assertIsNotNone(db_att.punch_out)
