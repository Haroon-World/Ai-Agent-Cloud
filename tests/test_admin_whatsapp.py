import unittest
from app import create_app
from models import db, Business, User, ClinicWhatsAppAccount

class TestAdminWhatsAppView(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_whatsapp_view_requires_login(self):
        with self.app.app_context():
            resp = self.client.get('/admin/whatsapp', follow_redirects=False)
            self.assertEqual(resp.status_code, 302)
            self.assertIn('/admin/login', resp.headers['Location'])

    def test_whatsapp_view_authenticated(self):
        with self.app.app_context():
            with self.client.session_transaction() as sess:
                sess['user_id'] = 1
                sess['business_id'] = 1
                sess['admin_user'] = 'admin'
                sess['is_platform_admin'] = False

            resp = self.client.get('/admin/whatsapp')
            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode('utf-8')
            self.assertIn('WhatsApp Integration', html)
            self.assertIn('Update WhatsApp Access Token', html)
            self.assertIn('Outbound Test Message', html)
            self.assertIn('Meta Webhook Configuration', html)
