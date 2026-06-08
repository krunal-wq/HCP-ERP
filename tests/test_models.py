from tests.test_base import BaseTestCase
from models import Lead, Employee, ClientMaster, User
from index import db
from datetime import datetime, timedelta, date

class TestModels(BaseTestCase):
    def test_lead_properties_and_helpers(self):
        # Create a test Lead
        lead = Lead(
            code='LD001',
            title='Test Product Lead',
            contact_name='Alice Smith',
            company_name='Wonderland Corp',
            phone='+123456789',
            status='open',
            team_members='2,3,4',
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        db.session.add(lead)
        db.session.commit()

        # Test properties
        self.assertEqual(lead.name, 'Alice Smith')
        self.assertEqual(lead.mobile, '+123456789')
        self.assertEqual(lead.company, 'Wonderland Corp')
        
        # Test lead_age property (should be 5 since created 5 days ago and still open)
        self.assertEqual(lead.lead_age, 5)

        # Update to closed, closed_at = 3 days after creation (age should be 3)
        lead.status = 'close'
        lead.closed_at = lead.created_at + timedelta(days=3)
        db.session.commit()
        self.assertEqual(lead.lead_age, 3)

        # Test get_team_member_ids helper
        self.assertEqual(lead.get_team_member_ids(), [2, 3, 4])

        # Test empty team members handles gracefully
        lead.team_members = ''
        db.session.commit()
        self.assertEqual(lead.get_team_member_ids(), [])

    def test_employee_and_user_creation(self):
        # Verify employee is created and fields are stored correctly
        emp = Employee.query.filter_by(employee_code='EMP001').first()
        self.assertIsNotNone(emp)
        self.assertEqual(emp.first_name, 'QA')
        self.assertEqual(emp.last_name, 'Tester')
        self.assertEqual(emp.department, 'Quality Assurance')
        self.assertEqual(emp.designation, 'QA Engineer')

        # Create a new client master record
        client = ClientMaster(
            company_name='Client ABC',
            contact_name='Bob Jones',
            email='bob@abc.com',
            mobile='9876543210'
        )
        db.session.add(client)
        db.session.commit()

        self.assertIsNotNone(client.id)
        self.assertEqual(ClientMaster.query.count(), 1)
