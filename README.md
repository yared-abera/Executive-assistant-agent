# Executive Assistant AI

Full-stack Autonomous AI Executive Assistant (Brain3 assignment): Gemini ReAct agent + Google Calendar + Resend + Supabase RAG + Socket.IO dashboard.

```
executive-assistant-AI/
├── backend/     # Django + DRF + Socket.IO (ASGI)
├── frontend/    # React (Vite) executive dashboard
└── docs/        # Assignment, SRS, Supabase SQL
```

## Prerequisites

- Python 3.12+ with `venv/` at repo root (or recreate)
- Node.js 20+
- Backend secrets in `backend/.env` (see `backend/.env.example`)

## Backend

```bash
cd backend
..\venv\Scripts\activate          # Windows — from backend/, or activate from root
pip install -r requirements.txt
python manage.py migrate

# Socket.IO requires uvicorn (not runserver):
uvicorn core.asgi:application --reload --host 127.0.0.1 --port 8000
```

### Key APIs

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/agent/command/` | NL command |
| Socket.IO | `/` | `run_command`, `agent_log`, `agent_done`, `pending_action` |
| POST | `/api/agent/preference/` | Store RAG preference |
| GET | `/api/calendar/events/?date=` | Day schedule |
| GET/POST | `/api/agent/pending/` … | Approvals |

Tests: `python manage.py test assistant`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL (usually `http://127.0.0.1:5173`). Env: `frontend/.env` → `VITE_API_URL` / `VITE_SOCKET_URL` = `http://127.0.0.1:8000`.

```bash
npm test                 # Vitest (API client, panels, Socket.IO hook)
```

### Dashboard panels (balanced FE/BE)

- **Command** — Socket.IO `run_command`
- **Agent activity** — live ReAct logs
- **Schedule** — live Google Calendar
- **Approvals** — one-click approve/reject
- **Preferences** — Supabase RAG
- **Notifications** — decline / briefing toasts

Responsive: mobile stack (approvals high), tablet 2-col, desktop 3-col.

## Docs

- `docs/AI Automation Assignment – Full Stack AI Software Engineer.docx`
- `docs/AI_Executive_Assistant_SRS_V2.docx`
- `docs/supabase_schema.sql`

## Demo script

1. Start backend (`uvicorn`) then frontend (`npm run dev`).
2. Save a preference (e.g. no meetings before 10 AM).
3. Run a schedule command — watch live logs.
4. Approve a pending action if proposed.
5. Confirm schedule refresh; optional Resend follow-up to your verified inbox.
