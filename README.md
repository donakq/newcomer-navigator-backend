# Newcomer Navigator Backend

FastAPI backend for Newcomer Navigator, which helps new F-1 students in Washington State figure out which admin tasks they need to do (SSN, bank account, phone, ...), how to do them, and track their progress.

## Layout

```
api/index.py        Vercel entrypoint
app/main.py         FastAPI app, CORS, /api/health
app/routers/        profile, checklist, tasks, chat endpoints
app/schemas/        Pydantic models (the API contract)
app/services/       profile, rules engine, checklist, tasks, chat logic
app/ai/             LLM client, prompts, output validators
app/db/             SQLAlchemy models and session
catalog/            team-curated task YAML files and events.yaml
scripts/            offline scripts (official source ingestion, cleanup)
tests/
```

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## API

All requests send `X-User-Id: <uuid4>` (the frontend generates it once and keeps it in localStorage). Errors always look like `{"error": {"code": "...", "message": "..."}}`. The full contract is the generated docs at `/docs`.

| Method | Path | What it does |
|---|---|---|
| GET | `/api/health` | Health check, app version, number of catalog tasks |
| GET / POST | `/api/profile` | Read / merge the student's answers; POST returns the checklist diff |
| GET | `/api/checklist` | The student's tasks with reason, status, progress, blocked_by |
| POST | `/api/checklist/{task_id}` | `{"action": "add" \| "dismiss"}` |
| GET | `/api/tasks/{task_id}` | Task steps, materials, official sources, done flags |
| PATCH | `/api/tasks/{task_id}/steps/{step_id}` | `{"done": true \| false}` |
| POST | `/api/tasks/{task_id}/steps/{step_id}/dso-draft` | Email draft for asking the DSO |
| POST | `/api/chat` | `{"message": "..."}` |

> **Prototype limits:** user data lives in memory, so it resets whenever Vercel recycles the function (no database yet). Task content in `catalog/` is placeholder text marked `TODO(content)`. Chat replies come from the LLM only when `LLM_API_KEY` is set; otherwise a fixed fallback message is returned.

## Deploy (Vercel)

1. Import this repo at vercel.com/new.
2. Set env vars: `LLM_API_KEY`, `CORS_ORIGINS` (comma-separated frontend origins), optionally `FAST_MODEL`.
3. Check `https://<deployment>/api/health` (`tasks` should be 3) and `https://<deployment>/docs`.

## Tests

```bash
pytest
```
