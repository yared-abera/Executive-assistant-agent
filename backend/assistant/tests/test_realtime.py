from unittest.mock import patch

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from assistant.agent import run_executive_agent
from assistant.models import PendingAction


class RealtimeEmitTests(SimpleTestCase):
    @patch("assistant.realtime.emit_sync")
    def test_broadcast_pending_emits_notification(self, mock_emit):
        from assistant.realtime import broadcast_pending_action

        item = {"id": 1, "title": "Approve", "summary": "Book at 11:00"}
        broadcast_pending_action(item)
        events = [c.args[0] for c in mock_emit.call_args_list]
        self.assertIn("pending_action", events)
        self.assertIn("notification", events)

    @patch("assistant.agent.get_gemini_client", side_effect=Exception("no key"))
    @patch("assistant.agent.retrieve_relevant_preferences", return_value="rules")
    def test_agent_on_log_callback(self, _prefs, _client):
        seen = []
        result = run_executive_agent("hello", on_log=seen.append)
        self.assertTrue(result.get("error"))
        self.assertTrue(seen)
        self.assertEqual(seen[-1]["type"], "thought")


class WebhookRealtimeTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_webhook_broadcasts_pending(self):
        with patch("assistant.realtime.broadcast_pending_action") as mock_rt:
            with patch.dict("os.environ", {"CALENDAR_WEBHOOK_TOKEN": "tok"}):
                res = self.client.post(
                    "/api/webhooks/google-calendar/",
                    {
                        "token": "tok",
                        "summary": "Sync",
                        "attendee_email": "a@b.com",
                    },
                    format="json",
                )
            self.assertEqual(res.status_code, 202)
            self.assertEqual(PendingAction.objects.count(), 1)
            mock_rt.assert_called_once()
