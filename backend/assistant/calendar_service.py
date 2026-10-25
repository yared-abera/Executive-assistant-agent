"""Google Calendar access with OAuth refresh token, mock fallback when unset."""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .clients import use_google_calendar

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
# Keep Google HTTP calls short so a flaky path fails fast instead of hanging ~120s.
GOOGLE_HTTP_TIMEOUT_SEC = float(os.environ.get("GOOGLE_HTTP_TIMEOUT_SEC", "8"))
# After a timeout, skip Google for a bit so the agent/UI stay responsive.
GOOGLE_CIRCUIT_COOLDOWN_SEC = float(os.environ.get("GOOGLE_CIRCUIT_COOLDOWN_SEC", "300"))

_creds_lock = threading.Lock()
_cached_creds = None  # google.oauth2.credentials.Credentials | None
_last_fetch_degraded = False
_circuit_open_until = 0.0

# Deterministic mock schedule used when OAuth credentials are absent (local/demo/tests).
MOCK_EVENTS_BY_WEEKDAY = {
    0: [  # Monday
        {"summary": "Team Sync", "start": "10:00", "end": "11:00"},
        {"summary": "Product Review", "start": "14:00", "end": "15:00"},
    ],
    1: [
        {"summary": "Leadership Standup", "start": "09:30", "end": "10:00"},
    ],
    2: [
        {"summary": "Design Critique", "start": "11:00", "end": "12:00"},
        {"summary": "Client Call", "start": "15:00", "end": "15:45"},
    ],
    3: [
        {"summary": "1:1 with Direct Report", "start": "13:00", "end": "13:30"},
    ],
    4: [
        {"summary": "Weekly Planning", "start": "10:00", "end": "11:00"},
    ],
}


def _timezone() -> ZoneInfo:
    tz_name = os.environ.get("EXECUTIVE_TIMEZONE", "UTC")
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def executive_timezone_name() -> str:
    return str(_timezone())


def executive_now() -> datetime:
    """Current instant in EXECUTIVE_TIMEZONE."""
    return datetime.now(_timezone())


def executive_today_iso() -> str:
    return executive_now().date().isoformat()


def executive_tomorrow_iso() -> str:
    return (executive_now().date() + timedelta(days=1)).isoformat()


def executive_clock_context() -> Dict[str, str]:
    """Timezone-aware clock snapshot for the agent system prompt."""
    now = executive_now()
    return {
        "timezone": executive_timezone_name(),
        "today": now.date().isoformat(),
        "tomorrow": (now.date() + timedelta(days=1)).isoformat(),
        "local_time": now.strftime("%H:%M"),
        "weekday": now.strftime("%A"),
    }


def _calendar_id() -> str:
    return os.environ.get("GOOGLE_CALENDAR_ID", "primary")


def _timed_auth_request():
    """google-auth Request that always uses a bounded HTTP timeout."""
    from google.auth.transport.requests import Request

    class TimedRequest(Request):
        def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs):
            return super().__call__(
                url,
                method=method,
                body=body,
                headers=headers,
                timeout=timeout if timeout is not None else GOOGLE_HTTP_TIMEOUT_SEC,
                **kwargs,
            )

    return TimedRequest()


def _is_transient_network_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    text = str(exc).lower()
    markers = (
        "timed out",
        "timeout",
        "max retries exceeded",
        "connection reset",
        "temporarily unavailable",
        "name or service not known",
        "failed to establish a new connection",
        "connecttimeout",
        "readtimeout",
    )
    if any(m in text for m in markers):
        return True
    if name in {
        "ConnectTimeoutError",
        "ReadTimeoutError",
        "ConnectTimeout",
        "ReadTimeout",
        "ConnectionError",
        "TimeoutError",
        "SSLError",
    }:
        return True
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    return bool(cause) and _is_transient_network_error(cause)


def _get_credentials():
    """Return cached OAuth credentials; refresh only when expired/missing."""
    global _cached_creds
    from google.oauth2.credentials import Credentials

    with _creds_lock:
        if _cached_creds is not None and _cached_creds.valid:
            return _cached_creds

        if _cached_creds is None:
            _cached_creds = Credentials(
                token=None,
                refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=os.environ["GOOGLE_CLIENT_ID"],
                client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
                scopes=SCOPES,
            )

        if not _cached_creds.valid:
            _cached_creds.refresh(_timed_auth_request())
        return _cached_creds


def get_calendar_service():
    from googleapiclient.discovery import build

    try:
        import google_auth_httplib2
        import httplib2

        creds = _get_credentials()
        http = httplib2.Http(timeout=GOOGLE_HTTP_TIMEOUT_SEC)
        authed_http = google_auth_httplib2.AuthorizedHttp(creds, http=http)
        return build("calendar", "v3", http=authed_http, cache_discovery=False)
    except ImportError:
        # Fallback if google_auth_httplib2 is unavailable — still reuse cached token.
        from googleapiclient.discovery import build as build_svc

        return build_svc(
            "calendar",
            "v3",
            credentials=_get_credentials(),
            cache_discovery=False,
        )


def _parse_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=_timezone())


def _mock_events_for_date(date_str: str) -> List[Dict[str, Any]]:
    day = _parse_date(date_str)
    templates = MOCK_EVENTS_BY_WEEKDAY.get(day.weekday(), [])
    events = []
    for item in templates:
        start_h, start_m = map(int, item["start"].split(":"))
        end_h, end_m = map(int, item["end"].split(":"))
        start_dt = day.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        end_dt = day.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        events.append(
            {
                "id": f"mock-{date_str}-{item['summary']}",
                "summary": item["summary"],
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "attendees": [],
                "status": "confirmed",
                "source": "mock",
            }
        )
    return events


def _list_google_events_for_date(date_str: str) -> List[Dict[str, Any]]:
    day_start = _parse_date(date_str)
    day_end = day_start + timedelta(days=1)
    service = get_calendar_service()
    result = (
        service.events()
        .list(
            calendarId=_calendar_id(),
            timeMin=day_start.isoformat(),
            timeMax=day_end.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = []
    for item in result.get("items", []):
        start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
        end = item.get("end", {}).get("dateTime") or item.get("end", {}).get("date")
        attendees = [
            a.get("email")
            for a in item.get("attendees", [])
            if a.get("email")
        ]
        events.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary", "(No title)"),
                "start": start,
                "end": end,
                "attendees": attendees,
                "status": item.get("status", "confirmed"),
                "source": "google",
            }
        )
    return events


def _mock_fallback_events(date_str: str) -> List[Dict[str, Any]]:
    global _last_fetch_degraded
    _last_fetch_degraded = True
    events = _mock_events_for_date(date_str)
    for ev in events:
        ev["source"] = "mock-fallback"
    return events


def _trip_circuit() -> None:
    global _circuit_open_until
    _circuit_open_until = time.monotonic() + GOOGLE_CIRCUIT_COOLDOWN_SEC


def _circuit_is_open() -> bool:
    return time.monotonic() < _circuit_open_until


def list_events_for_date(date_str: str) -> List[Dict[str, Any]]:
    """Return normalized events for YYYY-MM-DD.

    Uses Google when configured. On transient network/timeout errors, falls back
    to the local mock schedule so the UI and agent stay usable on flaky links.
    """
    global _last_fetch_degraded
    _last_fetch_degraded = False

    if not use_google_calendar():
        return _mock_events_for_date(date_str)

    if _circuit_is_open():
        logger.info(
            "Google Calendar circuit open; using mock schedule for %s", date_str
        )
        return _mock_fallback_events(date_str)

    try:
        return _list_google_events_for_date(date_str)
    except Exception as exc:
        if _is_transient_network_error(exc):
            logger.warning(
                "Google Calendar unreachable (%s); using mock schedule for %s",
                exc,
                date_str,
            )
            _trip_circuit()
            return _mock_fallback_events(date_str)
        raise


def last_fetch_was_degraded() -> bool:
    """True when the most recent list_events_for_date used mock-fallback."""
    return _last_fetch_degraded


def create_event(
    title: str,
    date_str: str,
    time_str: str,
    duration_minutes: int,
    attendee_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a calendar event. time_str examples: '11:30', '11:30 AM'."""
    start_dt = _combine_date_time(date_str, time_str)
    end_dt = start_dt + timedelta(minutes=int(duration_minutes))

    if not use_google_calendar():
        return {
            "id": f"mock-created-{date_str}-{time_str}",
            "summary": title,
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "htmlLink": None,
            "source": "mock",
            "message": (
                f"[Simulated booking] '{title}' on {date_str} at {time_str} "
                f"({duration_minutes} mins). Set CALENDAR_MODE=google (with GOOGLE_* "
                f"env vars) for real Calendar."
            ),
        }

    body: Dict[str, Any] = {
        "summary": title,
        "start": {"dateTime": start_dt.isoformat(), "timeZone": str(_timezone())},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": str(_timezone())},
    }
    if attendee_email:
        body["attendees"] = [{"email": attendee_email}]

    if _circuit_is_open():
        raise RuntimeError(
            "Google Calendar is temporarily unreachable (circuit open after timeout). "
            "Retry in a minute, or clear GOOGLE_* env vars to use mock bookings."
        )

    try:
        service = get_calendar_service()
        created = (
            service.events()
            .insert(
                calendarId=_calendar_id(),
                body=body,
                sendUpdates="all" if attendee_email else "none",
            )
            .execute()
        )
    except Exception as exc:
        if _is_transient_network_error(exc):
            _trip_circuit()
            raise RuntimeError(
                "Google Calendar is temporarily unreachable (network timeout). "
                "Retry shortly, or clear GOOGLE_* env vars to use mock bookings."
            ) from exc
        raise

    return {
        "id": created.get("id"),
        "summary": created.get("summary"),
        "start": created.get("start", {}).get("dateTime"),
        "end": created.get("end", {}).get("dateTime"),
        "htmlLink": created.get("htmlLink"),
        "source": "google",
        "message": f"Created calendar event '{title}' on {date_str} at {time_str}.",
    }


def propose_alternate_slots(
    date_str: str,
    duration_minutes: int = 30,
    earliest_hour: int = 10,
    latest_hour: int = 17,
    max_slots: int = 3,
) -> List[Dict[str, str]]:
    """Find open windows on the day respecting simple business hours."""
    events = list_events_for_date(date_str)
    day = _parse_date(date_str)
    busy = []
    for ev in events:
        try:
            start = datetime.fromisoformat(ev["start"])
            end = datetime.fromisoformat(ev["end"])
            if start.tzinfo is None:
                start = start.replace(tzinfo=_timezone())
            if end.tzinfo is None:
                end = end.replace(tzinfo=_timezone())
            busy.append((start, end))
        except Exception:
            continue
    busy.sort(key=lambda x: x[0])

    cursor = day.replace(hour=earliest_hour, minute=0, second=0, microsecond=0)
    day_end = day.replace(hour=latest_hour, minute=0, second=0, microsecond=0)
    duration = timedelta(minutes=int(duration_minutes))
    proposals = []

    while cursor + duration <= day_end and len(proposals) < max_slots:
        slot_end = cursor + duration
        conflict = any(not (slot_end <= b_start or cursor >= b_end) for b_start, b_end in busy)
        if not conflict:
            proposals.append(
                {
                    "date": date_str,
                    "start": cursor.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "label": f"{cursor.strftime('%I:%M %p').lstrip('0')} – {slot_end.strftime('%I:%M %p').lstrip('0')}",
                }
            )
            cursor = slot_end + timedelta(minutes=15)
        else:
            # Jump to end of overlapping busy block
            overlapping_ends = [b_end for b_start, b_end in busy if not (slot_end <= b_start or cursor >= b_end)]
            cursor = max(overlapping_ends) if overlapping_ends else cursor + timedelta(minutes=15)

    return proposals


def _combine_date_time(date_str: str, time_str: str) -> datetime:
    cleaned = time_str.strip().upper().replace(".", "")
    day = _parse_date(date_str)
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return day.replace(
                hour=parsed.hour,
                minute=parsed.minute,
                second=0,
                microsecond=0,
            )
        except ValueError:
            continue
    raise ValueError(f"Unrecognized time format: {time_str}")


def format_schedule_summary(date_str: str, events: List[Dict[str, Any]]) -> str:
    degraded = _last_fetch_degraded or any(
        ev.get("source") == "mock-fallback" for ev in events
    )
    if not events:
        base = f"Schedule for {date_str}: no events. All slots open."
        if degraded:
            return (
                base
                + " (Google Calendar was unreachable; showing empty local fallback.)"
            )
        return base
    lines = [f"Schedule for {date_str}:"]
    if degraded:
        lines.append(
            "(Google Calendar unreachable — showing local mock schedule until connectivity returns.)"
        )
    for ev in events:
        try:
            start = datetime.fromisoformat(ev["start"]).strftime("%I:%M %p").lstrip("0")
            end = datetime.fromisoformat(ev["end"]).strftime("%I:%M %p").lstrip("0")
            lines.append(f"- {start} – {end}: {ev['summary']}")
        except Exception:
            lines.append(f"- {ev.get('start')} – {ev.get('end')}: {ev.get('summary')}")
    lines.append("Remaining daytime slots may be open; call propose_alternate_slots for suggestions.")
    return "\n".join(lines)
