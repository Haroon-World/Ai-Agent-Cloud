import unittest
from app import create_app
from models import db, Business, User, ClinicWhatsAppAccount

class TestAdminWhatsAppView(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_whatsapp_view_removed_from_admin(self):
        """Verify that /admin/whatsapp has been completely removed from clinic admin for security."""
        with self.app.app_context():
            resp = self.client.get('/admin/whatsapp')
            self.assertEqual(resp.status_code, 404)
