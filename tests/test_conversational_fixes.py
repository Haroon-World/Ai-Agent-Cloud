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

if __name__ == "__main__":
    unittest.main()
