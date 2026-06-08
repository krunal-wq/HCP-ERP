import os
import sys
import unittest

# Ensure the project root is in the path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Configure database to use in-memory SQLite before index is imported
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from index import app, db
from models import User, Employee
from core.permissions import seed_permissions
from modules.hr.routes.hr_master_routes import seed_defaults

class BaseTestCase(unittest.TestCase):
    def setUp(self):
        # Set testing flag
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for easier API testing
        
        self.app = app
        self.client = app.test_client()
        self.ctx = app.app_context()
        self.ctx.push()

        # Create all tables in sqlite memory
        db.create_all()

        # Seed default configurations and permissions
        seed_permissions()
        try:
            seed_defaults()
        except Exception:
            pass

        # Create default Admin user
        self.admin_user = User(
            username='admin',
            email='admin@hcp.com',
            full_name='Administrator',
            role='admin',
            is_active=True
        )
        self.admin_user.set_password('admin123')
        db.session.add(self.admin_user)

        # Create default regular User
        self.regular_user = User(
            username='qa_user',
            email='qa@hcp.com',
            full_name='QA Tester',
            role='user',
            is_active=True
        )
        self.regular_user.set_password('user123')
        db.session.add(self.regular_user)

        # Create default Employee linked to regular user (optional link, but helps tests)
        self.employee = Employee(
            employee_code='EMP001',
            employee_id='EMP001',
            first_name='QA',
            middle_name='Test',
            last_name='Tester',
            mobile='1234567890',
            department='Quality Assurance',
            designation='QA Engineer',
            status='active',
            is_deleted=False
        )
        db.session.add(self.employee)
        db.session.commit()

        # Link regular user to employee
        self.employee.user_id = self.regular_user.id
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def login(self, username, password):
        return self.client.post('/login', data=dict(
            username=username,
            password=password
        ), follow_redirects=True)

    def logout(self):
        return self.client.get('/logout', follow_redirects=True)
