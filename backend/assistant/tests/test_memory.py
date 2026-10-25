from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from assistant.memory import (
    date_blocked_by_preferences,
    delete_preference,
    list_preferences,
    retrieve_relevant_preferences,
    store_preference,
)


class MemoryTests(SimpleTestCase):
    @patch("assistant.memory.supabase_configured", return_value=False)
    @patch("assistant.memory.embed_text", return_value=[0.1] * 8)
    def test_store_preference_simulates_without_supabase(self, _embed, _cfg):
        msg = store_preference("No meetings before 10 AM")
        self.assertIn("Simulated store", msg)

    @patch("assistant.memory.supabase_configured", return_value=True)
    @patch("assistant.memory.embed_text", return_value=[0.1] * 8)
    @patch("assistant.memory.get_supabase_client")
    def test_store_preference_inserts(self, mock_supabase, _embed, _cfg):
        table = MagicMock()
        mock_supabase.return_value.table.return_value = table
        table.insert.return_value.execute.return_value = MagicMock()

        msg = store_preference("Prefer 15-minute buffers")
        self.assertIn("Stored preference", msg)
        table.insert.assert_called_once()

    @patch("assistant.memory.supabase_configured", return_value=True)
    @patch("assistant.memory.get_supabase_client", side_effect=RuntimeError("db down"))
    def test_retrieve_falls_back_on_error(self, _sb, _cfg):
        result = retrieve_relevant_preferences("schedule a meeting")
        self.assertIn("business hours", result.lower())

    def test_retrieve_without_supabase_uses_fallback(self):
        with patch("assistant.memory.supabase_configured", return_value=False):
            result = retrieve_relevant_preferences("anything")
        self.assertIn("15-minute buffer", result)

    @patch("assistant.memory.supabase_configured", return_value=True)
    @patch("assistant.memory.embed_text", return_value=[0.1] * 8)
    @patch("assistant.memory.get_supabase_client")
    def test_retrieve_includes_listed_prefs_when_vector_empty(self, mock_sb, _embed, _cfg):
        client = MagicMock()
        mock_sb.return_value = client
        table = MagicMock()
        client.table.return_value = table
        table.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"content": "No meetings on monday"}]
        )
        client.rpc.return_value.execute.return_value = MagicMock(data=[])

        result = retrieve_relevant_preferences("schedule tomorrow")
        self.assertIn("No meetings on monday", result)

    def test_date_blocked_by_monday_preference(self):
        prefs = "No meetings on monday"
        # 2026-10-26 is a Monday
        reason = date_blocked_by_preferences("2026-10-26", prefs)
        self.assertIsNotNone(reason)
        self.assertIn("You set a preference", reason)
        self.assertIn("No meetings on monday", reason)
        self.assertIn("delete this preference", reason.lower())
        # 2026-10-27 is a Tuesday
        self.assertIsNone(date_blocked_by_preferences("2026-10-27", prefs))

    @patch("assistant.memory.supabase_configured", return_value=True)
    @patch("assistant.memory.get_supabase_client")
    def test_list_preferences(self, mock_sb, _cfg):
        client = MagicMock()
        mock_sb.return_value = client
        table = MagicMock()
        client.table.return_value = table
        table.select.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": 3, "content": "No meetings on monday"}]
        )
        items = list_preferences()
        self.assertEqual(items, [{"id": 3, "content": "No meetings on monday"}])

    @patch("assistant.memory.supabase_configured", return_value=True)
    @patch("assistant.memory.get_supabase_client")
    def test_delete_preference(self, mock_sb, _cfg):
        client = MagicMock()
        mock_sb.return_value = client
        table = MagicMock()
        client.table.return_value = table
        table.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 3, "content": "No meetings on monday"}]
        )
        msg = delete_preference(3)
        self.assertIn("Deleted preference", msg)
        self.assertIn("No meetings on monday", msg)
