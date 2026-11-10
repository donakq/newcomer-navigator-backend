# Newcomer Navigator

Helps new F-1 students in Washington State figure out which admin tasks they need to do (SSN, bank account, phone, ...), how to do them, and track their progress.

This repo holds both parts of the app:

| Folder | What | Details |
|---|---|---|
| [`backend/`](backend/README.md) | FastAPI API: rules engine, task catalog, chat | [backend/README.md](backend/README.md) |
| [`frontend/`](frontend/README.md) | Web UI (currently a mock page) | [frontend/README.md](frontend/README.md) |
| `docs/` | Implementation plans | |

## Environments

| | Pre-prod (testing) | Production |
|---|---|---|
| Branch | `pre-prod` | `prod` |
| Backend | https://newcomer-navigator-preprod.vercel.app | https://newcomer-navigator-backend.vercel.app |
| Frontend | not deployed yet | not deployed yet |

All sites are public. The backend serves its API docs at `/docs`.

## Workflow

1. Create a branch from `pre-prod`, make your changes, and open a PR into `pre-prod`.
2. After the PR is merged, Vercel redeploys pre-prod automatically. Test on the pre-prod URLs.
3. When it looks good, open a PR from `pre-prod` into `prod`. Merging it updates production.

Never push directly to `prod`. A change that touches both the API and the UI goes in one PR, so both parts move to pre-prod and prod together.

## Run everything locally

Backend (terminal 1):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Mock frontend (terminal 2):

```bash
cd frontend
python3 -m http.server 5173
```

Open http://localhost:5173. When served from localhost, the frontend calls the backend at http://127.0.0.1:8000.

## Status

This is a prototype. User data lives in memory and resets when Vercel recycles the backend, task content is placeholder text, and chat is a stub. See [backend/README.md](backend/README.md#status).
