import unittest
from app import create_app
from models import db, Business, Doctor, Service, Customer, Appointment, Conversation
from models.user import User


class TestTopbarSearchAndDashboardDate(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_search_unauthenticated_redirects(self):
        """Unauthenticated call to /admin/api/search must redirect to admin login."""
        res = self.client.get("/admin/api/search?q=Ahmed")
        self.assertIn(res.status_code, (302, 401))

    def test_search_authenticated_returns_grouped_results(self):
        """Authenticated call to /admin/api/search returns grouped results for matching query."""
        admin_user = User.query.filter_by(username="admin").first()
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_user.id if admin_user else 1
            sess["business_id"] = 1
            sess["admin_user"] = "admin"
            sess["clinic_name"] = "Arfa Polyclinic"

        res = self.client.get("/admin/api/search?q=Ahmed")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("query"), "Ahmed")
        self.assertIn("appointments", data.get("results"))
        self.assertIn("doctors", data.get("results"))
        self.assertIn("conversations", data.get("results"))
        self.assertIn("services", data.get("results"))

        # Should match Dr. Ahmed Khan
        doc_names = [d["name"] for d in data["results"]["doctors"]]
        self.assertTrue(any("Ahmed" in name for name in doc_names))

    def test_search_services(self):
        """Authenticated search for services returns matching service records."""
        admin_user = User.query.filter_by(username="admin").first()
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_user.id if admin_user else 1
            sess["business_id"] = 1
            sess["admin_user"] = "admin"
            sess["clinic_name"] = "Arfa Polyclinic"

        res = self.client.get("/admin/api/search?q=Dental")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        svc_names = [s["name"] for s in data["results"]["services"]]
        self.assertTrue(any("Dental" in name for name in svc_names))

    def test_dashboard_duplicate_date_removed(self):
        """Dashboard must not contain the duplicate dashboardDateDisplay badge."""
        admin_user = User.query.filter_by(username="admin").first()
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_user.id if admin_user else 1
            sess["business_id"] = 1
            sess["admin_user"] = "admin"
            sess["clinic_name"] = "Arfa Polyclinic"

        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertNotIn("dashboardDateDisplay", html)
        self.assertIn("topbarDateBadge", html)
        self.assertIn("topbarSearchInput", html)
        self.assertIn("topbarSearchDropdown", html)
