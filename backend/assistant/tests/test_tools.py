from django.test import SimpleTestCase, override_settings
from unittest.mock import MagicMock, patch

from assistant.tools import (
    book_calendar_meeting,
    check_calendar_conflicts,
    propose_alternate_slots,
    send_email_notification,
)


class ToolsTests(SimpleTestCase):
    @patch("assistant.calendar_service.google_calendar_configured", return_value=False)
    def test_check_calendar_conflicts_mock_mode(self, _cfg):
        summary = check_calendar_conflicts("2026-10-26")  # Monday
        self.assertIn("2026-10-26", summary)
        self.assertIn("Team Sync", summary)

    @patch("assistant.calendar_service.google_calendar_configured", return_value=False)
    def test_book_calendar_meeting_mock_mode(self, _cfg):
        result = book_calendar_meeting(
            title="Sync with David",
            date_str="2026-10-24",
            time_str="11:30",
            duration_minutes=30,
        )
        self.assertIn("Simulated booking", result)
        self.assertIn("Sync with David", result)

    @patch("assistant.calendar_service.google_calendar_configured", return_value=False)
    def test_propose_alternate_slots_returns_open_windows(self, _cfg):
        result = propose_alternate_slots("2026-10-26", duration_minutes=30, earliest_hour=10)
        self.assertIn("Open slots", result)

    def test_send_email_simulated_without_key(self):
        with patch.dict("os.environ", {"SENDGRID_API_KEY": ""}, clear=False):
            # Force sendgrid_configured false via empty key
            with patch("assistant.tools.sendgrid_configured", return_value=False):
                result = send_email_notification(
                    "a@b.com", "Hello", "Body text"
                )
        self.assertIn("[Simulated Email]", result)
        self.assertIn("a@b.com", result)

    @patch("assistant.tools.SendGridAPIClient")
    def test_send_email_real_path_mocked(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.send.return_value.status_code = 202
        mock_client_cls.return_value = mock_client

        with patch("assistant.tools.sendgrid_configured", return_value=True):
            with patch.dict(
                "os.environ",
                {
                    "SENDGRID_API_KEY": "SG.fake",
                    "SENDGRID_FROM_EMAIL": "assistant@example.com",
                },
            ):
                result = send_email_notification("a@b.com", "Hi", "Body")

        self.assertIn("Email sent successfully", result)
        mock_client.send.assert_called_once()
