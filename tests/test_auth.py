from tests.test_base import BaseTestCase
from models import User, LoginLog, Employee
from index import db
from datetime import datetime, timedelta

class TestAuth(BaseTestCase):
    def test_login_success_username(self):
        # Test login via username
        response = self.login('admin', 'admin123')
        self.assertIn(b'Welcome, Administrator!', response.data)
        
        # Verify db state for last login
        user = User.query.filter_by(username='admin').first()
        self.assertIsNotNone(user.last_login)
        
        # Verify audit log or login log was created
        log = LoginLog.query.filter_by(username='admin').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, 'success')

    def test_login_success_email(self):
        # Test login via email
        response = self.login('admin@hcp.com', 'admin123')
        self.assertIn(b'Welcome, Administrator!', response.data)

    def test_login_success_employee_code(self):
        # Test login via employee code
        response = self.login('EMP001', 'user123')
        self.assertIn(b'Welcome, QA Tester!', response.data)

    def test_login_failed_invalid_credentials(self):
        # Test wrong password
        response = self.login('admin', 'wrongpassword')
        self.assertIn(b'Wrong password!', response.data)
        
        # Check login attempts count
        user = User.query.filter_by(username='admin').first()
        self.assertEqual(user.login_attempts, 1)

    def test_login_failed_nonexistent_user(self):
        response = self.login('nonexistent', 'password')
        self.assertIn(b'Invalid username / email / employee code!', response.data)

    def test_account_lockout_logic(self):
        # Trigger 5 failed login attempts
        user = User.query.filter_by(username='qa_user').first()
        self.assertEqual(user.login_attempts, 0)

        for i in range(5):
            response = self.login('qa_user', 'wrong')
            if i < 4:
                self.assertIn(b'Wrong password!', response.data)
            else:
                self.assertIn(b'Too many attempts! Locked for 15 min.', response.data)

        # Confirm user is locked in database
        db.session.refresh(user)
        self.assertEqual(user.login_attempts, 5)
        self.assertTrue(user.is_locked())

        # Next login attempt should be rejected due to lockout
        response = self.login('qa_user', 'user123')
        self.assertIn(b'Account locked! Try again in', response.data)

    def test_login_disabled_account(self):
        # Disable regular user
        user = User.query.filter_by(username='qa_user').first()
        user.is_active = False
        db.session.commit()

        # Login should be blocked
        response = self.login('qa_user', 'user123')
        self.assertIn(b'Account disabled. Contact admin.', response.data)

    def test_logout(self):
        # Login first
        self.login('admin', 'admin123')
        # Send logout request
        response = self.logout()
        # Verify redirect/flash message
        self.assertIn(b'Logged out.', response.data)
