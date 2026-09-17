import sys, os
sys.path.insert(0, r'D:\AI-Agent-Render')
import unittest
from app import create_app
from config.config import Config
from models import db, Business, Doctor, Service, Customer, Conversation, Appointment
from ai.agent import Agent

class TestConvFlow(unittest.TestCase):
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

        # Create Clinic
        self.clinic = Business(
            name="Arfa Dental Clinic",
            business_type="dental",
            address="123 Main Street",
            phone="+923001234567",
            subscription_status="active"
        )
        db.session.add(self.clinic)
        db.session.commit()

        # Create Doctors
        self.doc1 = Doctor(
            business_id=self.clinic.id,
            name="Dr. Ahmed Khan",
            specialization="General Dentistry",
            working_days="Monday,Tuesday,Wednesday,Thursday,Friday,Saturday",
            start_time="09:00",
            end_time="17:00",
            slot_interval=30
        )
        self.doc2 = Doctor(
            business_id=self.clinic.id,
            name="Dr. Sara Malik",
            specialization="Pediatric & Cosmetic Dentistry",
            working_days="Monday,Tuesday,Friday,Saturday",
            start_time="09:00",
            end_time="17:00",
            slot_interval=30
        )
        db.session.add_all([self.doc1, self.doc2])
        db.session.commit()

        # Create Services
        self.svc1 = Service(
            business_id=self.clinic.id,
            doctor_id=self.doc2.id,
            name="Pediatric & General Consultation",
            duration=30,
            price=2000.0
        )
        self.svc2 = Service(
            business_id=self.clinic.id,
            doctor_id=self.doc2.id,
            name="Dental Cleaning & Scaling",
            duration=30,
            price=4000.0
        )
        db.session.add_all([self.svc1, self.svc2])
        db.session.commit()

        # Create Customer
        self.cust = Customer(
            business_id=self.clinic.id,
            name="Mahr Haroon",
            phone="03187538771"
        )
        db.session.add(self.cust)
        db.session.commit()

        # Create Conversation (simulating WhatsApp thread)
        self.conv = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            pending_customer_name=self.cust.name,
            pending_customer_phone=self.cust.phone,
            workflow_state="START"
        )
        db.session.add(self.conv)
        db.session.commit()

        self.agent = Agent(business_id=self.clinic.id)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_whatsapp_simulation(self):
        steps = [
            "Hi",
            "I want an appointment with Dr sara",
            "Consultation",
            "Tomorrow",
            "09:00 AM",
            "yes"
        ]

        for step in steps:
            print(f"\n--- USER: {step} ---")
            res = self.agent.process_message(self.conv.id, step)
            db.session.refresh(self.conv)
            print(f"BOT ({res.get('status')} | state={self.conv.workflow_state} | awaiting={self.conv.awaiting_input}):")
            print(res.get("content"))
            if res.get("executed_tools"):
                print("Executed tools:", res.get("executed_tools"))

    def test_earliest_slot_flow(self):
        # Create a fresh conversation
        conv2 = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            pending_customer_name=self.cust.name,
            pending_customer_phone=self.cust.phone,
            workflow_state="START"
        )
        db.session.add(conv2)
        db.session.commit()

        steps = [
            "Hi",
            "Dr Sara",
            "Consultation",
            "earliest slot",
            "yes"
        ]

        for step in steps:
            print(f"\n--- EARLIEST TEST USER: {step} ---")
            res = self.agent.process_message(conv2.id, step)
            db.session.refresh(conv2)
            print(f"BOT ({res.get('status')} | state={conv2.workflow_state} | awaiting={conv2.awaiting_input}):")
            print(res.get("content"))
            if res.get("executed_tools"):
                print("Executed tools:", res.get("executed_tools"))
        self.assertEqual(conv2.workflow_state, "BOOKED")

    def test_dont_cancel_negation(self):
        # Once an appointment is booked, saying "don't cancel" should NOT cancel it
        conv3 = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            pending_customer_name=self.cust.name,
            pending_customer_phone=self.cust.phone,
            workflow_state="BOOKED"
        )
        db.session.add(conv3)
        db.session.commit()

        res = self.agent.process_message(conv3.id, "please don't cancel my appointment")
        db.session.refresh(conv3)
        self.assertEqual(conv3.workflow_state, "BOOKED")
        self.assertIn("not been cancelled", res.get("content").lower())

    def test_question_does_not_accidentally_book(self):
        # Asking a question should not trigger book_appointment
        conv4 = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            selected_doctor_id=self.doc2.id,
            selected_service_id=self.svc1.id,
            requested_date="2026-09-18",
            pending_customer_name=self.cust.name,
            pending_customer_phone=self.cust.phone,
            workflow_state="CHECKING_AVAILABILITY",
            awaiting_input="time_choice"
        )
        db.session.add(conv4)
        db.session.commit()

        res = self.agent.process_message(conv4.id, "why were you telling me 1.30")
        db.session.refresh(conv4)
        self.assertNotEqual(conv4.workflow_state, "BOOKED")
        self.assertNotIn("successfully booked", res.get("content").lower())

    def test_inactivity_timeout_resets_draft(self):
        from datetime import datetime, timezone, timedelta
        from models import Message

        conv = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            selected_doctor_id=self.doc2.id,
            selected_service_id=self.svc1.id,
            requested_date="2026-09-18",
            requested_time="09:00",
            pending_customer_name="Ali",
            pending_customer_phone="03001234567",
            workflow_state="COLLECTING_INFO",
            awaiting_input="service_choice"
        )
        db.session.add(conv)
        db.session.commit()

        # Simulate last message 3 hours ago
        past_time = datetime.now(timezone.utc) - timedelta(hours=3)
        msg = Message(
            conversation_id=conv.id,
            role="user",
            content="Earlier message 3 hours ago",
            created_at=past_time
        )
        db.session.add(msg)
        conv.updated_at = past_time
        db.session.commit()

        # User sends a new message after 3 hours
        res = self.agent.process_message(conv.id, "Hi")
        db.session.refresh(conv)

        # Verify draft state has been completely reset
        self.assertIsNone(conv.selected_doctor_id)
        self.assertIsNone(conv.selected_service_id)
        self.assertIsNone(conv.requested_date)
        self.assertIsNone(conv.requested_time)
        self.assertIsNone(conv.pending_customer_name)
        self.assertIsNone(conv.pending_customer_phone)

    def test_booking_for_another_patient_with_different_number(self):
        conv = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            pending_customer_name=None,
            pending_customer_phone=None,
            workflow_state="START"
        )
        db.session.add(conv)
        db.session.commit()

        self.agent.process_message(conv.id, "Dr Sara")
        self.agent.process_message(conv.id, "Consultation")
        r_earliest = self.agent.process_message(conv.id, "earliest slot")
        db.session.refresh(conv)
        self.assertIn("share the patient's full name and mobile number", r_earliest.get("content", ""))

        # User books for another patient: Ali, with separate mobile 03001234567
        r_book = self.agent.process_message(conv.id, "For Ali, 03001234567")
        db.session.refresh(conv)
        self.assertEqual(conv.workflow_state, "BOOKED")

        # Verify appointment customer is Ali with 03001234567
        appt = Appointment.query.filter_by(conversation_id=conv.id).first()
        self.assertIsNotNone(appt)
        self.assertEqual(appt.customer.name, "Ali")
        self.assertEqual(appt.customer.phone, "03001234567")
        # Verify booked_by_phone is the WhatsApp thread phone
        self.assertEqual(appt.booked_by_phone, self.cust.phone)

    def test_booking_for_another_patient_using_whatsapp_number(self):
        conv = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            pending_customer_name=None,
            pending_customer_phone=None,
            workflow_state="START"
        )
        db.session.add(conv)
        db.session.commit()

        self.agent.process_message(conv.id, "Dr Sara")
        self.agent.process_message(conv.id, "Consultation")
        self.agent.process_message(conv.id, "earliest slot")
        
        # User specifies patient name only
        r_name = self.agent.process_message(conv.id, "For Ali")
        db.session.refresh(conv)
        # Agent asks whether to use WhatsApp contact number or a different mobile
        self.assertIn(self.cust.phone, r_name.get("content", ""))

        # User confirms to use WhatsApp contact number
        r_confirm = self.agent.process_message(conv.id, "use this number")
        db.session.refresh(conv)
        self.assertEqual(conv.workflow_state, "BOOKED")

        # Verify appointment is booked for Ali with WhatsApp number
        appt = Appointment.query.filter_by(conversation_id=conv.id).first()
        self.assertIsNotNone(appt)
        self.assertEqual(appt.customer.name, "Ali")
        self.assertEqual(appt.customer.phone, self.cust.phone)
        self.assertEqual(appt.booked_by_phone, self.cust.phone)

    def test_subsequent_booking_after_booked_state_prompts_patient_details(self):
        conv = Conversation(
            business_id=self.clinic.id,
            customer_id=self.cust.id,
            status="AI",
            channel="whatsapp",
            selected_doctor_id=self.doc2.id,
            selected_service_id=self.svc1.id,
            requested_date="2026-09-18",
            requested_time="09:00",
            pending_customer_name="Ali",
            pending_customer_phone="03001234567",
            workflow_state="BOOKED"
        )
        db.session.add(conv)
        db.session.commit()

        # User initiates a new booking request
        r1 = self.agent.process_message(conv.id, "I want to book another appointment with Dr Sara")
        db.session.refresh(conv)
        # Pending patient details should have been reset
        self.assertIsNone(conv.pending_customer_name)
        self.assertIsNone(conv.pending_customer_phone)

        self.agent.process_message(conv.id, "Consultation")
        r_earliest = self.agent.process_message(conv.id, "earliest slot")
        # Verify agent prompts for patient details again instead of assuming Ali
        self.assertIn("share the patient's full name and mobile number", r_earliest.get("content", ""))

if __name__ == "__main__":
    unittest.main()

