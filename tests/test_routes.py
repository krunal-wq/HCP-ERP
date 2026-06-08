from tests.test_base import BaseTestCase
from models import User
from index import db

class TestRoutes(BaseTestCase):
    def test_dashboard_redirects_for_anonymous_user(self):
        # Accessing dashboard without login should redirect to login page
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        # Use assertIn since query parameters (like ?next=%2F) might be appended
        self.assertIn('/login', response.location)

    def test_dashboard_loads_for_authenticated_admin(self):
        # Login as admin
        self.login('admin', 'admin123')
        
        # Access dashboard
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Verify bento grid page content
        self.assertIn(b'Welcome,', response.data)
        self.assertIn(b'Administrator', response.data)
        self.assertIn(b'CRM Dashboard', response.data)
        self.assertIn(b'HR Management', response.data)

    def test_page_not_found_renders_custom_404(self):
        # Access a non-existent URL
        response = self.client.get('/invalid-route-that-does-not-exist')
        self.assertEqual(response.status_code, 404)
        
        # Verify custom 404 handler template rendering
        self.assertIn(b'404', response.data)
        self.assertIn(b'Page Not Found', response.data)
