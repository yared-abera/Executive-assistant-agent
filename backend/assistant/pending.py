"""Create and execute pending approval actions for the UI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import PendingAction
from .tools import book_calendar_meeting, draft_reschedule_email, send_email_notification


def create_pending_action(
    action_type: str,
    title: str,
    summary: str,
    payload: Optional[Dict[str, Any]] = None,
) -> PendingAction:
    return PendingAction.objects.create(
        action_type=action_type,
        title=title,
        summary=summary,
        payload=payload or {},
        status=PendingAction.Status.PENDING,
    )


def list_pending(status: str = PendingAction.Status.PENDING) -> List[dict]:
    qs = PendingAction.objects.all()
    if status:
        qs = qs.filter(status=status)
    return [item.to_dict() for item in qs]


def execute_pending(action: PendingAction) -> str:
    payload = action.payload or {}
    if action.action_type == PendingAction.ActionType.BOOK_MEETING:
        return book_calendar_meeting(
            title=payload.get("title", action.title),
            date_str=payload["date_str"],
            time_str=payload["time_str"],
            duration_minutes=int(payload.get("duration_minutes", 30)),
            attendee_email=payload.get("attendee_email", ""),
        )
    if action.action_type == PendingAction.ActionType.SEND_EMAIL:
        return send_email_notification(
            to_email=payload["to_email"],
            subject=payload.get("subject", action.title),
            message_body=payload.get("message_body", action.summary),
        )
    if action.action_type == PendingAction.ActionType.RESCHEDULE:
        return draft_reschedule_email(
            to_email=payload["to_email"],
            original_meeting=payload.get("original_meeting", action.title),
            proposed_times=payload.get("proposed_times", ""),
        )
    return f"No executor for action type {action.action_type}"


def approve_pending(action_id: int) -> dict:
    action = PendingAction.objects.get(pk=action_id)
    if action.status != PendingAction.Status.PENDING:
        return {"status": action.status, "result": action.result or "Already processed"}

    try:
        result = execute_pending(action)
        action.status = PendingAction.Status.EXECUTED
        action.result = result
        action.save(update_fields=["status", "result", "updated_at"])
        return {"status": action.status, "result": result, "item": action.to_dict()}
    except Exception as exc:
        action.status = PendingAction.Status.FAILED
        action.result = str(exc)
        action.save(update_fields=["status", "result", "updated_at"])
        return {"status": action.status, "result": str(exc), "item": action.to_dict()}


def reject_pending(action_id: int) -> dict:
    action = PendingAction.objects.get(pk=action_id)
    action.status = PendingAction.Status.REJECTED
    action.result = "Rejected by user"
    action.save(update_fields=["status", "result", "updated_at"])
    return {"status": action.status, "result": action.result, "item": action.to_dict()}
