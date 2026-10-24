# GCP Cloud Run (Always Free tier friendly)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN python manage.py collectstatic --noinput || true

ENV PORT=8080
# uvicorn serves Django HTTP + Socket.IO WebSockets
CMD exec uvicorn core.asgi:application --host 0.0.0.0 --port $PORT --workers 1
 