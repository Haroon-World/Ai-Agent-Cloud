import unittest
from datetime import date, timedelta
from app import create_app
from models import db, Business, Doctor, DoctorSchedule, Service, Appointment, Conversation, sync_postgres_sequences, auto_migrate_db
from services.booking_service import BookingService, RequestCache
from ai.response_generator import _format_doctor_schedule_lines
from ai.prompts import _get_cached_services_info
from config.config import Config


class TestNewDoctorWorkflow(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            TESTING = True
            SECRET_KEY = "test-secret"
            LLM_PROVIDER = "mock"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        self.app_context = self.app.app_context()
        self.app_context.push()

        RequestCache.clear()

        # Retrieve seeded clinic and service
        self.clinic = db.session.get(Business, 1)
        self.clinic.consultation_fee = 2500.0
        db.session.commit()

        self.svc1 = db.session.get(Service, 1)

    def tearDown(self):
        RequestCache.clear()
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_sync_postgres_sequences_safe_on_sqlite(self):
        """sync_postgres_sequences should execute gracefully without crashing on SQLite."""
        try:
            sync_postgres_sequences()
        except Exception as e:
            self.fail(f"sync_postgres_sequences raised exception on SQLite: {e}")

    def test_dynamic_add_new_doctor_auto_provisions_consultation_service(self):
        """When a new doctor is added with no services, ensure_doctor_consultation_service creates one."""
        new_doc = Doctor(
            business_id=1,
            name="Dr. Ali Raza",
            specialization="Neurologist",
            working_days="Monday,Wednesday,Friday",
            start_time="10:00",
            end_time="16:00",
            slot_interval=30,
            is_active=True
        )
        db.session.add(new_doc)
        db.session.commit()

        # Call ensure_doctor_consultation_service
        consult_svc = BookingService.ensure_doctor_consultation_service(1, new_doc.id)
        self.assertIsNotNone(consult_svc)
        self.assertEqual(consult_svc.doctor_id, new_doc.id)
        self.assertIn("Consultation", consult_svc.name)
        self.assertEqual(consult_svc.price, 2500.0)

        # Check that it's persisted in the database
        db_svc = Service.query.filter_by(business_id=1, doctor_id=new_doc.id).first()
        self.assertIsNotNone(db_svc)
        self.assertEqual(db_svc.id, consult_svc.id)

    def test_auto_migrate_db_creates_missing_schedules_and_services(self):
        """auto_migrate_db should populate DoctorSchedule and consultation Service for existing doctors."""
        bare_doc = Doctor(
            business_id=1,
            name="Dr. Maria Qureshi",
            specialization="Dermatologist",
            working_days="Tuesday,Thursday",
            start_time="11:00",
            end_time="15:00",
            slot_interval=30,
            is_active=True
        )
        db.session.add(bare_doc)
        db.session.commit()

        # Doctor has no schedules and no services yet
        self.assertEqual(DoctorSchedule.query.filter_by(doctor_id=bare_doc.id).count(), 0)
        self.assertEqual(Service.query.filter_by(doctor_id=bare_doc.id).count(), 0)

        # Run auto_migrate_db
        auto_migrate_db()

        # Now schedules must exist for all 7 days
        scheds = DoctorSchedule.query.filter_by(doctor_id=bare_doc.id).all()
        self.assertEqual(len(scheds), 7)
        tue_sched = next(s for s in scheds if s.day_of_week == "Tuesday")
        self.assertTrue(tue_sched.is_available)
        self.assertEqual(tue_sched.start_time, "11:00")
        self.assertEqual(tue_sched.end_time, "15:00")
        mon_sched = next(s for s in scheds if s.day_of_week == "Monday")
        self.assertFalse(mon_sched.is_available)

        # And a consultation service must now exist
        svc = Service.query.filter_by(doctor_id=bare_doc.id).first()
        self.assertIsNotNone(svc)
        self.assertEqual(svc.name, "Consultation & Checkup")

    def test_format_doctor_schedule_lines_with_list_working_days(self):
        """_format_doctor_schedule_lines must not crash when working_days is a list."""
        doc_dict_with_list = {
            "name": "Dr. Tariq",
            "working_days": ["Monday", "Wednesday", "Friday"],
            "start_time": "09:00",
            "end_time": "17:00",
            "weekly_schedule": []  # Empty so it falls back to flat schedule logic
        }
        try:
            lines = _format_doctor_schedule_lines(doc_dict_with_list, target_day=None)
            self.assertTrue(len(lines) > 0)
            self.assertTrue(any("Monday" in l and "9:00 AM" in l for l in lines))
            self.assertTrue(any("Tuesday: Closed" in l for l in lines))
        except AttributeError as e:
            self.fail(f"Crashed with AttributeError on list working_days: {e}")

    def test_prompts_cached_services_auto_provisions_consultation(self):
        """_get_cached_services_info must auto-provision consultation instead of 'No active services listed'."""
        new_doc = Doctor(
            business_id=1,
            name="Dr. Bilal Consultant",
            specialization="Pediatrician",
            working_days="Monday,Tuesday,Wednesday",
            start_time="09:00",
            end_time="14:00",
            is_active=True
        )
        db.session.add(new_doc)
        db.session.commit()
        RequestCache.clear()

        services_str = _get_cached_services_info(1, 2500.0)
        self.assertIn("Dr. Bilal Consultant", services_str)
        self.assertNotIn("No active services listed.", services_str)
        self.assertIn("Consultation", services_str)

    def test_check_availability_for_new_doctor_without_service_id(self):
        """check_availability for newly added doctor without service_id should succeed and return slots."""
        # Find next Monday date
        today = date.today()
        days_ahead = (0 - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = today + timedelta(days=days_ahead)
        date_str = target_date.isoformat()

        # Add doctor with Monday schedule
        new_doc = Doctor(
            business_id=1,
            name="Dr. Zafar",
            specialization="Orthopedic",
            working_days="Monday",
            start_time="09:00",
            end_time="12:00",
            slot_interval=30,
            is_active=True
        )
        db.session.add(new_doc)
        db.session.commit()
        auto_migrate_db()

        res = BookingService.check_availability(
            business_id=1,
            doctor_id=new_doc.id,
            service_id=None,
            date_str=date_str
        )
        self.assertTrue(res.get("success"), f"check_availability failed: {res}")
        slots = res.get("available_slots", [])
        self.assertTrue(len(slots) > 0, "Expected non-empty slots for working day")
        self.assertIn("09:00", slots)
        self.assertIn("09:30", slots)

    def test_check_availability_cross_doctor_service_mismatch_fallback(self):
        """If caller passes service_id from another doctor, check_availability remaps or falls back gracefully."""
        today = date.today()
        days_ahead = (0 - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = today + timedelta(days=days_ahead)
        date_str = target_date.isoformat()

        doc_other = Doctor(
            business_id=1,
            name="Dr. Usman",
            specialization="General Physician",
            working_days="Monday",
            start_time="14:00",
            end_time="17:00",
            slot_interval=30,
            is_active=True
        )
        db.session.add(doc_other)
        db.session.commit()
        auto_migrate_db()

        res = BookingService.check_availability(
            business_id=1,
            doctor_id=doc_other.id,
            service_id=self.svc1.id,  # belongs to doc 1!
            date_str=date_str
        )
        self.assertTrue(res.get("success"), f"check_availability failed: {res}")
        slots = res.get("available_slots", [])
        self.assertIn("14:00", slots)

    def test_book_appointment_for_new_doctor_without_explicit_service_id(self):
        """book_appointment should auto-provision/resolve consultation service if service_id is omitted."""
        today = date.today()
        days_ahead = (0 - today.weekday() + 7) % 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = today + timedelta(days=days_ahead)
        date_str = target_date.isoformat()

        doc_new = Doctor(
            business_id=1,
            name="Dr. Hamza",
            specialization="Dentist",
            working_days="Monday",
            start_time="09:00",
            end_time="17:00",
            slot_interval=30,
            is_active=True
        )
        db.session.add(doc_new)
        db.session.commit()
        auto_migrate_db()

        # Book appointment with doctor_id, but NO service_id
        res = BookingService.book_appointment(
            business_id=1,
            customer_name="Kamran Ahmed",
            customer_phone="+92 321 9876543",
            doctor_id=doc_new.id,
            service_id=None,
            appointment_date=date_str,
            appointment_time="09:00"
        )
        self.assertTrue(res.get("success"), f"book_appointment failed: {res}")
        appt = res.get("appointment")
        self.assertIsNotNone(appt)
        self.assertEqual(appt["doctor_id"], doc_new.id)
        booked_svc = db.session.get(Service, appt["service_id"])
        self.assertIsNotNone(booked_svc)
        self.assertEqual(booked_svc.doctor_id, doc_new.id)
        self.assertIn("Consultation", booked_svc.name)


if __name__ == "__main__":
    unittest.main()
