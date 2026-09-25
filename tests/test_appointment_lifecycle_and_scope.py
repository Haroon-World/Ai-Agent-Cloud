import unittest
from datetime import datetime, timedelta
from app import create_app
from config.config import Config
from models import db, Business, Appointment, Customer, Doctor, Service, Reminder
from seed import seed_database


class TestAppointmentLifecycleAndScope(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            TESTING = True
            SECRET_KEY = "test-secret"
            LLM_PROVIDER = "mock"

        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        seed_database(self.app)

        self.client = self.app.test_client()
        biz = Business.query.first()
        self.business_id = biz.id if biz else 1
        self.doc = Doctor.query.filter_by(business_id=self.business_id).first()
        self.svc = Service.query.filter_by(business_id=self.business_id).first()

        # Create patient
        self.cust = Customer(
            business_id=self.business_id,
            name="Tariq Jameel",
            phone="+923009998877"
        )
        db.session.add(self.cust)
        db.session.flush()

        # Create past appointment
        past_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        self.past_appt = Appointment(
            business_id=self.business_id,
            customer_id=self.cust.id,
            doctor_id=self.doc.id,
            service_id=self.svc.id,
            appointment_date=past_date,
            appointment_time="11:00 AM",
            status="CONFIRMED"
        )
        db.session.add(self.past_appt)

        # Create upcoming appointment
        future_date = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        self.future_appt = Appointment(
            business_id=self.business_id,
            customer_id=self.cust.id,
            doctor_id=self.doc.id,
            service_id=self.svc.id,
            appointment_date=future_date,
            appointment_time="02:00 PM",
            status="CONFIRMED"
        )
        db.session.add(self.future_appt)
        db.session.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["business_id"] = self.business_id
            sess["is_platform_admin"] = False

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_past_appointment_renders_as_completed(self):
        """Past confirmed appointments must render with COMPLETED status badge."""
        res = self.client.get("/admin/appointments")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Scope tabs present
        self.assertIn('id="tabScopeUpcoming"', html)
        self.assertIn('id="tabScopePast"', html)
        self.assertIn('Upcoming &amp; Today', html)
        self.assertIn('Past History', html)

        # Past appointment has effective status COMPLETED in row and badge
        self.assertIn('badge-pill-completed', html)
        self.assertIn('COMPLETED', html)

    def test_update_status_to_completed_api(self):
        """Staff can manually mark appointment as COMPLETED."""
        res = self.client.post("/api/admin/appointments/update-status", json={
            "appointment_id": self.future_appt.id,
            "status": "COMPLETED"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "COMPLETED")

        updated = db.session.get(Appointment, self.future_appt.id)
        self.assertEqual(updated.status, "COMPLETED")

    def test_update_status_to_cancelled_api(self):
        """Staff can cancel appointment with reason."""
        res = self.client.post("/api/admin/appointments/update-status", json={
            "appointment_id": self.future_appt.id,
            "status": "CANCELLED",
            "reason": "Patient called to reschedule"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        updated = db.session.get(Appointment, self.future_appt.id)
        self.assertEqual(updated.status, "CANCELLED")


if __name__ == "__main__":
    unittest.main()
