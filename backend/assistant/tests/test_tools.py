from django.test import SimpleTestCase
from unittest.mock import MagicMock, patch

from assistant.tools import (
    book_calendar_meeting,
    check_calendar_conflicts,
    propose_alternate_slots,
    send_email_notification,
)


class ToolsTests(SimpleTestCase):
    @patch("assistant.tools.retrieve_relevant_preferences", return_value="No special preferences found.")
    @patch("assistant.calendar_service.use_google_calendar", return_value=False)
    def test_check_calendar_conflicts_mock_mode(self, _cfg, _prefs):
        summary = check_calendar_conflicts("2026-10-26")  # Monday
        self.assertIn("2026-10-26", summary)
        self.assertIn("Team Sync", summary)

    @patch("assistant.tools.retrieve_relevant_preferences", return_value="No special preferences found.")
    @patch("assistant.calendar_service.use_google_calendar", return_value=False)
    def test_book_calendar_meeting_mock_mode(self, _cfg, _prefs):
        result = book_calendar_meeting(
            title="Sync with David",
            date_str="2026-10-24",
            time_str="11:30",
            duration_minutes=30,
        )
        self.assertIn("Simulated booking", result)
        self.assertIn("Sync with David", result)

    @patch(
        "assistant.tools.retrieve_relevant_preferences",
        return_value="No meetings on monday",
    )
    def test_book_refuses_monday_when_preference_set(self, _prefs):
        result = book_calendar_meeting(
            title="Sync",
            date_str="2026-10-26",  # Monday
            time_str="11:30",
            duration_minutes=30,
        )
        self.assertIn("Booking refused", result)
        self.assertIn("You set a preference", result)
        self.assertIn("monday", result.lower())
        self.assertIn("delete this preference", result.lower())

    @patch("assistant.tools.retrieve_relevant_preferences", return_value="No special preferences found.")
    @patch("assistant.calendar_service.use_google_calendar", return_value=False)
    def test_propose_alternate_slots_returns_open_windows(self, _cfg, _prefs):
        result = propose_alternate_slots("2026-10-26", duration_minutes=30, earliest_hour=10)
        self.assertIn("Open slots", result)

    def test_send_email_simulated_without_key(self):
        with patch("assistant.tools.resend_configured", return_value=False):
            result = send_email_notification("a@b.com", "Hello", "Body text")
        self.assertIn("[Simulated Email]", result)
        self.assertIn("a@b.com", result)

    @patch("assistant.tools.resend_configured", return_value=True)
    def test_send_email_real_path_mocked(self, _cfg):
        mock_module = MagicMock()
        mock_module.Emails.send.return_value = {"id": "email_123"}

        with patch.dict("sys.modules", {"resend": mock_module}):
            with patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_fake",
                    "RESEND_FROM_EMAIL": "beth.t@example.com",
                    "EMAIL_MODE": "",
                },
                clear=False,
            ):
                result = send_email_notification("a@b.com", "Hi", "Body")

        self.assertIn("Email sent successfully", result)
        self.assertIn("email_123", result)
        mock_module.Emails.send.assert_called_once()

    @patch("assistant.tools.resend_configured", return_value=True)
    def test_send_email_falls_back_on_domain_block(self, _cfg):
        mock_module = MagicMock()
        mock_module.Emails.send.side_effect = Exception(
            "The example.com domain is not verified. Please, add and verify your domain "
            "on https://resend.com/domains"
        )

        with patch.dict("sys.modules", {"resend": mock_module}):
            with patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_fake",
                    "RESEND_FROM_EMAIL": "beth.t@example.com",
                    "EMAIL_MODE": "",
                },
                clear=False,
            ):
                result = send_email_notification("yaredoabera7@gmail.com", "Hi", "Body")

        self.assertIn("[Simulated Email]", result)
        self.assertIn("yaredoabera7@gmail.com", result)
        self.assertNotIn("Email failed", result)

    @patch("assistant.tools.resend_configured", return_value=True)
    def test_send_email_mode_simulate(self, _cfg):
        with patch.dict("os.environ", {"EMAIL_MODE": "simulate"}, clear=False):
            result = send_email_notification("a@b.com", "Hello", "Body")
        self.assertIn("[Simulated Email]", result)
        self.assertIn("EMAIL_MODE=simulate", result)
