import unittest
from app import create_app
from models import db, Business, Doctor, Service, Customer, Appointment
from models.user import User
from routes.admin import normalize_time_to_24h, format_time_to_12h


class Test12HrTimeAndManualBooking(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["WTF_CSRF_ENABLED"] = False
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        admin_user = User.query.filter_by(username="admin").first()
        self.admin_id = admin_user.id if admin_user else 1

    def tearDown(self):
        self.app_context.pop()

    def _login_session(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_id
            sess["business_id"] = 1
            sess["admin_user"] = "admin"
            sess["clinic_name"] = "Arfa Polyclinic"

    def test_normalize_time_to_24h(self):
        """Test conversion of 12-hour AM/PM strings and 24h strings to standard HH:MM."""
        self.assertEqual(normalize_time_to_24h("09:00 AM"), "09:00")
        self.assertEqual(normalize_time_to_24h("9:30 am"), "09:30")
        self.assertEqual(normalize_time_to_24h("01:15 PM"), "13:15")
        self.assertEqual(normalize_time_to_24h("2:00 pm"), "14:00")
        self.assertEqual(normalize_time_to_24h("12:00 PM"), "12:00")
        self.assertEqual(normalize_time_to_24h("12:00 AM"), "00:00")
        self.assertEqual(normalize_time_to_24h("12:30 AM"), "00:30")
        self.assertEqual(normalize_time_to_24h("14:00"), "14:00")
        self.assertEqual(normalize_time_to_24h("09:00"), "09:00")
        self.assertEqual(normalize_time_to_24h(""), "")

    def test_format_time_to_12h(self):
        """Test conversion of 24h strings to 12-hour AM/PM representation."""
        self.assertEqual(format_time_to_12h("09:00"), "09:00 AM")
        self.assertEqual(format_time_to_12h("13:00"), "01:00 PM")
        self.assertEqual(format_time_to_12h("14:30"), "02:30 PM")
        self.assertEqual(format_time_to_12h("00:00"), "12:00 AM")
        self.assertEqual(format_time_to_12h("12:00"), "12:00 PM")
        self.assertEqual(format_time_to_12h("21:00"), "09:00 PM")
        # Idempotence on already formatted strings
        self.assertEqual(format_time_to_12h("02:00 PM"), "02:00 PM")

    def test_template_filter_format_12hr(self):
        """Test the registered Jinja template filter format_12hr."""
        filter_func = self.app.jinja_env.filters.get("format_12hr")
        self.assertIsNotNone(filter_func)
        self.assertEqual(filter_func("09:00"), "09:00 AM")
        self.assertEqual(filter_func("17:00"), "05:00 PM")
        self.assertEqual(filter_func("20:45"), "08:45 PM")
        self.assertEqual(filter_func(""), "")
        self.assertEqual(filter_func(None), "")

    def test_api_doctor_slots_returns_12hr_labels(self):
        """Verify /api/admin/doctor-slots returns slots with 12h labels."""
        self._login_session()
        doctor = Doctor.query.filter_by(business_id=1, is_active=True).first()
        self.assertIsNotNone(doctor)

        res = self.client.get(f"/api/admin/doctor-slots?doctor_id={doctor.id}&date=2026-09-25")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        slots = data.get("slots", [])
        self.assertGreater(len(slots), 0)

        # Check first slot structure
        s0 = slots[0]
        self.assertIn("time", s0)
        self.assertIn("time_12h", s0)
        self.assertIn("status", s0)
        self.assertTrue("AM" in s0["time_12h"] or "PM" in s0["time_12h"])

    def test_manual_booking_with_12hr_time_and_conflict_detection(self):
        """Verify manual booking supports 12-hour AM/PM inputs and gives inline conflict error on occupied slot."""
        self._login_session()
        doctor = Doctor.query.filter_by(business_id=1, is_active=True).first()
        service = Service.query.filter_by(business_id=1, is_active=True).first()
        self.assertIsNotNone(doctor)
        self.assertIsNotNone(service)

        test_date = "2026-10-15"
        test_time_12h = "10:00 AM"

        # 1. Clean any existing appointment for this slot
        Appointment.query.filter_by(
            business_id=1,
            doctor_id=doctor.id,
            appointment_date=test_date,
            appointment_time="10:00"
        ).delete()
        db.session.commit()

        # 2. Book using 12-hour formatted time "10:00 AM"
        payload = {
            "doctor_id": doctor.id,
            "service_id": service.id,
            "appointment_date": test_date,
            "appointment_time": test_time_12h,
            "customer_name": "Tariq Mahmood",
            "customer_phone": "03009988776",
            "notes": "Testing 12hr time template"
        }
        res1 = self.client.post("/api/admin/appointments/manual-book", json=payload)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1.get("success"))

        # Verify it was saved in normalized 24-hour format "10:00" in database
        created = Appointment.query.filter_by(id=data1["appointment_id"]).first()
        self.assertIsNotNone(created)
        self.assertEqual(created.appointment_time, "10:00")

        # 3. Attempting to book the SAME occupied slot should return 409 conflict with clear message
        res2 = self.client.post("/api/admin/appointments/manual-book", json=payload)
        self.assertEqual(res2.status_code, 409)
        data2 = res2.get_json()
        self.assertFalse(data2.get("success"))
        self.assertIn("error", data2)
        # Message must clearly mention the occupied conflict
        self.assertTrue(
            "already occupied" in data2["error"].lower() or
            "already booked" in data2["error"].lower() or
            "unavailable" in data2["error"].lower()
        )


if __name__ == "__main__":
    unittest.main()
