# Frontend

The files here (`index.html`, `config.js`) are a **mock**: a single static page with no build step that exercises every backend endpoint. Replace them with the real frontend; any framework works (Next.js, Vite + React, ...).

## Talking to the backend

| Frontend runs on | Backend it should call |
|---|---|
| `localhost` | http://127.0.0.1:8000 |
| pre-prod (`newcomer-navigator-web-preprod.vercel.app`) | https://newcomer-navigator-preprod.vercel.app |
| prod (`newcomer-navigator-web.vercel.app`) | https://newcomer-navigator-backend.vercel.app |

The mock picks the backend in `config.js` by hostname. In the real frontend, use an environment variable set per Vercel project instead (for example `NEXT_PUBLIC_API_BASE_URL` or `VITE_API_BASE_URL`).

Rules every request must follow:
- Send header `X-User-Id: <uuid4>`. Generate it once with `crypto.randomUUID()` and keep it in localStorage.
- Errors come back as `{"error": {"code": "...", "message": "..."}}`.
- The backend allows requests from any origin for now, so CORS needs no setup.

## API contract

The backend's `/openapi.json` is the contract; browse it at `/docs`. To get TypeScript types instead of copying field names by hand:

```bash
npx openapi-typescript https://newcomer-navigator-preprod.vercel.app/openapi.json -o src/api/schema.ts
```

Re-run it whenever the backend changes an endpoint.

## Running the mock locally

Start the backend first (see [backend/README.md](../backend/README.md)), then from this folder:

```bash
python3 -m http.server 5173
```

Open http://localhost:5173.

## Deployment (Vercel)

Two Vercel projects, both with **Root Directory** `frontend`:

| Vercel project | Production branch |
|---|---|
| `newcomer-navigator-web` → https://newcomer-navigator-web.vercel.app | `prod` |
| `newcomer-navigator-web-preprod` → https://newcomer-navigator-web-preprod.vercel.app | `pre-prod` |

For the mock, use the **Other** preset with no build command. When the real frontend lands, switch the preset to its framework and set the API base URL env var in each project.
