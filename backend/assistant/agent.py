"""Gemini ReAct executive assistant loop with structured UI-ready logs."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from google.genai import types

from .calendar_service import executive_clock_context
from .clients import ConfigurationError, get_gemini_client
from .memory import retrieve_relevant_preferences
from .pending import create_pending_action
from .tools import (
    book_calendar_meeting,
    check_calendar_conflicts,
    propose_alternate_slots,
    send_email_notification,
)

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 8

TOOL_MAP = {
    "check_calendar_conflicts": check_calendar_conflicts,
    "book_calendar_meeting": book_calendar_meeting,
    "propose_alternate_slots": propose_alternate_slots,
    "send_email_notification": send_email_notification,
}

AGENT_TOOLS = list(TOOL_MAP.values())


def _maybe_queue_pending_from_tool(tool_name: str, args: dict, result: str) -> list:
    """Create pending approvals for destructive/outbox actions when useful for the UI."""
    pending = []
    # Bookings go through immediately via the tool; if the model proposes alternatives
    # without booking, we do not auto-create pending. Explicit queue helper for future use.
    if tool_name == "book_calendar_meeting" and "failed" not in result.lower():
        # Already executed by the tool — surface as executed trail for the UI if needed.
        return pending
    return pending


def run_executive_agent(
    user_command: str,
    on_log: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """Executes the Reason + Act (ReAct) loop with dynamic tool calling.

    on_log: optional callback invoked for each log entry (Socket.IO / SSE streaming).
    """
    execution_logs: List[Dict[str, Any]] = []
    pending_actions: List[Dict[str, Any]] = []

    def _log(entry: Dict[str, Any]) -> None:
        execution_logs.append(entry)
        if on_log:
            try:
                on_log(entry)
            except Exception:
                logger.debug("on_log callback failed", exc_info=True)

    try:
        relevant_rules = retrieve_relevant_preferences(user_command)
        clock = executive_clock_context()
        _log(
            {
                "type": "thought",
                "detail": (
                    f"Retrieved Executive Rules: {relevant_rules} | "
                    f"Clock {clock['timezone']} today={clock['today']} "
                    f"tomorrow={clock['tomorrow']}"
                ),
            }
        )

        system_instruction = f"""
You are an autonomous AI Executive Assistant for a tech-startup executive.
You schedule meetings, resolve calendar conflicts, and send follow-up emails.

Executive clock (authoritative — do not invent dates):
- Timezone: {clock['timezone']}
- Today ({clock['weekday']}): {clock['today']}
- Tomorrow: {clock['tomorrow']}
- Current local time: {clock['local_time']}

When the user says "today", "tomorrow", or a weekday relative to now, convert to
YYYY-MM-DD using ONLY the dates above. Always pass date_str as YYYY-MM-DD to tools.
Never invent or reuse example dates from training data.

Executive Rules & Preferences (MUST follow — these override the user's preferred day/time):
{relevant_rules}

If a preference forbids meetings on a weekday (e.g. "No meetings on Monday"):
- Do NOT call book_calendar_meeting for that weekday.
- Remind the user in plain language that they set that preference (quote the exact rule),
  say that day is unavailable, and mention they can delete it under Preferences if they
  want to allow that weekday again.
- Then propose times on the next allowed day (propose_alternate_slots on an allowed date,
  or ask the user to pick another day).

Workflow for scheduling:
1. Always call check_calendar_conflicts for the requested date first.
2. If the requested time conflicts, call propose_alternate_slots (respect no-meetings-before rules).
3. Explain conflicts and proposed alternatives clearly.
4. Only call book_calendar_meeting when the requested slot is free OR the user already chose an alternate,
   AND the date is not banned by preferences.
5. For follow-ups / confirmations, use send_email_notification.
6. Prefer proposing alternatives over silently moving existing meetings.
7. Never invent calendar data — rely on tool observations.
8. If a tool reports a local/mock schedule (Google unreachable or CALENDAR_MODE=mock),
   treat that observation as authoritative for availability in this demo.
"""

        client = get_gemini_client()
        chat = client.chats.create(
            model="gemini-3.5-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=AGENT_TOOLS,
                temperature=0.2,
                # We run tools in the ReAct loop below. Leaving AFC on makes the
                # SDK invoke callables itself and can crash on postponed annotations
                # (isinstance() arg 2 must be a type...) under Python 3.14+.
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
            ),
        )

        response = chat.send_message(user_command)
        iterations = 0

        while response.function_calls and iterations < MAX_TOOL_ITERATIONS:
            iterations += 1
            function_response_parts = []

            for call in response.function_calls:
                tool_name = call.name
                args = dict(call.args or {})

                _log({"type": "action", "tool": tool_name, "arguments": args})

                if tool_name in TOOL_MAP:
                    try:
                        result = TOOL_MAP[tool_name](**args)
                    except TypeError as exc:
                        result = f"Tool argument error: {exc}"
                    except Exception as exc:
                        result = f"Tool execution error: {exc}"
                else:
                    result = f"Error: Tool '{tool_name}' not recognized."

                _log({"type": "observation", "result": result})
                pending_actions.extend(
                    _maybe_queue_pending_from_tool(tool_name, args, str(result))
                )

                function_response_parts.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": result},
                    )
                )

            # Batch all tool results into a single model turn (correct multi-tool handling).
            response = chat.send_message(function_response_parts)

        if response.function_calls and iterations >= MAX_TOOL_ITERATIONS:
            _log(
                {
                    "type": "thought",
                    "detail": "Stopped: reached max tool iterations.",
                }
            )

        final_text = getattr(response, "text", None) or "Done."
        _log({"type": "final_answer", "detail": final_text})

        # If the agent proposed alternatives without booking, create a pending book action
        # when observation includes open slots and the user command looks like a schedule ask.
        pending_actions = _enrich_pending_from_logs(
            user_command, execution_logs, pending_actions
        )

        return {
            "final_response": final_text,
            "logs": execution_logs,
            "pending_actions": pending_actions,
        }

    except ConfigurationError as exc:
        _log({"type": "thought", "detail": str(exc)})
        return {
            "error": str(exc),
            "final_response": None,
            "logs": execution_logs,
            "pending_actions": pending_actions,
        }
    except Exception as exc:
        logger.exception("Agent failed")
        _log({"type": "thought", "detail": f"Agent error: {exc}"})
        return {
            "error": f"Agent failed: {exc}",
            "final_response": None,
            "logs": execution_logs,
            "pending_actions": pending_actions,
        }


def _enrich_pending_from_logs(
    user_command: str,
    logs: List[Dict[str, Any]],
    existing: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """If alternate slots were proposed and no booking occurred, queue a pending booking."""
    if existing:
        return existing

    proposed = None
    booked = False
    for entry in logs:
        if entry.get("type") == "action" and entry.get("tool") == "book_calendar_meeting":
            booked = True
        if entry.get("type") == "action" and entry.get("tool") == "propose_alternate_slots":
            proposed = entry.get("arguments") or {}

    if booked or not proposed:
        return existing

    # Create a soft pending action for the first proposed slot — UI one-click approve.
    date_str = proposed.get("date_str")
    duration = int(proposed.get("duration_minutes", 30))
    obs = next(
        (
            e.get("result")
            for e in logs
            if e.get("type") == "observation" and "Open slots" in str(e.get("result", ""))
        ),
        "",
    )
    # Parse first "start HH:MM" if present
    time_str = "10:00"
    for line in str(obs).splitlines():
        if "start " in line:
            time_str = line.split("start ")[-1].strip(")")
            break

    action = create_pending_action(
        action_type="book_meeting",
        title=f"Approve booking on {date_str} at {time_str}",
        summary=(
            f"Agent proposed alternate times for: {user_command}\n\n{obs}\n\n"
            f"Default selection: {date_str} {time_str} ({duration} min)."
        ),
        payload={
            "title": "Meeting (from assistant proposal)",
            "date_str": date_str,
            "time_str": time_str,
            "duration_minutes": duration,
            "attendee_email": "",
        },
    )
    return [action.to_dict()]
