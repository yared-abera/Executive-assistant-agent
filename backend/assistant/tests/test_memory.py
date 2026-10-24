from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from assistant.memory import retrieve_relevant_preferences, store_preference


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
    @patch("assistant.memory.embed_text", side_effect=RuntimeError("boom"))
    def test_retrieve_falls_back_on_error(self, _embed, _cfg):
        result = retrieve_relevant_preferences("schedule a meeting")
        self.assertIn("business hours", result.lower())

    def test_retrieve_without_supabase_uses_fallback(self):
        with patch("assistant.memory.supabase_configured", return_value=False):
            result = retrieve_relevant_preferences("anything")
        self.assertIn("15-minute buffer", result)
