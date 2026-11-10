# Newcomer Navigator Backend

FastAPI backend for Newcomer Navigator, which helps new F-1 students in Washington State figure out which admin tasks they need to do (SSN, bank account, phone, ...), how to do them, and track their progress.

| Environment | Branch | URL |
|---|---|---|
| Pre-prod (testing) | `pre-prod` | https://newcomer-navigator-preprod.vercel.app |
| Production | `prod` | https://newcomer-navigator-backend.vercel.app |

Both sites are public. Each one serves a demo page at `/` and the API docs at `/docs`.

## Status

This is a prototype:
- **Data is not saved.** User data lives in memory and resets whenever Vercel recycles the function. A database comes later.
- **Task content is placeholder text.** Everything in `catalog/` is marked `TODO(content)` and has not been verified against official sources.
- **Chat is a stub.** `/api/chat` sends the message to the LLM when `LLM_API_KEY` is set, otherwise it returns a fixed fallback reply. The live LLM call has not been verified on Vercel yet.
- **The demo page is temporary.** `app/static/index.html` is a minimal UI for showing the team; the real frontend replaces it.

## Workflow

1. Create a branch from `pre-prod`, make your changes, and open a PR into `pre-prod`.
2. After the PR is merged, Vercel redeploys pre-prod automatically. Test on the pre-prod URL.
3. When it looks good, open a PR from `pre-prod` into `prod`. Merging it updates production.

Never push directly to `prod`.

## Editing task content

Tasks live in `catalog/tasks/<task_id>.yaml`, one file per task. Events the chat can recognize live in `catalog/events.yaml`. The fields are described in the design notes (Task Catalog Schema).

- Copy an existing task file as a starting point.
- When you change a task's steps or text, bump its `version` by 1.
- Use only profile fields that exist in `app/schemas/profile.py` in `when` conditions.
- Run `pytest` before opening the PR. A broken YAML file stops the whole app from starting, so the site would go down.

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
| POST | `/api/tasks/{task_id}/steps/{step_id}/dso-draft` | Email draft for asking the DSO (fixed template) |
| POST | `/api/chat` | `{"message": "..."}` |

## Layout

```
app/main.py           FastAPI app (Vercel entrypoint); serves the demo page at /
app/static/           demo page (temporary)
app/routers/          profile, checklist, tasks, chat endpoints
app/schemas/          Pydantic models: the API contract, profile, catalog format
app/services/         rules engine, checklist, profile, tasks, chat, in-memory store
app/ai/client.py      the only module that calls the LLM
app/catalog_loader.py loads and validates catalog/ at startup
app/errors.py         error format; app/deps.py: X-User-Id check
catalog/              team-maintained task YAML files and events.yaml
docs/                 implementation plans
tests/
```

`app/db/` and `scripts/` are empty placeholders for the database and the official-source ingestion script.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000 (demo page) or http://127.0.0.1:8000/docs (API docs).

Run the tests:

```bash
pytest
```

## Deployment (Vercel)

Two Vercel projects deploy from this one repo:

| Vercel project | Production branch | Notes |
|---|---|---|
| `newcomer-navigator-backend` | `prod` | |
| `newcomer-navigator-preprod` | `pre-prod` | A separate project so its URL is public; preview deployments require a Vercel login |

Both use the **FastAPI** preset with default settings. No `vercel.json` is needed: Vercel runs `app/main.py` and bundles every project file, including `catalog/`. A push to the production branch deploys automatically.

Environment variables are set per project, so set them in both:

| Variable | Needed? | Purpose |
|---|---|---|
| `LLM_API_KEY` | For chat | API key for the LLM |
| `FAST_MODEL` | Optional | Model id for chat (default `claude-haiku-5-5`) |
| `CORS_ORIGINS` | Only when a frontend on another domain calls the API | Comma-separated origins |

After a deploy, `/api/health` should return `"tasks": 3`.
