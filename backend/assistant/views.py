"""UI-ready REST API for the Executive Assistant backend."""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .agent import run_executive_agent
from .calendar_service import list_events_for_date
from .memory import store_preference
from .models import PendingAction
from .pending import approve_pending, list_pending, reject_pending
from .tools import send_email_notification


class AgentCommandView(APIView):
    def post(self, request):
        command = request.data.get("command")
        if not command:
            return Response(
                {"error": "No command provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .realtime import (
            broadcast_agent_done,
            broadcast_pending_action,
            make_log_emitter,
        )

        try:
            result = run_executive_agent(command, on_log=make_log_emitter())
        except Exception as exc:
            return Response(
                {"error": "Agent execution failed", "detail": str(exc), "logs": []},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        result.setdefault("logs", [])
        result.setdefault("pending_actions", [])
        for item in result.get("pending_actions") or []:
            broadcast_pending_action(item)
        broadcast_agent_done(result)

        if result.get("error"):
            return Response(result, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result, status=status.HTTP_200_OK)


class AgentCommandStreamView(APIView):
    """SSE stream that runs the agent and emits each log entry as an event."""

    def get(self, request):
        command = request.query_params.get("command")
        if not command:
            return Response(
                {"error": "No command provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        def event_stream():
            yield _sse("status", {"detail": "starting"})
            result = run_executive_agent(command)
            for entry in result.get("logs", []):
                yield _sse("log", entry)
            payload = {
                "final_response": result.get("final_response"),
                "pending_actions": result.get("pending_actions", []),
                "error": result.get("error"),
            }
            yield _sse("done", payload)

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class AddPreferenceView(APIView):
    def post(self, request):
        preference = request.data.get("preference")
        if not preference:
            return Response(
                {"error": "No preference provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            msg = store_preference(preference)
            return Response(
                {"status": "success", "message": msg, "preference": preference},
                status=status.HTTP_201_CREATED,
            )
        except Exception as exc:
            return Response(
                {"error": "Failed to store preference", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class CalendarEventsView(APIView):
    def get(self, request):
        date_str = request.query_params.get("date") or date.today().isoformat()
        try:
            events = list_events_for_date(date_str)
            return Response({"date": date_str, "events": events})
        except Exception as exc:
            return Response(
                {"error": "Failed to load calendar", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class PendingActionListView(APIView):
    def get(self, request):
        status_filter = request.query_params.get("status", PendingAction.Status.PENDING)
        return Response({"items": list_pending(status=status_filter)})


class PendingActionApproveView(APIView):
    def post(self, request, pk: int):
        try:
            result = approve_pending(pk)
            return Response(result, status=status.HTTP_200_OK)
        except PendingAction.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            return Response(
                {"error": "Approve failed", "detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class PendingActionRejectView(APIView):
    def post(self, request, pk: int):
        try:
            result = reject_pending(pk)
            return Response(result, status=status.HTTP_200_OK)
        except PendingAction.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)


class GoogleCalendarWebhookView(APIView):
    """Receives Google Calendar push notifications / simulated decline events."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        expected = os.environ.get("CALENDAR_WEBHOOK_TOKEN", "")
        token = request.headers.get("X-Goog-Channel-Token") or request.data.get("token")
        if expected and token != expected:
            return Response({"error": "Invalid webhook token"}, status=status.HTTP_403_FORBIDDEN)

        # Google sends sync headers; for demo we also accept JSON decline payloads.
        payload = request.data if isinstance(request.data, dict) else {}
        event_summary = payload.get("summary") or payload.get("original_meeting") or "Meeting"
        attendee = payload.get("attendee_email") or payload.get("to_email") or "attendee@example.com"
        proposed = payload.get("proposed_times") or "Tomorrow 10:00 AM, 11:00 AM, or 2:00 PM"

        from .pending import create_pending_action

        action = create_pending_action(
            action_type=PendingAction.ActionType.RESCHEDULE,
            title=f"Reschedule after decline: {event_summary}",
            summary=(
                f"Attendee {attendee} declined '{event_summary}'. "
                f"Approve to send a reschedule email with: {proposed}"
            ),
            payload={
                "to_email": attendee,
                "original_meeting": event_summary,
                "proposed_times": proposed,
            },
        )
        item = action.to_dict()
        from .realtime import broadcast_pending_action

        broadcast_pending_action(item)
        return Response(
            {"status": "queued", "item": item},
            status=status.HTTP_202_ACCEPTED,
        )


class DailyBriefingJobView(APIView):
    """Cloud Scheduler target: email a short briefing for tomorrow's calendar."""

    authentication_classes = []
    permission_classes = []

    def post(self, request):
        secret = os.environ.get("SCHEDULER_SECRET", "")
        provided = request.headers.get("X-Scheduler-Secret") or request.data.get("secret")
        if secret and provided != secret:
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        events = list_events_for_date(tomorrow)
        lines = [f"Daily briefing for {tomorrow}:"]
        if not events:
            lines.append("No meetings on the calendar.")
        else:
            for ev in events:
                lines.append(f"- {ev.get('start')} – {ev.get('end')}: {ev.get('summary')}")

        pending_count = PendingAction.objects.filter(
            status=PendingAction.Status.PENDING
        ).count()
        lines.append(f"Open approvals waiting: {pending_count}")
        body = "<br/>".join(lines)

        to_email = (
            request.data.get("to_email")
            or os.environ.get("EXECUTIVE_EMAIL")
            or os.environ.get("SENDGRID_FROM_EMAIL")
            or "executive@example.com"
        )
        mail_result = send_email_notification(
            to_email=to_email,
            subject=f"Executive briefing — {tomorrow}",
            message_body=body,
        )
        payload = {
            "status": "ok",
            "date": tomorrow,
            "events": events,
            "pending_count": pending_count,
            "email_result": mail_result,
        }
        from .realtime import emit_sync

        emit_sync(
            "notification",
            {
                "type": "daily_briefing",
                "title": f"Executive briefing — {tomorrow}",
                "summary": f"{len(events)} events, {pending_count} pending approvals",
                "item": payload,
            },
            room="dashboard",
        )
        return Response(payload)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"
