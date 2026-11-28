# Full Setup Wizard and Vertical Timeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** New students answer everything the plan needs in one six-step `/setup`, end on a vertical timeline with
colored date ranges, and only then reach My Checklist.

**Architecture:** The backend adds `Plan.ranges` (computed from timeline nodes and processing-time min/max). The
frontend adds a `/setup` wizard that saves each step through existing endpoints, a shared `VerticalTimeline`
component (used by Step 6 and `/opt/timeline`), and a "setup complete" check that drives routing.

**Tech Stack:** FastAPI 0.162 + Pydantic 2.14 (backend, pytest 9.2); Next.js 16.4 + React 19.3 + Tailwind 4.3
(frontend; no test runner — verify with `tsc`, `npm run build` and the browser).

**Spec:** `docs/superpowers/specs/2026-11-27-full-setup-and-vertical-timeline-design.md`

## Global Constraints

- Range colors: LEGAL_WINDOW green (`bg-[#e7f3ea]`, left border `#4f8f63`), ESTIMATE amber (`bg-[#fdf3de]`,
  border `#e0a845`), NEEDS_DATE gray dashed (striped `#f3f3f3`/white, `border-dashed #9a9a9a`) — as in the approved mockup.
- Ranges are computed only by the backend; the frontend never derives range dates.
- Setup steps, in order: program → opt → progress → offer → processing → timeline. Processing is skippable.
- Out-of-scope at Step 2 (intent ≠ `AFTER_GRADUATION` or not first time) stops with the existing UW ISS copy from `/opt/select`.
- No app nav (`Shell showNav={false}`) anywhere in `/setup`.
- Next 16 `cacheComponents` keeps hidden pages mounted: any page whose local state must not survive navigation
  clears it in a `useLayoutEffect` cleanup (pattern already in `app/onboarding/page.tsx`).
- Copy is plain English, no legal-advice wording; dates shown with `formatDate` (`lib/demo.ts`).
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A student who already filed or is approved: no filing window or DSO range; no EAD range once approved.
2. Window closed, conflict, or more than 12 months out: `ranges == []` and the timeline shows the existing warning, not an empty page.
3. Leaving mid-setup and signing in again resumes at the first unfinished step, not Step 1 and not Checklist.
4. An existing account with stage and dates set but no offer lands on Step 4 (offer), with earlier answers kept.
5. Entering a DSO date in the range editor that conflicts with the window shows the API's error in the editor and the CONFLICT warning after save, never a blank timeline.

---

### Task 1: Backend — `Plan.ranges`

**Files:**
- Create: `backend/app/opt/ranges.py`
- Modify: `backend/app/schemas/opt.py` (new enums/model next to `Plan`; `Plan.ranges: list[TimelineRange]`)
- Modify: `backend/app/mock/opt_demo.py` (`build_plan` sets `ranges=build_ranges(profile, timeline)`)
- Test: `backend/tests/test_ranges.py`

**Interfaces:**
- Produces: `RangeKind`, `RangeAction`, `TimelineRange` exactly as in the spec's "Backend" section; JSON key `ranges` on `GET /api/me/opt-plan`.
- Produces: `build_ranges(profile: Profile, timeline: TimelineResult) -> list[TimelineRange]` in `app/opt/ranges.py`, ranges sorted by `start`.

Rules (spec table, with one refinement: FILING_WINDOW is dropped once the student has filed):

| id | shown when | start | end | related_task_ids | action |
|---|---|---|---|---|---|
| FILING_WINDOW | N2 and N4 dated and `uscis_receipt_date` is None | N2 | N4 | `["T05"]` | CONFIRM_WITH_SCHOOL |
| EAD_ARRIVAL | filing date (receipt or N3) known and stage ≠ APPROVED | filing + USCIS min | filing + USCIS max | `["T06"]` | ADJUST_PROCESSING |
| DSO_REC_DATE | `dso_rec_date` None and stage in (None, PLANNING, I20_REQUESTED) and base (i20_request_date or N1) known | base + school min | base + school max | `["T03"]` | ENTER_DSO_REC_DATE |
| START_DATE | `offer` set, `has_offer` False, `start_preference` in (None, NOT_SURE) | P + 1 | P + 60 | `["T05"]` | PICK_START_DATE |

USCIS entry = `uscis_premium_business_days` when `offer.premium_intent == YES`, else `uscis_standard_days`. Min/max
come from `opt_demo.processing_times(profile)`; `unit == "business_days"` → `add_business_days`, else `timedelta(days=…)`.

- [ ] **Step 1: Write the failing tests** in `tests/test_ranges.py` (use `client`, `auth` fixtures; `auth` loads `demo_profile()`: P 2027-06-11, offer start 2027-07-12, stage PLANNING, no R):

```python
def _plan(client, auth): return client.get("/api/me/opt-plan", headers=auth).json()
def _ranges(plan): return {r["id"]: r for r in plan["ranges"]}
def _node(plan, i): return date.fromisoformat(next(n for n in plan["nodes"] if n["id"] == i)["date"])

def test_demo_student_gets_window_ead_and_dso_ranges(client, auth):
    plan = _plan(client, auth); r = _ranges(plan)
    assert set(r) == {"FILING_WINDOW", "EAD_ARRIVAL", "DSO_REC_DATE"}
    assert r["FILING_WINDOW"]["kind"] == "LEGAL_WINDOW"
    assert (r["FILING_WINDOW"]["start"], r["FILING_WINDOW"]["end"]) == (str(_node(plan, "N2")), str(_node(plan, "N4")))
    n3 = _node(plan, "N3")
    assert (r["EAD_ARRIVAL"]["start"], r["EAD_ARRIVAL"]["end"]) == (str(n3 + timedelta(90)), str(n3 + timedelta(150)))
    n1 = _node(plan, "N1")
    assert r["DSO_REC_DATE"]["start"] == str(add_business_days(n1, 20))
    assert r["DSO_REC_DATE"]["end"] == str(add_business_days(n1, 28))
    assert [x["start"] for x in plan["ranges"]] == sorted(x["start"] for x in plan["ranges"])

def test_dso_range_gone_once_r_known(client, auth): ...      # PUT /status I20_RECEIVED + dso_rec_date 2027-03-20 → no DSO_REC_DATE; FILING_WINDOW == (R, R+30)
def test_premium_uses_business_day_range(client, auth): ...  # PUT /offer premium_intent YES → EAD = add_business_days(N3, 1)..(N3, 30)
def test_after_filing_no_window_and_ead_from_receipt(client, auth): ...  # stage I765_FILED, receipt 2027-03-25 → no FILING_WINDOW; EAD starts 2027-06-23
def test_approved_has_no_ead_range(client, auth): ...        # stage APPROVED → "EAD_ARRIVAL" not in ranges
def test_no_offer_not_sure_gets_start_date_range(client, auth): ...  # PUT /offer has_offer False, start_preference NOT_SURE → START_DATE 2027-06-12..2027-08-10, kind NEEDS_DATE
def test_conflict_or_closed_window_has_no_ranges(client, auth): ...  # R 2027-02-01 (conflict) → ranges == []
```

Fill each `...` with the setup call in its comment and the stated assertions.

- [ ] **Step 2: Run** `cd backend && .venv/bin/pytest -q tests/test_ranges.py` — expected: FAIL (`KeyError: 'ranges'`).
- [ ] **Step 3: Implement** the schema, `build_ranges`, and the `build_plan` wiring. Labels/notes (exact copy):
  - FILING_WINDOW: "You can file Form I-765" / "The legal filing window. It narrows to 30 days after your DSO recommendation once you enter it. Confirm with UW ISS."
  - EAD_ARRIVAL: "EAD card expected" / "Based on USCIS processing of {min}–{max} {days|business days} after filing. Adjust if you have better information."
  - DSO_REC_DATE: "DSO recommendation date (expected)" / "We estimate this until you enter the date from your OPT I-20."
  - START_DATE: "Choose your OPT start date" / "Your start date must be within 60 days after your program end date."
- [ ] **Step 4: Run** `.venv/bin/pytest -q` — expected: all pass (316 existing + new).
- [ ] **Step 5: Commit** `feat: date ranges on the OPT plan (filing window, EAD estimate, missing dates)`.

### Task 2: Frontend — types, setup state, range actions

**Files:**
- Modify: `frontend/lib/api.ts` (types), `frontend/lib/demo.ts` (state + actions)

**Interfaces:**
- Consumes: Task 1 JSON.
- Produces (api.ts): `export type ApiRange = { id: "FILING_WINDOW" | "EAD_ARRIVAL" | "DSO_REC_DATE" | "START_DATE"; kind: "LEGAL_WINDOW" | "ESTIMATE" | "NEEDS_DATE"; label: string; start: string; end: string; note: string; action: "CONFIRM_WITH_SCHOOL" | "ADJUST_PROCESSING" | "ENTER_DSO_REC_DATE" | "PICK_START_DATE"; related_task_ids: string[] }`; `ApiPlan.ranges: ApiRange[]`.
- Produces (demo.ts):
  - `export type SetupStep = "program" | "opt" | "progress" | "offer" | "done"`
  - `export function nextSetupStep(p: ApiProfile | null): SetupStep` — `null` → program; `opt_selection` missing or not (`AFTER_GRADUATION` and `first_time_at_level`) → opt; `stage === null` → progress; `offer === null` → offer; else done.
  - State gains `setupStep: SetupStep`, set in `refresh()` from the raw `ApiProfile` (`onboarding_required` → `"program"`; no token → `"program"`). `useDemoProfile()` returns `setupStep`.
  - `actions.verify` returns `SetupStep` instead of `onboarded` boolean (update the login page caller: `"done"` → `/checklist`, else `/setup`).
  - `actions.enterDsoRecDate(date: string)` → `PUT /api/me/status` with `stage: "I20_RECEIVED"`, current stage dates, `dso_rec_date: date`; then `refresh()`.
  - `actions.pickStartDate(date: string)` → `PUT /api/me/offer` with current offer fields, `has_offer: false`, `start_preference: "SPECIFIC_DATE"`, `preferred_start_date: date`; then `refresh()`.

- [ ] **Step 1: Implement** the types, `nextSetupStep`, state field and actions above; update `app/login/page.tsx` routing.
- [ ] **Step 2: Verify** `cd frontend && npx tsc --noEmit` — expected: no output.
- [ ] **Step 3: Commit** `feat(frontend): setup-step state and range edit actions`.

### Task 3: Frontend — extract offer and processing forms

**Files:**
- Create: `frontend/components/OfferForm.tsx`, `frontend/components/ProcessingTimesForm.tsx`
- Modify: `frontend/app/opt/timeline/page.tsx` (use the two components; behavior unchanged)

**Interfaces:**
- Produces: `OfferForm({ onSaved, submitLabel }: { onSaved: () => void; submitLabel: string })` — the "Plan your next steps" panel body from `opt/timeline` (has offer / start date / flexible / start preference / premium), saving via `actions.calculateTimeline`.
- Produces: `ProcessingTimesForm({ onSaved, onSkip }: { onSaved: () => void; onSkip?: () => void })` — the existing processing-time panel body (from the function at the bottom of `opt/timeline/page.tsx`), saving via `actions.saveProcessingTimes`; renders a "Skip" button only when `onSkip` is given.

- [ ] **Step 1: Move** the JSX and handlers into the components; `opt/timeline` renders them in its existing panels.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run build` pass; in the browser `/opt/timeline` still saves an offer and a processing time (network shows `PUT /api/me/offer` 200 and `PUT /api/me/processing-times` 200).
- [ ] **Step 3: Commit** `refactor(frontend): reusable offer and processing-time forms`.

### Task 4: Frontend — `VerticalTimeline` with range editors

**Files:**
- Create: `frontend/components/VerticalTimeline.tsx`

**Interfaces:**
- Consumes: `ApiPlan` (with `ranges`), `actions.enterDsoRecDate`, `actions.pickStartDate`, `ProcessingTimesForm` (Task 3).
- Produces: `VerticalTimeline({ plan }: { plan: ApiPlan })`.

Layout (approved mockup A): one column, items sorted by date — task cards at `due_at ?? deadline_at` (undated tasks
last), range blocks at `start`, and a "Today" divider at today's date. Task card: `T0x · title`, chip from status /
`due_type` (Done ✓, Recommended date, Estimate, Your date, Federal deadline). Range block: label, `formatDate(start)
– formatDate(end)`, note, and an action control:
- CONFIRM_WITH_SCHOOL → link "Confirm with UW ISS ↗" to `https://iss.washington.edu/`.
- ENTER_DSO_REC_DATE → "Enter date when you get it" expands an inline date input + Save.
- PICK_START_DATE → "Pick a start date" expands an inline date input (min P+1, max P+60 = the range's start/end) + Save.
- ADJUST_PROCESSING → "Adjust processing time" expands `ProcessingTimesForm`.
Editor errors show under the editor (`role="alert"`). A legend with the three colors sits above the column. If
`plan.risk_labels` includes WINDOW_CLOSED, CONFLICT or OUT_OF_SCOPE, show the matching warning card above the column.

- [ ] **Step 1: Implement** the component per the layout above.
- [ ] **Step 2: Verify** `npx tsc --noEmit` passes.
- [ ] **Step 3: Commit** `feat(frontend): vertical timeline with colored ranges and inline editors`.

### Task 5: Frontend — `/setup` wizard

**Files:**
- Create: `frontend/app/setup/page.tsx`
- Modify: `frontend/app/onboarding/page.tsx` (becomes a `router.replace("/setup")` redirect)

**Interfaces:**
- Consumes: `useDemoProfile().setupStep`, `actions.onboard`, `actions.selectOpt`, `actions.saveStatus`, `OfferForm`, `ProcessingTimesForm`, `VerticalTimeline`.

Steps (header "Step N of 6", Back/Continue): 1 program (school read-only UW, degree, Program End Date — from
`onboarding`), 2 OPT path (from `opt/select`, same out-of-scope copy, Continue disabled when out of scope),
3 progress (stage + dates — from `opt/status`, same required-date rules), 4 offer (`OfferForm`), 5 processing
(`ProcessingTimesForm` with `onSkip`), 6 timeline (`VerticalTimeline` + primary "Go to My Checklist →" to `/checklist`).
On load the wizard opens at `setupStep` (`"done"` opens Step 6); Back moves within the wizard and keeps saved
answers. Local step state resets in a `useLayoutEffect` cleanup. `Shell showNav={false}`.

- [ ] **Step 1: Implement** the page and the `/onboarding` redirect.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run build` pass.
- [ ] **Step 3: Commit** `feat(frontend): six-step setup wizard`.

### Task 6: Frontend — routing guards

**Files:**
- Modify: `frontend/components/Shell.tsx`, `frontend/app/checklist/page.tsx`, `frontend/app/home/page.tsx`

**Interfaces:**
- Consumes: `useDemoProfile().setupStep`, `ready`.

- `Shell` with `showNav` true: when `ready`, signed in (`getToken()`), and `setupStep !== "done"` → `router.replace("/setup")`.
- Start over (checklist) pushes `/setup`. Restore (home): after `restorePlan`, if the refreshed `setupStep !== "done"` push `/setup`.

- [ ] **Step 1: Implement** the guard and the two redirects.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run build` pass.
- [ ] **Step 3: Commit** `feat(frontend): send incomplete setups to /setup`.

### Task 7: Frontend — `/opt/timeline` uses `VerticalTimeline`

**Files:**
- Modify: `frontend/app/opt/timeline/page.tsx`

- [ ] **Step 1: Replace** the "Timeline milestones" panel with `<VerticalTimeline plan={plan} />`; keep the offer and processing panels and the policy notes. Remove helpers that become unused.
- [ ] **Step 2: Verify** `npx tsc --noEmit && npm run build` pass.
- [ ] **Step 3: Commit** `feat(frontend): timeline page uses the vertical timeline`.

### Task 8: End-to-end check

- [ ] **Step 1:** `cd backend && .venv/bin/pytest -q` — all pass.
- [ ] **Step 2:** Run backend (`uvicorn app.main:app --port 8000`) and frontend (`npm run dev -- --port 3000`); in the browser:
  - New account → Step 1 … Step 6 → Checklist; nav hidden throughout `/setup`.
  - New account → stop after Step 3 → sign in again → lands on Step 4 (Review Focus 3, 4).
  - Step 2 "While I'm still studying" → blocked with UW ISS copy; switching back to "After I graduate" continues.
  - Step 6: each range color present for the demo inputs; enter a DSO date (2027-03-20) → DSO range disappears, window narrows; enter 2027-02-01 → conflict warning shown (Review Focus 5); adjust processing → EAD range moves.
  - Visiting `/checklist` mid-setup redirects to `/setup`.
- [ ] **Step 3:** Revert `frontend/next-env.d.ts` if `next dev` changed it; leave `frontend/AGENTS.md` uncommitted.
