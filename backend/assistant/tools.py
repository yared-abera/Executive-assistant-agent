"""Agent tools: Google Calendar + SendGrid (with local simulate fallbacks)."""

from __future__ import annotations

import json
import os
from typing import Optional

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .calendar_service import (
    create_event,
    format_schedule_summary,
    list_events_for_date,
    propose_alternate_slots as find_alternate_slots,
)
from .clients import sendgrid_configured


def check_calendar_conflicts(date_str: str) -> str:
    """Check existing events on the user's calendar for a specific date (YYYY-MM-DD)."""
    try:
        events = list_events_for_date(date_str)
        return format_schedule_summary(date_str, events)
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


def send_email_notification(to_email: str, subject: str, message_body: str) -> str:
    """Dispatches an email notification or follow-up via SendGrid API."""
    if not sendgrid_configured():
        return (
            f"[Simulated Email] To: {to_email} | Subject: {subject} | Content: {message_body}"
        )

    from_email = os.environ.get("SENDGRID_FROM_EMAIL", "assistant@yourdomain.com")
    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        html_content=f"<p>{message_body}</p>",
    )
    try:
        sg = SendGridAPIClient(os.environ["SENDGRID_API_KEY"])
        response = sg.send(message)
        return f"Email sent successfully. Status code: {response.status_code}"
    except Exception as e:
        return f"Email failed: {str(e)}"


def draft_reschedule_email(
    to_email: str,
    original_meeting: str,
    proposed_times: str,
) -> str:
    """Draft (and send if SendGrid configured) a polite reschedule email after a decline."""
    subject = f"Rescheduling: {original_meeting}"
    body = (
        f"Hi,<br/><br/>"
        f"It looks like we need to reschedule <strong>{original_meeting}</strong>. "
        f"Here are a few times that work on our side:<br/>{proposed_times}<br/><br/>"
        f"Please let me know what works best.<br/><br/>Thanks,"
    )
    return send_email_notification(to_email, subject, body)
