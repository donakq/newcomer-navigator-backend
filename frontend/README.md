# Paperwork Navigator — Frontend

Next.js and TypeScript frontend for the UW Post-Completion OPT MVP.

## Local development

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

## Production build

```bash
npm run build
```

## Current status

This frontend runs in Demo Mode using local browser data.

The following are not yet connected to production services:
- Email authentication
- Backend OPT Plan Service
- Persistent database storage
- AI assistant API

OPT timeline dates are illustrative and must not be used as verified immigration guidance.

## Deployment

The frontend is intended to deploy from the frontend/ directory using Next.js on Vercel.

Changes are submitted through a feature branch into pre-prod, then promoted to prod after testing.
