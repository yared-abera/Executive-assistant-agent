"""
ASGI config for core project — Django HTTP + Socket.IO WebSocket.

Start with:
    uvicorn core.asgi:application --reload --host 127.0.0.1 --port 8000
"""

import os

import socketio
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

django_asgi_app = get_asgi_application()

# Import after Django setup so models/settings are ready.
from assistant.realtime import sio  # noqa: E402

application = socketio.ASGIApp(sio, other_asgi_app=django_asgi_app)
