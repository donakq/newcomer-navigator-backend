# Backend

FastAPI API for Paperwork Navigator (UW post-completion OPT, PRD v1.3). Branches, environments and the team workflow are in the [root README](../README.md).

## Status

This is a prototype:
- **Data is stored in Postgres** when `DATABASE_URL` is set (both Vercel backends use Neon). Without it, the backend keeps data in memory, which resets on every restart; that is fine for quick local work and is what most tests use.
- **Login is mock.** No email is sent; the code is always `000000`.
- **Content is placeholder text.** Everything in `catalog/` is marked `TODO(reviewer)` or `TODO(PM)` and has not been verified against official sources.
- **The AI assistant is a stub.** `/api/assistant/messages` refuses out-of-scope topics and answers in the user's language, but does not really answer OPT questions yet.

## API

Errors always look like `{"error": {"code": "...", "message": "..."}}`. The full contract is the generated docs at `/docs` (machine-readable at `/openapi.json`). The backend root `/` redirects to `/docs`.

### OPT MVP v1 (PRD v1.3 §8.3)

These endpoints implement the PRD contract. Each logged-in user has their own profile and task statuses (kept in memory for now). Dates come from the timeline engine in `app/opt/timeline.py`; content comes from `catalog/`. A new user gets `404 onboarding_required` from `/api/me/*` until onboarding.

Auth: `POST /api/auth/email/verify` returns a token; send it as `Authorization: Bearer <token>` on every `/api/me/*` and `/api/assistant/*` request. Without it, or after a server restart, you get `401 unauthenticated`. **Mock: no email is sent and the code is always `000000`.** A bearer token is used instead of a cookie because the frontend and backend are on different `*.vercel.app` sites, where browsers block third-party cookies.

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
| PUT | `/api/me/processing-times` | Student's own estimates for UW I-20, USCIS standard and premium processing; each must be inside the range the plan shows | 422 `out_of_range` |
| POST | `/api/me/opt-plan/generate` | Generate plan: tasks T01–T06, nodes N1–N7 (+ N1d, UW I-20 request deadline), risk labels, processing ranges | — |
| GET | `/api/me/opt-plan` | Current plan (Checklist and Timeline read the same data) | — |
| GET / PATCH | `/api/me/tasks/{id}` | Task details / update status or dates | 404, 409 `task_blocked`, 422 `missing_fields` (T03 needs `dso_rec_date`, T05 needs `uscis_receipt_date` to complete) |
| POST | `/api/me/dso-drafts` | Email draft for the school office (never sent) | 422 |
| POST | `/api/assistant/messages` | AI Widget (mock: refuses H-1B/CPT/green card, answers in the user's language) | 422 |
| GET | `/api/health` | Health check, app version, number of OPT task templates | — |

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

## Layout

```
app/main.py           FastAPI app (Vercel entrypoint); / redirects to /docs
app/routers/          auth, schools, me (all /api/me endpoints), assistant
app/schemas/opt.py    Pydantic models: the API contract and PRD enums
app/opt/timeline.py   OPT date engine: N1–N7, risk labels (pure functions, no LLM)
app/opt/content.py    loads and validates the content YAML in catalog/ at startup
app/store/            storage: Store interface, memory.py (no DATABASE_URL), sql.py (Postgres tables)
app/mock/             demo student, stub assistant
app/ai/client.py      the only module that calls the LLM (used by the real assistant later)
app/errors.py         error format; app/deps.py: bearer token parsing
catalog/              team-maintained content YAML (see Editing content)
tests/
```

`app/db/` and `scripts/` are empty placeholders for the database and the official-source ingestion script.

## Local development

From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs. Without `DATABASE_URL` the data lives in memory.

To use a real Postgres locally (Docker):

```bash
docker run -d --name pn-postgres -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=paperwork -p 54329:5432 postgres:16-alpine
```

```bash
DATABASE_URL=postgres://postgres:devpass@127.0.0.1:54329/paperwork uvicorn app.main:app --reload
```

Tables are created automatically on first start. Once the schema has to change on a database that already holds data, add Alembic migrations.

Run the tests (every test runs on the in-memory store and on SQLite):

```bash
pytest
```

Also run them on Postgres:

```bash
TEST_DATABASE_URL=postgres://postgres:devpass@127.0.0.1:54329/paperwork pytest
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
| `DATABASE_URL` | Yes | Postgres connection string. Use Neon's **pooled** URL; `postgres://…` works as-is |
| `LLM_API_KEY` | Later (real assistant) | API key for the LLM |
| `FAST_MODEL` | Optional | Model id for the assistant (default `claude-haiku-5-5`) |
| `LLM_PROVIDER` | Optional | `anthropic` (default) or `gemini` |
| `GEMINI_API_KEY` | When `LLM_PROVIDER=gemini` | Gemini API key from Google AI Studio. The free tier lets Google use prompts to improve its products |
| `GEMINI_MODEL` | Optional | Gemini model id (default `gemini-3.5-flash-lite`, free tier) |
| `CORS_ORIGINS` | Optional | Comma-separated frontend origins allowed to call the API (default `*`, any origin) |

After a deploy, `/api/health` should return `"tasks": 6`.
