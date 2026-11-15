# Paperwork Navigator — Frontend

Next.js and TypeScript frontend for the UW Post-Completion OPT MVP.

## Local development

Start the backend first (see [backend/README.md](../backend/README.md)); it serves the API at http://127.0.0.1:8000. Then:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and sign in with any email. The mock backend sends no email; the code is always `000000`.

## Talking to the backend

All data comes from the backend OPT API. The frontend keeps no rules or date math of its own.

- `lib/api.ts`: fetch wrapper and response types. Sends `Authorization: Bearer <token>`; the token from login is kept in localStorage.
- `lib/demo.ts`: shared client store behind `useDemoProfile()`. It maps API fields to the page fields, sends edits, and turns the backend plan into the Timeline view. A `401` sends the user back to `/login`.
- Backend URL: `NEXT_PUBLIC_API_BASE_URL` (see `.env.example`); defaults to http://127.0.0.1:8000.

| Frontend runs on | `NEXT_PUBLIC_API_BASE_URL` |
|---|---|
| `localhost` | http://127.0.0.1:8000 (default) |
| pre-prod | https://newcomer-navigator-preprod.vercel.app |
| prod | https://newcomer-navigator-backend.vercel.app |

The full API contract is the backend's `/docs` page.

## Production build

```bash
npm run build
```

## Current status

The pages are connected to the backend OPT API, which still runs on **mock data**:
- Login is real in shape (email, then a code) but sends no email; the code is `000000`.
- Each user's data lives in the backend's memory and is lost when the backend restarts.
- Task content, processing times, sources and office contacts are placeholders until the policy reviewer fills them in (`backend/catalog/`).
- The AI assistant is a stub: it refuses out-of-scope topics and answers in the user's language, but does not really answer OPT questions yet.

OPT timeline dates are not verified and must not be used as immigration guidance.

## Deployment

The frontend deploys from the `frontend/` directory with Next.js on Vercel. Set `NEXT_PUBLIC_API_BASE_URL` in each Vercel project to the matching backend.

Changes are submitted through a feature branch into pre-prod, then promoted to prod after testing.
