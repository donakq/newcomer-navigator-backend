# Backend

FastAPI API for Newcomer Navigator. Branches, environments and the team workflow are in the [root README](../README.md).

## Status

This is a prototype:
- **Data is not saved.** User data lives in memory and resets whenever Vercel recycles the function. A database comes later.
- **Task content is placeholder text.** Everything in `catalog/` is marked `TODO(content)` and has not been verified against official sources.
- **Chat is a stub.** `/api/chat` sends the message to the LLM when `LLM_API_KEY` is set, otherwise it returns a fixed fallback reply. The live LLM call has not been verified on Vercel yet.

## API

Errors always look like `{"error": {"code": "...", "message": "..."}}`. The full contract is the generated docs at `/docs` (machine-readable at `/openapi.json`). The backend root `/` redirects to `/docs`.

### OPT MVP v1 (PRD v1.3 §8.3): mock data

These endpoints implement the PRD contract but return **mock data**: nothing is saved, and every user sees the same demo student (PRD persona A: UW, Master, Program End Date 2027-06-11, offer start 2027-07-12). Dates are real; they come from the timeline engine in `app/opt/timeline.py`. Policy values (processing times, UW contact info, source URLs) are placeholders marked `TODO(reviewer)`.

Auth: `POST /api/auth/email/verify` returns a token; send it as `Authorization: Bearer <token>` on every `/api/me/*` and `/api/assistant/*` request. Without it you get `401 unauthenticated`. **Mock: no email is sent and the code is always `000000`.** A bearer token is used instead of a cookie because the frontend and backend are on different `*.vercel.app` sites, where browsers block third-party cookies.

| Method | Path | What it does | Errors |
|---|---|---|---|
| POST | `/api/auth/email/start` | Send a login code | 422 bad email |
| POST | `/api/auth/email/verify` | Log in; returns `token`, `is_new_user` | 401 `invalid_code`, 422 terms not accepted |
| POST | `/api/auth/logout` | Log out | — |
| GET | `/api/schools?q=` | Search schools (only UW is `SUPPORTED`) | — |
| GET | `/api/schools/{id}/office` | Contact panel info card | 404 |
| PUT | `/api/me/onboarding` | School, Program End Date, degree | 409 `unsupported_school`, 422 |
| GET / PATCH | `/api/me/profile` | Home: read / edit profile; PATCH returns `plan_version` | 422 |
| DELETE | `/api/me` | Delete account and data | — |
| GET | `/api/me/checklist` | Overview: modules, graduation banner, OPT summary | — |
| PUT | `/api/me/opt-selection` | Select OPT | 422 `out_of_scope` |
| PUT | `/api/me/status` | Stage + stage dates | 422 `missing_fields` |
| PUT | `/api/me/offer` | Timeline inputs | 422 `missing_fields` |
| POST | `/api/me/opt-plan/generate` | Generate plan: tasks T01–T06, nodes N1–N7, risk labels | — |
| GET | `/api/me/opt-plan` | Current plan (Checklist and Timeline read the same data) | — |
| GET / PATCH | `/api/me/tasks/{id}` | Task details / update status or dates | 404, 422 `missing_fields` (T03 needs `dso_rec_date`, T05 needs `uscis_receipt_date` to complete) |
| POST | `/api/me/dso-drafts` | Email draft for the school office (never sent) | 422 |
| POST | `/api/assistant/messages` | AI Widget (mock: refuses H-1B/CPT/green card, answers in the user's language) | 422 |

### Legacy newcomer endpoints

Used by the current mock frontend; removed once the real frontend switches to the OPT endpoints. They send `X-User-Id: <uuid4>` instead of a token.

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

## Editing content

OPT content lives in `catalog/` as YAML (format: the OPT MVP v1 Data Spec). The app validates it at startup, so a broken file stops the deploy instead of breaking pages.

| File | What it holds | Who fills it |
|---|---|---|
| `catalog/schools.yaml` | Supported schools | PM |
| `catalog/policy/uw.yaml` | UW Policy Pack: processing time, request window, office contact, field hints, review status | Policy reviewer |
| `catalog/federal.yaml` | USCIS processing times, buffer, federal rule references | Policy reviewer |
| `catalog/sources.yaml` | Official sources (URL, last reviewed) | Policy reviewer |
| `catalog/tasks/T01.yaml` … `T06.yaml` | Task steps, documents, sources, prerequisites, which timeline node to show | Policy reviewer |
| `catalog/ai/*.yaml` | AI chips, refusal / disclaimer templates, glossary | PM |

Every value is a placeholder for now and is marked `TODO(reviewer)` or `TODO(PM)`. While the Policy Pack status is not `REVIEWED_ACTIVE`, the plan response carries a warning saying dates are unverified.

Checks that run at startup: every `source_id` exists; task prerequisites and timeline nodes exist; `complete_requires` only names known date fields; `REVIEWED_ACTIVE` needs `reviewer` and `reviewed_at`; a `FORM` / `PORTAL` contact channel needs `advising_form_url`; all four field hints are present. Run `pytest` before opening a PR.

`catalog/legacy/` holds the old newcomer tasks (SSN, phone, bank) used by the legacy endpoints.

## Layout

```
app/main.py           FastAPI app (Vercel entrypoint); / redirects to /docs
app/routers/          profile, checklist, tasks, chat endpoints
app/schemas/          Pydantic models: the API contract, profile, catalog format
app/services/         rules engine, checklist, profile, tasks, chat, in-memory store
app/ai/client.py      the only module that calls the LLM
app/catalog_loader.py loads and validates catalog/ at startup
app/errors.py         error format; app/deps.py: bearer token (OPT) and X-User-Id (legacy) checks
app/opt/timeline.py   OPT date engine: N1–N7, risk labels (pure functions, no LLM)
app/opt/content.py    loads and validates the OPT content YAML in catalog/
app/mock/             demo student behind the OPT endpoints until the database and login exist
catalog/              team-maintained task YAML files and events.yaml
tests/
```

`app/db/` and `scripts/` are empty placeholders for the database and the official-source ingestion script.

## Local development

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

Run the tests:

```bash
pytest
```

## Deployment (Vercel)

| Vercel project | Root Directory | Production branch |
|---|---|---|
| `newcomer-navigator-backend` | `backend` | `prod` |
| `newcomer-navigator-preprod` | `backend` | `pre-prod` |

Both use the **FastAPI** preset with default settings. No `vercel.json` is needed: Vercel runs `app/main.py` and bundles every file under `backend/`, including `catalog/`. A push to the production branch deploys automatically. The pre-prod backend is a separate project (not a preview of the prod project) because preview deployments require a Vercel login.

Environment variables are set per project, so set them in both:

| Variable | Needed? | Purpose |
|---|---|---|
| `LLM_API_KEY` | For chat | API key for the LLM |
| `FAST_MODEL` | Optional | Model id for chat (default `claude-haiku-5-5`) |
| `CORS_ORIGINS` | Optional | Comma-separated frontend origins allowed to call the API (default `*`, any origin) |

After a deploy, `/api/health` should return `"tasks": 3`.
