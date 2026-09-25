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
        self.assertIn('History', html)

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

    def test_reschedule_appointment_api(self):
        """Staff can reschedule appointment to new date/time with updated patient details."""
        new_date_str = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        res = self.client.post("/api/admin/appointments/reschedule", json={
            "appointment_id": self.future_appt.id,
            "new_date": new_date_str,
            "new_time": "10:30",
            "customer_name": "Tariq Jameel Updated",
            "customer_phone": "+923001112233",
            "notes": "Patient requested later slot"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

        updated = db.session.get(Appointment, self.future_appt.id)
        self.assertEqual(updated.appointment_date, new_date_str)
        self.assertEqual(updated.appointment_time, "10:30")
        self.assertEqual(updated.customer.name, "Tariq Jameel Updated")
        self.assertEqual(updated.customer.phone, "+923001112233")
        self.assertEqual(updated.status, "CONFIRMED")

    def test_reschedule_modal_and_fixed_action_menu_rendered(self):
        """Reschedule modal and fixed positioning logic are rendered in appointments page."""
        res = self.client.get("/admin/appointments")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn('id="rescheduleModal"', html)
        self.assertIn('id="reschedPatientName"', html)
        self.assertIn('id="reschedPatientPhone"', html)
        self.assertIn('id="reschedDoctorSelect"', html)
        self.assertIn('id="reschedDateInput"', html)
        self.assertIn('id="reschedTimeSelect"', html)
        self.assertIn('openRescheduleModal', html)
        self.assertIn('position: fixed', html)

    def test_get_doctor_slots_api(self):
        """Doctor slots API works via both /api/admin/doctor-slots and /api/admin/doctors/<id>/slots."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Test query string format
        res1 = self.client.get(f"/api/admin/doctor-slots?doctor_id={self.doc.id}&date={today_str}&exclude_appointment_id={self.future_appt.id}")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1.get("success"))
        self.assertIn("slots", data1)
        self.assertEqual(data1.get("doctor_name"), self.doc.name)

        # Test path param format
        res2 = self.client.get(f"/api/admin/doctors/{self.doc.id}/slots?date={today_str}")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("success"))
        self.assertIn("slots", data2)


if __name__ == "__main__":
    unittest.main()

