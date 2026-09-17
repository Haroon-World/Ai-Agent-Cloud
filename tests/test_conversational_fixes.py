import unittest
from app import create_app
from config.config import Config
from models import db
from seed import seed_database
from ai.llm_client import _extract_name, MockAdapter
from ai.response_generator import _format_availability
from services.whatsapp_service import WhatsAppService

class TestConversationalFixes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        class TestConfig(Config):
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            TESTING = True
            SECRET_KEY = "test-secret"
            LLM_PROVIDER = "mock"
            WHATSAPP_PHONE_NUMBER_ID = "1313879111808444"
            WHATSAPP_ACCESS_TOKEN = "mock-token"

        cls.app = create_app(TestConfig)
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()
        seed_database(cls.app)

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def test_name_extraction_third_party_and_correction(self):
        """Verify name extraction for 3rd-party and correction statements."""
        self.assertEqual(
            _extract_name("The appointment is not for ABDULLAH KASHIF it is for Abdul wahab"),
            "Abdul Wahab"
        )
        self.assertEqual(
            _extract_name("Change the name of the patient :Abdul Wahab"),
            "Abdul Wahab"
        )
        self.assertEqual(
            _extract_name("Abdul wahab", is_awaiting_name=True),
            "Abdul Wahab"
        )
        self.assertEqual(
            _extract_name("patient name: Abdul Wahab"),
            "Abdul Wahab"
        )

    def test_earliest_slot_does_not_trigger_eye_checkup(self):
        """Verify that 'Earliest slot' does NOT match 'ear' in non_dental_terms and trigger eye disclaimer."""
        adapter = MockAdapter()
        doctor_roster = [
            {"id": 1, "name": "Dr. Ahmed Khan", "specialization": "General Dentistry & Orthodontics"},
            {"id": 2, "name": "Dr. Sara Malik", "specialization": "Pediatric & Cosmetic Dentistry"}
        ]
        service_roster = [
            {"id": 1, "name": "Dental Checkup & Consultation", "doctor_id": 1},
            {"id": 5, "name": "Root Canal Treatment", "doctor_id": 1}
        ]
        conv_state = {
            "selected_doctor_id": 1,
            "selected_service_id": 5,
            "workflow_state": "COLLECTING_INFO",
            "doctor_roster": doctor_roster,
            "service_roster": service_roster
        }
        res = adapter.chat_completion(
            system_prompt="Clinic Name: Arfa Dental Clinic",
            messages=[{"role": "user", "content": "Earliest slot"}],
            tools=[],
            conversation_state=conv_state
        )
        content = res.get("content", "")
        self.assertNotIn("eye checkup", content.lower())
        self.assertNotIn("non-rostered services", content.lower())
        self.assertIn("earliest available slot", content.lower())

    def test_initial_greeting_welcome_branding(self):
        """Verify that 'Hi' or 'Hello' receives a warm Arfa Dental Clinic greeting."""
        adapter = MockAdapter()
        doctor_roster = [
            {"id": 1, "name": "Dr. Ahmed Khan", "specialization": "General Dentistry & Orthodontics"},
            {"id": 2, "name": "Dr. Sara Malik", "specialization": "Pediatric & Cosmetic Dentistry"}
        ]
        conv_state = {
            "awaiting_input": "doctor_choice",
            "clinic_name": "Arfa Dental Clinic",
            "doctor_roster": doctor_roster,
            "service_roster": []
        }
        res = adapter.chat_completion(
            system_prompt="Clinic Name: Arfa Dental Clinic",
            messages=[{"role": "user", "content": "Hi"}],
            tools=[],
            conversation_state=conv_state
        )
        content = res.get("content", "")
        self.assertIn("welcome", content.lower())
        self.assertIn("arfa dental clinic", content.lower())
        self.assertIn("dr. ahmed khan", content.lower())

    def test_whatsapp_formatting(self):
        """Verify that standard markdown **bold** is converted to WhatsApp single asterisk *bold*."""
        raw_msg = "🎉 **Your appointment has been successfully booked and confirmed!**\n• **Doctor:** Dr. Ahmed Khan"
        wa_msg = WhatsAppService.format_for_whatsapp(raw_msg)
        self.assertNotIn("**", wa_msg)
        self.assertIn("*Your appointment has been successfully booked and confirmed!*", wa_msg)
        self.assertIn("*Doctor:*", wa_msg)

    def test_availability_formatting_when_both_name_and_phone_known(self):
        """Verify that when requested time is matched and customer info is known, it does not dump 15 slots."""
        results = [{
            "doctor_id": 1,
            "doctor_name": "Dr. Ahmed Khan",
            "available_slots": ["09:00", "09:30", "12:00", "15:00"],
            "date": "2026-09-18"
        }]
        conv_state = {
            "requested_time": "15:00",
            "pending_customer_name": "Abdul Wahab",
            "pending_customer_phone": "923187538771"
        }
        resp = _format_availability(
            tool_data={"success": True, "results": results, "date": "2026-09-18"},
            lang="en",
            user_text_lower="friday at 3 pm",
            conv_state=conv_state
        )
        self.assertIn("03:00 PM", resp)
        self.assertIn("Abdul Wahab", resp)
        self.assertIn("Shall I go ahead and confirm this appointment?", resp)
        self.assertNotIn("Here are the available appointment slots", resp)

    def test_time_extraction_default_pm(self):
        """Verify that bare hour/minute between 1 and 7 defaults to PM (clinic hours)."""
        from ai.llm_client import _extract_time_str
        self.assertEqual(_extract_time_str("1.30"), "13:30")
        self.assertEqual(_extract_time_str("1:30"), "13:30")
        self.assertEqual(_extract_time_str("3 pm"), "15:00")
        self.assertEqual(_extract_time_str("1.30 am"), "01:30")
        self.assertEqual(_extract_time_str("10.30"), "10:30")

    def test_why_question_detection_and_no_autobooking(self):
        """Verify that 'Then why did you told me wrong' is classified as question and does not trigger book_appointment."""
        from ai.llm_client import _is_question_query
        self.assertTrue(_is_question_query("Then why were you telling me 1.30"))
        self.assertTrue(_is_question_query("Then why did you told me wrong"))

        adapter = MockAdapter()
        conv_state = {
            "selected_doctor_id": 2,
            "selected_service_id": 3,
            "target_date_str": "2026-09-18",
            "pending_customer_name": "Ali",
            "pending_customer_phone": "923187538771",
            "workflow_state": "SELECTING_TIME",
            "all_offered_slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "16:00", "16:30"],
            "last_offered_slots": {
                "2": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "16:00", "16:30"]
            },
            "doctor_roster": [
                {"id": 2, "name": "Dr. Sara Malik", "specialization": "Pediatric & Cosmetic Dentistry"}
            ],
            "service_roster": [
                {"id": 3, "name": "Teeth Whitening", "doctor_id": 2}
            ]
        }
        res = adapter.chat_completion(
            system_prompt="Clinic Name: Arfa Dental Clinic",
            messages=[{"role": "user", "content": "Then why did you told me wrong"}],
            tools=[],
            conversation_state=conv_state
        )
        # Should not book appointment tool call
        self.assertEqual(res.get("tool_calls"), [])
        content = res.get("content", "")
        self.assertIn("apologize", content.lower())
        self.assertIn("05:00 pm", content.lower())

    def test_negation_dont_cancel_safety(self):
        """Verify that 'don't cancel my appointment' does NOT trigger cancel_appointment."""
        adapter = MockAdapter()
        conv_state = {
            "selected_doctor_id": 1,
            "selected_service_id": 1,
            "workflow_state": "BOOKED",
            "intent": "BOOK_APPOINTMENT",
            "pending_customer_name": "Ali Hassan",
            "pending_customer_phone": "03001234567"
        }
        res = adapter.chat_completion(
            system_prompt="Clinic Name: Arfa Dental Clinic",
            messages=[{"role": "user", "content": "Please don't cancel my appointment"}],
            tools=[],
            conversation_state=conv_state
        )
        self.assertEqual(res.get("tool_calls"), [])
        content = res.get("content", "")
        self.assertIn("not been cancelled", content.lower())

    def test_no_word_not_parsed_as_nine(self):
        """Verify that 'no', 'no thanks', 'room no 2' are not parsed as 9:00 AM, while 'no baje' is."""
        from ai.llm_client import _extract_time_str
        from ai.agent import _extract_time_token

        self.assertIsNone(_extract_time_str("no"))
        self.assertIsNone(_extract_time_token("no"))
        self.assertIsNone(_extract_time_str("no thanks"))
        self.assertIsNone(_extract_time_token("no thanks"))
        self.assertIsNone(_extract_time_str("room no 2"))
        self.assertIsNone(_extract_time_token("room no 2"))

        self.assertEqual(_extract_time_str("no baje"), "09:00")
        self.assertEqual(_extract_time_token("no baje"), "09:00")

    def test_room_no_2_does_not_cancel_booking(self):
        """Verify that mentioning 'room no 2' does not cancel booking during confirmation."""
        adapter = MockAdapter()
        conv_state = {
            "awaiting_input": "confirmation",
            "workflow_state": "SELECTING_TIME",
            "pending_customer_name": "Ali",
            "pending_customer_phone": "03001234567",
            "target_date_str": "2026-09-18",
            "req_time": "10:00",
            "selected_doctor_id": 1,
            "selected_service_id": 1
        }
        res = adapter.chat_completion(
            system_prompt="Clinic Name: Arfa Dental Clinic",
            messages=[{"role": "user", "content": "room no 2"}],
            tools=[],
            conversation_state=conv_state
        )
        content = res.get("content", "")
        self.assertNotIn("cancelled your booking request", content.lower())

    def test_earliest_slot_resolution_and_confirmation(self):
        """Verify that 'earliest slot' populates requested_date, requested_time, awaiting_input='confirmation', and 'yes' books the appointment."""
        from models import Conversation, Customer
        from ai.agent import Agent

        customer = Customer(
            business_id=1,
            name="Mahr Haroon",
            phone="923187538771"
        )
        db.session.add(customer)
        db.session.commit()

        conv = Conversation(
            business_id=1,
            customer_id=customer.id,
            channel="whatsapp",
            status="AI",
            workflow_state="COLLECTING_INFO",
            selected_doctor_id=2,  # Dr. Sara Malik
            selected_service_id=7,  # Pediatric & General Consultation
            pending_customer_name="Mahr Haroon",
            pending_customer_phone="923187538771"
        )
        db.session.add(conv)
        db.session.commit()

        agent = Agent(business_id=1, llm_provider="mock")
        # Step 1: User says 'earliest slot'
        res1 = agent.process_message(conv.id, "earliest slot")
        db.session.refresh(conv)
        self.assertIsNotNone(conv.requested_date)
        self.assertIsNotNone(conv.requested_time)
        self.assertEqual(conv.awaiting_input, "confirmation")
        self.assertIn("earliest available slot", res1.get("content", "").lower())

        # Step 2: User says 'yes'
        res2 = agent.process_message(conv.id, "yes")
        db.session.refresh(conv)
        self.assertEqual(conv.workflow_state, "BOOKED")
        self.assertTrue(any(t.get("name") == "book_appointment" for t in res2.get("executed_tools", [])))
        self.assertIn("confirmed", res2.get("content", "").lower())

    def test_whatsapp_profile_name_sanitization_and_override(self):
        """Verify profile names with tildes and spaces are cleaned and override old test names."""
        import re
        raw_name = "~Mahr Haroon~"
        clean_name = re.sub(r'^[~_\s]+|[~_\s]+$', '', raw_name).strip()
        self.assertEqual(clean_name, "Mahr Haroon")

    def test_full_user_transcript_dr_sara_earliest_slot_flow(self):
        """Simulate the exact 5-step user transcript and verify successful booking on 'yes'."""
        from models import Conversation, Customer
        from ai.agent import Agent

        customer = Customer(
            business_id=1,
            name="Mahr Haroon",
            phone="923187538779"
        )
        db.session.add(customer)
        db.session.commit()

        conv = Conversation(
            business_id=1,
            customer_id=customer.id,
            channel="whatsapp",
            status="AI",
            workflow_state="START",
            pending_customer_name="Mahr Haroon",
            pending_customer_phone="923187538779"
        )
        db.session.add(conv)
        db.session.commit()

        agent = Agent(business_id=1, llm_provider="mock")

        # Turn 1: "HI"
        r1 = agent.process_message(conv.id, "HI")
        self.assertIn("Arfa Dental Clinic", r1.get("content", ""))

        # Turn 2: "DR SARA"
        r2 = agent.process_message(conv.id, "DR SARA")
        db.session.refresh(conv)
        self.assertEqual(conv.selected_doctor_id, 2)
        self.assertIn("Sara Malik", r2.get("content", ""))

        # Turn 3: "consultation"
        r3 = agent.process_message(conv.id, "consultation")
        db.session.refresh(conv)
        self.assertEqual(conv.selected_service_id, 7)

        # Turn 4: "earliest slot"
        r4 = agent.process_message(conv.id, "earliest slot")
        db.session.refresh(conv)
        self.assertIsNotNone(conv.requested_date)
        self.assertIsNotNone(conv.requested_time)
        self.assertEqual(conv.awaiting_input, "confirmation")
        self.assertIn("earliest available slot", r4.get("content", "").lower())
        self.assertIn("reserve this appointment for you", r4.get("content", "").lower())

        # Turn 5: "yes"
        r5 = agent.process_message(conv.id, "yes")
        db.session.refresh(conv)
        self.assertEqual(conv.workflow_state, "BOOKED")
        self.assertIn("confirmed", r5.get("content", "").lower())
        self.assertIn("Mahr Haroon", r5.get("content", ""))
        self.assertIn("Dr. Sara Malik", r5.get("content", ""))

if __name__ == "__main__":
    unittest.main()



