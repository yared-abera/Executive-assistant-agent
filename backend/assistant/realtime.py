"""
Socket.IO realtime layer (SRS: stream agent execution + pending notifications).

Compatible with the official socket.io JS/React client.
Run the ASGI app with uvicorn (not Django runserver) for WebSocket support:

    uvicorn core.asgi:application --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

import socketio

logger = logging.getLogger(__name__)

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",
    logger=False,
    engineio_logger=False,
)

ROOM_DASHBOARD = "dashboard"

# Captured from the ASGI event loop so sync Django views can emit safely.
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def _capture_loop() -> None:
    global _main_loop
    try:
        _main_loop = asyncio.get_running_loop()
    except RuntimeError:
        pass


def emit_sync(event: str, data: Any, room: Optional[str] = None) -> None:
    """Emit a Socket.IO event from synchronous Django code."""

    async def _emit():
        if room:
            await sio.emit(event, data, room=room)
        else:
            await sio.emit(event, data)

    loop = _main_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(_emit(), loop)
        return

    try:
        running = asyncio.get_running_loop()
        running.create_task(_emit())
    except RuntimeError:
        logger.debug("Socket.IO emit skipped (ASGI loop not ready yet): %s", event)


def broadcast_agent_log(entry: Dict[str, Any], room: str = ROOM_DASHBOARD) -> None:
    emit_sync("agent_log", entry, room=room)


def broadcast_agent_done(payload: Dict[str, Any], room: str = ROOM_DASHBOARD) -> None:
    emit_sync("agent_done", payload, room=room)


def broadcast_pending_action(item: Dict[str, Any], room: str = ROOM_DASHBOARD) -> None:
    emit_sync("pending_action", item, room=room)
    emit_sync(
        "notification",
        {
            "type": "pending_action",
            "title": item.get("title"),
            "summary": item.get("summary"),
            "item": item,
        },
        room=room,
    )


def make_log_emitter(room: str = ROOM_DASHBOARD) -> Callable[[Dict[str, Any]], None]:
    """Callback suitable for run_executive_agent(on_log=...)."""

    def _on_log(entry: Dict[str, Any]) -> None:
        broadcast_agent_log(entry, room=room)

    return _on_log


@sio.event
async def connect(sid, environ):
    _capture_loop()
    await sio.enter_room(sid, ROOM_DASHBOARD)
    await sio.emit(
        "connected",
        {
            "sid": sid,
            "room": ROOM_DASHBOARD,
            "message": "Executive Assistant realtime ready",
        },
        to=sid,
    )
    logger.info("Socket.IO client connected: %s", sid)


@sio.event
async def disconnect(sid):
    logger.info("Socket.IO client disconnected: %s", sid)


@sio.on("join_dashboard")
async def join_dashboard(sid, data=None):
    _capture_loop()
    await sio.enter_room(sid, ROOM_DASHBOARD)
    await sio.emit("joined", {"room": ROOM_DASHBOARD}, to=sid)


@sio.on("run_command")
async def run_command(sid, data):
    """
    Client → server: { "command": "Schedule a meeting..." }
    Server → dashboard room: agent_status, agent_log*, pending_action*, agent_done
    """
    from .agent import run_executive_agent

    _capture_loop()
    command = (data or {}).get("command") if isinstance(data, dict) else None
    if not command:
        await sio.emit(
            "agent_done",
            {"error": "No command provided", "logs": [], "pending_actions": []},
            to=sid,
        )
        return

    await sio.emit(
        "agent_status",
        {"detail": "starting", "command": command},
        room=ROOM_DASHBOARD,
    )

    loop = asyncio.get_running_loop()

    def on_log(entry: Dict[str, Any]) -> None:
        asyncio.run_coroutine_threadsafe(
            sio.emit("agent_log", entry, room=ROOM_DASHBOARD),
            loop,
        )

    result = await loop.run_in_executor(
        None,
        lambda: run_executive_agent(command, on_log=on_log),
    )
    result.setdefault("logs", [])
    result.setdefault("pending_actions", [])

    for item in result.get("pending_actions") or []:
        await sio.emit("pending_action", item, room=ROOM_DASHBOARD)
        await sio.emit(
            "notification",
            {
                "type": "pending_action",
                "title": item.get("title"),
                "summary": item.get("summary"),
                "item": item,
            },
            room=ROOM_DASHBOARD,
        )

    await sio.emit("agent_done", result, room=ROOM_DASHBOARD)
