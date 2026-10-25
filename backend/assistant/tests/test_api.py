from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from assistant.models import PendingAction


class ApiContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_command_requires_body(self):
        res = self.client.post("/api/agent/command/", {}, format="json")
        self.assertEqual(res.status_code, 400)
        self.assertIn("error", res.data)

    @patch("assistant.views.run_executive_agent")
    def test_command_success_includes_logs_and_pending(self, mock_agent):
        mock_agent.return_value = {
            "final_response": "Booked.",
            "logs": [
                {"type": "thought", "detail": "rules"},
                {"type": "final_answer", "detail": "Booked."},
            ],
            "pending_actions": [{"id": 1, "title": "Approve"}],
        }
        res = self.client.post(
            "/api/agent/command/",
            {"command": "schedule sync"},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("logs", res.data)
        self.assertIn("pending_actions", res.data)
        self.assertTrue(res.data["logs"])
        self.assertTrue(res.data["pending_actions"])

    @patch("assistant.views.run_executive_agent")
    def test_command_agent_error_is_json(self, mock_agent):
        mock_agent.return_value = {
            "error": "GEMINI_API_KEY missing",
            "final_response": None,
            "logs": [],
            "pending_actions": [],
        }
        res = self.client.post(
            "/api/agent/command/",
            {"command": "hi"},
            format="json",
        )
        self.assertEqual(res.status_code, 502)
        self.assertIn("error", res.data)

    def test_preference_requires_body(self):
        res = self.client.post("/api/agent/preference/", {}, format="json")
        self.assertEqual(res.status_code, 400)

    @patch("assistant.views.store_preference", return_value="Stored preference: 'x'")
    def test_preference_created(self, _store):
        res = self.client.post(
            "/api/agent/preference/",
            {"preference": "No meetings before 10 AM"},
            format="json",
        )
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "success")
        self.assertEqual(res.data["preference"], "No meetings before 10 AM")

    @patch(
        "assistant.views.list_preferences",
        return_value=[{"id": 3, "content": "No meetings on monday"}],
    )
    def test_preference_list(self, _list):
        res = self.client.get("/api/agent/preferences/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["items"]), 1)
        self.assertEqual(res.data["items"][0]["id"], 3)

    @patch(
        "assistant.views.delete_preference",
        return_value="Deleted preference: 'No meetings on monday'",
    )
    def test_preference_delete(self, _delete):
        res = self.client.delete("/api/agent/preference/3/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "success")
        _delete.assert_called_once_with(3)

    @patch("assistant.views.delete_preference", side_effect=ValueError("Preference id=9 not found"))
    def test_preference_delete_not_found(self, _delete):
        res = self.client.delete("/api/agent/preference/9/")
        self.assertEqual(res.status_code, 404)

    def test_calendar_events(self):
        res = self.client.get("/api/calendar/events/?date=2026-10-26")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["date"], "2026-10-26")
        self.assertIn("events", res.data)

    def test_pending_list_approve_reject(self):
        action = PendingAction.objects.create(
            action_type=PendingAction.ActionType.BOOK_MEETING,
            title="Book sync",
            summary="Approve booking",
            payload={
                "title": "Sync",
                "date_str": "2026-10-27",
                "time_str": "11:00",
                "duration_minutes": 30,
            },
        )
        listed = self.client.get("/api/agent/pending/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data["items"]), 1)

        approved = self.client.post(f"/api/agent/pending/{action.id}/approve/")
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(approved.data["status"], PendingAction.Status.EXECUTED)

        action2 = PendingAction.objects.create(
            action_type=PendingAction.ActionType.SEND_EMAIL,
            title="Email",
            summary="Draft",
            payload={
                "to_email": "a@b.com",
                "subject": "Hi",
                "message_body": "Hello",
            },
        )
        rejected = self.client.post(f"/api/agent/pending/{action2.id}/reject/")
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.data["status"], PendingAction.Status.REJECTED)

    def test_calendar_webhook_creates_pending(self):
        with patch.dict("os.environ", {"CALENDAR_WEBHOOK_TOKEN": "tok"}):
            res = self.client.post(
                "/api/webhooks/google-calendar/",
                {
                    "token": "tok",
                    "summary": "Client Call",
                    "attendee_email": "david@example.com",
                    "proposed_times": "11:00 AM",
                },
                format="json",
            )
        self.assertEqual(res.status_code, 202)
        self.assertEqual(PendingAction.objects.count(), 1)
        self.assertEqual(
            PendingAction.objects.first().action_type,
            PendingAction.ActionType.RESCHEDULE,
        )

    def test_daily_briefing_job(self):
        with patch.dict("os.environ", {"SCHEDULER_SECRET": "secret"}):
            res = self.client.post(
                "/api/jobs/daily-briefing/",
                {"to_email": "exec@example.com"},
                format="json",
                HTTP_X_SCHEDULER_SECRET="secret",
            )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["status"], "ok")
        self.assertIn("events", res.data)
