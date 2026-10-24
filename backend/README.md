# Backend

Django Executive Assistant API. See root [README.md](../README.md) for full-stack setup.

```bash
pip install -r requirements.txt
python manage.py migrate
uvicorn core.asgi:application --reload --host 127.0.0.1 --port 8000
```

Copy `.env.example` → `.env` and fill Gemini, Google Calendar, SendGrid, Supabase keys.
