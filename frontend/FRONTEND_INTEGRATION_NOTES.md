# Paperwork Navigator · Frontend PRD v1.3 demo implementation

This directory was authored as a **frontend-only demo candidate** using the PM PRD v1.3. It deliberately **does not pretend backend features are implemented**.

## Routes
- `/` original-style landing page with UW/OPT positioning
- `/login` explicitly fake demo access (NOT email OTP)
- `/onboarding` UW, program end date and degree
- `/home` profile and local demo-data reset
- `/checklist` multi-module overview, OPT T01–T06, task progress
- `/opt/select` scope and eligibility-path selection
- `/opt/status` application-stage questions and dates
- `/opt/timeline` illustrative offer/no-offer branching and dated milestone display
- `/opt/tasks/T01` ... `/opt/tasks/T06` task content, statuses, sources
- `/opt` redirects to Checklist (old bookmark compatibility)

## Local demo data
`lib/demo.ts` stores test-only data in browser localStorage under `paperwork-navigator-opt-demo-v1`. This is **not** an account, shared storage, or production security. Do not enter real email or immigration information. The UI explicitly marks mock-only services.

## Deliberate gaps / backend dependencies
1. Auth and verified email/session (`POST /auth/email/*`): not implemented, `/login` is a demo bypass.
2. Policy Pack review/sign-off, dated source verification, school processing times: not implemented.
3. Backend-owned rules engine and Plan Service (`/me/opt-plan`): date calculations here are illustrative only and should be replaced with backend nodes before real students rely on them.
4. Profile, tasks, status persistence, audit, privacy / account deletion: local browser mock only; no Neon/Postgres integration.
5. AI Widget and Contact panel: UI preview only; no AI calls or mail-generation endpoints.
6. PRD v1.3 is not fully signed off (scope/branches/widget in decision log). Confirm with PM.
7. The backend design provided is the older Newcomer/SSN `/api/...` and `X-User-Id` model and **is not compatible** with the new PRD `/me/...` model without a contract decision.

## QA / acceptance before real users
- Verify with `npm run build` and `npm run lint` in the actual GitHub checkout.
- Check mobile layout and keyboard accessibility.
- Run the 45 PRD acceptance tests, especially closed-window, conflicting SEVIS date, date dependencies and task state transitions.
- Verify all law-related statements and sources with designated policy reviewer.
- Enable authentication, account deletion and proper secure user isolation in backend before storing real personal data.

## How to use this overlay
This package contains the modified `app/`, new `components/` and `lib/`, and this note. **Do not replace the repository's package.json, next.config.ts, tsconfig.json, git metadata, or backend directory**. Back up / commit existing changes first. Extract the overlay within the repository's `frontend/` directory and check the diff with `git status` and `git diff` before creating a PR.
