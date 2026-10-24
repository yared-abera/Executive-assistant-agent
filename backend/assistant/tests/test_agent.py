from unittest.mock import MagicMock, patch

from django.test import TestCase

from assistant.agent import run_executive_agent
from assistant.models import PendingAction


class _FakeCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class AgentTests(TestCase):
    @patch("assistant.agent.retrieve_relevant_preferences", return_value="No meetings before 10 AM")
    @patch("assistant.agent.get_gemini_client")
    def test_multi_tool_batch_and_contract(self, mock_client_factory, _prefs):
        chat = MagicMock()
        client = MagicMock()
        client.chats.create.return_value = chat
        mock_client_factory.return_value = client

        first = MagicMock()
        first.function_calls = [
            _FakeCall("check_calendar_conflicts", {"date_str": "2026-10-26"}),
            _FakeCall(
                "propose_alternate_slots",
                {"date_str": "2026-10-26", "duration_minutes": 30},
            ),
        ]
        first.text = None

        second = MagicMock()
        second.function_calls = None
        second.text = "I can book 11:00 AM instead."

        chat.send_message.side_effect = [first, second]

        with patch(
            "assistant.agent.check_calendar_conflicts",
            return_value="Schedule for 2026-10-26: busy at 10",
        ), patch(
            "assistant.agent.propose_alternate_slots",
            return_value="Open slots on 2026-10-26 (30 min):\n- 11:00 AM (start 11:00)",
        ):
            result = run_executive_agent(
                "Schedule a 30 min sync on 2026-10-26 at 10:00 AM"
            )

        self.assertIsNone(result.get("error"))
        self.assertIn("final_response", result)
        self.assertIn("logs", result)
        self.assertIn("pending_actions", result)
        self.assertTrue(any(e["type"] == "action" for e in result["logs"]))
        self.assertTrue(any(e["type"] == "observation" for e in result["logs"]))
        self.assertTrue(any(e["type"] == "final_answer" for e in result["logs"]))
        # Balance check: UI dashboard data, not only chat text
        self.assertIsInstance(result["pending_actions"], list)
        self.assertGreaterEqual(len(result["pending_actions"]), 1)
        self.assertEqual(PendingAction.objects.count(), 1)

        # Multi-tool: second send_message should receive a list of parts
        self.assertEqual(chat.send_message.call_count, 2)
        batched = chat.send_message.call_args_list[1].args[0]
        self.assertIsInstance(batched, list)
        self.assertEqual(len(batched), 2)

    @patch("assistant.agent.get_gemini_client", side_effect=Exception("quota"))
    @patch("assistant.agent.retrieve_relevant_preferences", return_value="rules")
    def test_agent_returns_structured_error(self, _prefs, _client):
        result = run_executive_agent("hello")
        self.assertIn("error", result)
        self.assertIsNone(result["final_response"])
        self.assertIn("logs", result)
