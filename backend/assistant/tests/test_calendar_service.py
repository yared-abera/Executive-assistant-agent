from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from assistant import calendar_service as cal


class CalendarServiceTests(SimpleTestCase):
    def tearDown(self):
        cal._cached_creds = None
        cal._last_fetch_degraded = False
        cal._circuit_open_until = 0.0

    @patch.object(cal, "use_google_calendar", return_value=True)
    @patch.object(cal, "_list_google_events_for_date")
    def test_list_falls_back_on_timeout(self, mock_list, _cfg):
        mock_list.side_effect = ConnectionError(
            "HTTPSConnectionPool(host='oauth2.googleapis.com', port=443): "
            "Max retries exceeded with url: /token "
            "(Caused by ConnectTimeoutError(, 'Connection timed out'))"
        )
        events = cal.list_events_for_date("2026-10-26")  # Monday
        self.assertTrue(cal.last_fetch_was_degraded())
        self.assertTrue(events)
        self.assertTrue(all(e.get("source") == "mock-fallback" for e in events))
        self.assertIn("Team Sync", cal.format_schedule_summary("2026-10-26", events))
        self.assertIn("unreachable", cal.format_schedule_summary("2026-10-26", events).lower())

    @patch.object(cal, "use_google_calendar", return_value=True)
    @patch.object(cal, "_list_google_events_for_date")
    def test_list_rethrows_non_network_errors(self, mock_list, _cfg):
        mock_list.side_effect = ValueError("bad calendar id")
        with self.assertRaises(ValueError):
            cal.list_events_for_date("2026-10-26")
        self.assertFalse(cal.last_fetch_was_degraded())

    @patch.object(cal, "_list_google_events_for_date")
    @patch.dict("os.environ", {"CALENDAR_MODE": "mock"}, clear=False)
    def test_calendar_mode_mock_skips_google(self, mock_list):
        # Credentials may be present; mock mode must not call Google.
        events = cal.list_events_for_date("2026-10-26")
        mock_list.assert_not_called()
        self.assertTrue(events)
        self.assertTrue(all(e.get("source") == "mock" for e in events))
        self.assertFalse(cal.last_fetch_was_degraded())

    @patch.dict(
        "os.environ",
        {"EXECUTIVE_TIMEZONE": "Africa/Addis_Ababa"},
        clear=False,
    )
    @patch.object(cal, "executive_now")
    def test_executive_clock_helpers(self, mock_now):
        mock_now.return_value = datetime(
            2026, 10, 25, 14, 30, tzinfo=ZoneInfo("Africa/Addis_Ababa")
        )
        self.assertEqual(cal.executive_today_iso(), "2026-10-25")
        self.assertEqual(cal.executive_tomorrow_iso(), "2026-10-26")
        ctx = cal.executive_clock_context()
        self.assertEqual(ctx["today"], "2026-10-25")
        self.assertEqual(ctx["tomorrow"], "2026-10-26")
        self.assertEqual(ctx["local_time"], "14:30")
        self.assertEqual(ctx["weekday"], "Sunday")
        self.assertIn("Addis_Ababa", ctx["timezone"])
