"""Agent tools: Google Calendar + Resend email (with local simulate fallbacks)."""

# Do not use postponed annotations here — google-genai AFC uses isinstance() on
# runtime type hints; stringified annotations raise TypeError on Python 3.14+.
import json
import os

from .calendar_service import (
    create_event,
    format_schedule_summary,
    list_events_for_date,
    propose_alternate_slots as find_alternate_slots,
)
from .clients import resend_configured
from .memory import date_blocked_by_preferences, retrieve_relevant_preferences


def check_calendar_conflicts(date_str: str) -> str:
    """Check existing events on the user's calendar for a specific date (YYYY-MM-DD)."""
    try:
        prefs = retrieve_relevant_preferences(f"schedule on {date_str}")
        blocked = date_blocked_by_preferences(date_str, prefs)
        events = list_events_for_date(date_str)
        summary = format_schedule_summary(date_str, events)
        if blocked:
            return f"{summary}\n{blocked}"
        return summary
    except Exception as exc:
        return f"Calendar check failed for {date_str}: {exc}"


def book_calendar_meeting(
    title: str,
    date_str: str,
    time_str: str,
    duration_minutes: int,
    attendee_email: str = "",
) -> str:
    """Books a meeting on the calendar at the given date, time, and duration.

    Args:
        title: Meeting title.
        date_str: Date in YYYY-MM-DD.
        time_str: Start time like '11:30' or '11:30 AM'.
        duration_minutes: Length of the meeting.
        attendee_email: Optional attendee email to invite.
    """
    try:
        prefs = retrieve_relevant_preferences(f"book meeting {title} on {date_str}")
        blocked = date_blocked_by_preferences(date_str, prefs)
        if blocked:
            return f"Booking refused. {blocked}"
        result = create_event(
            title=title,
            date_str=date_str,
            time_str=time_str,
            duration_minutes=duration_minutes,
            attendee_email=attendee_email or None,
        )
        return result.get("message") or json.dumps(result)
    except Exception as exc:
        return f"Booking failed: {exc}"


def propose_alternate_slots(
    date_str: str,
    duration_minutes: int = 30,
    earliest_hour: int = 10,
    latest_hour: int = 17,
) -> str:
    """Propose open meeting slots on a date, respecting busy blocks and business hours.

    Prefer earliest_hour=10 when the executive dislikes early meetings.
    """
    try:
        prefs = retrieve_relevant_preferences(f"open slots on {date_str}")
        blocked = date_blocked_by_preferences(date_str, prefs)
        if blocked:
            return (
                f"No slots offered on {date_str}. {blocked} "
                "Propose times on the next allowed weekday instead."
            )
        slots = find_alternate_slots(
            date_str=date_str,
            duration_minutes=duration_minutes,
            earliest_hour=earliest_hour,
            latest_hour=latest_hour,
        )
        if not slots:
            return f"No open slots found on {date_str} between {earliest_hour}:00 and {latest_hour}:00."
        lines = [f"Open slots on {date_str} ({duration_minutes} min):"]
        for slot in slots:
            lines.append(f"- {slot['label']} (start {slot['start']})")
        return "\n".join(lines)
    except Exception as exc:
        return f"Could not propose slots: {exc}"


def _simulated_email(to_email: str, subject: str, message_body: str, reason: str = "") -> str:
    note = f" ({reason})" if reason else ""
    return (
        f"[Simulated Email]{note} To: {to_email} | Subject: {subject} | Content: {message_body}"
    )


def _is_resend_domain_block(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "domain is not verified",
            "only send testing emails",
            "verify a domain",
            "resend.com/domains",
        )
    )


def send_email_notification(to_email: str, subject: str, message_body: str) -> str:
    """Dispatches an email notification or follow-up via Resend API.

    Falls back to a simulated send when Resend rejects unverified domains /
    test-sender limits so demos stay usable without a paid custom domain.
    """
    if not resend_configured():
        return _simulated_email(to_email, subject, message_body, "RESEND_API_KEY unset")

    force_sim = (os.environ.get("EMAIL_MODE") or "").strip().lower() == "simulate"
    if force_sim:
        return _simulated_email(to_email, subject, message_body, "EMAIL_MODE=simulate")

    import resend

    from_email = (os.environ.get("RESEND_FROM_EMAIL") or "beth.t@example.com").strip().strip('"').strip("'")
    resend.api_key = os.environ["RESEND_API_KEY"].strip().strip('"').strip("'")
    try:
        result = resend.Emails.send(
            {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "html": f"<p>{message_body}</p>",
            }
        )
        email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
        return f"Email sent successfully via Resend. Id: {email_id}"
    except Exception as e:
        if _is_resend_domain_block(e):
            return _simulated_email(
                to_email,
                subject,
                message_body,
                "Resend blocked send — verify your own domain or use EMAIL_MODE=simulate; "
                f"raw error: {e}",
            )
        return f"Email failed: {str(e)}"


def draft_reschedule_email(
    to_email: str,
    original_meeting: str,
    proposed_times: str,
) -> str:
    """Draft (and send if Resend configured) a polite reschedule email after a decline."""
    subject = f"Rescheduling: {original_meeting}"
    body = (
        f"Hi,<br/><br/>"
        f"It looks like we need to reschedule <strong>{original_meeting}</strong>. "
        f"Here are a few times that work on our side:<br/>{proposed_times}<br/><br/>"
        f"Please let me know what works best.<br/><br/>Thanks,"
    )
    return send_email_notification(to_email, subject, body)
