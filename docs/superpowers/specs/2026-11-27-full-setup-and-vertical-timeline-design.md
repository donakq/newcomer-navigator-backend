# Full Setup Wizard and Vertical Timeline — Design

Date: 2026-11-27 · Branch: `feat/full-setup-wizard` · Status: waiting for approval

## Why

A new student today answers only School, Degree and Program End Date, then lands on My Checklist. The rest of
"Your situation" (OPT path, current stage and its dates, offer or start preference, processing times) is
scattered over `/opt/select`, `/opt/status` and `/opt/timeline`, so most students reach the Checklist before the
plan can compute a real timeline or the right tasks. We want every input collected up front, then a timeline the
student can read before entering the app.

## Goals

- First sign-in runs one guided setup that asks everything the plan needs.
- Setup ends with a **vertical timeline**: tasks placed at their dates, plus date ranges in three colors:
  - **Green — legal window** (confirm with the DSO), e.g. "You can file I-765: Mar 13 – Aug 10".
  - **Amber — estimate** (student can adjust), e.g. "EAD card expected: Jun 28 – Jul 20".
  - **Gray dashed — waiting for a real date**, e.g. "DSO recommendation date: Mar 16 – Apr 3?".
- Only after setup is complete does the student see the normal signed-in pages (My Checklist by default).

## Non-goals

- New OPT types (pre-completion, STEM): still out of scope; the wizard stops and refers to UW ISS.
- Changing date rules in the timeline engine (`app/opt/timeline.py`). Ranges are derived from what it already
  computes plus the processing-time min/max.
- Real email codes (still `000000`).

## Anti-goals

- A wizard that loses answers when the student leaves halfway.
- Ranges that look certain when they are estimates; every range says what kind it is and what to do.

## Approaches considered

1. **One `/setup` route with six steps (chosen).** A single page holds the step state, saves each step through
   the existing endpoints, and resumes at the first unfinished step. One place to guard and to restyle.
2. Chain the existing pages (`/onboarding` → `/opt/select` → `/opt/status` → `/opt/timeline`) with a progress bar.
   Less new code, but four pages with their own navigation and the app nav visible mid-setup; hard to guarantee
   "no app pages until setup is done".
3. One long form on a single screen. Fast to build, but conditional fields (stage dates, offer vs no offer) make a
   long, confusing page on a phone.

The student picked the vertical timeline (layout A) over a horizontal Gantt layout, because it reads like an
ordered to-do list and works on phones.

## The flow (agreed)

```
Step 1  School & program   School (UW) · Degree · Program End Date
Step 2  OPT path           When will you use OPT · First time at this degree level
Step 3  Current progress   Planning / I-20 requested / I-20 received / I-765 filed / Approved + that stage's dates
Step 4  Job offer          Yes: start date, flexible?   No: start preference (ASAP / date / not sure), premium?
Step 5  Processing times   School and USCIS times; defaults are the conservative maximum; "Skip" keeps defaults
Step 6  Your timeline      Vertical timeline → "Go to My Checklist"
```

Agreed details:
- **Out of scope** (Step 2 not "after graduation", or not first time): stop at Step 2 with the existing UW ISS
  referral copy. No way forward.
- **Resume**: each step saves when the student continues. On sign-in, a student whose setup is incomplete goes
  to `/setup` at the first unfinished step; complete → `/checklist`.
- **Later edits** keep using Home's links ("Change OPT selection", "Update status") and the existing pages.
- **`/opt/timeline`** uses the same vertical timeline component as Step 6.
- **Ranges come from the backend** in the plan; the frontend only draws them.
- **Range actions open a small inline editor** (on Step 6 and on `/opt/timeline`); saving recomputes the plan.

## Backend

### `Plan.ranges` (new field)

```python
class RangeKind(str, Enum):
    LEGAL_WINDOW = "LEGAL_WINDOW"   # green
    ESTIMATE = "ESTIMATE"           # amber
    NEEDS_DATE = "NEEDS_DATE"       # gray dashed

class RangeAction(str, Enum):
    CONFIRM_WITH_SCHOOL = "CONFIRM_WITH_SCHOOL"   # link to UW ISS, nothing to edit
    ADJUST_PROCESSING = "ADJUST_PROCESSING"       # edit processing_times
    ENTER_DSO_REC_DATE = "ENTER_DSO_REC_DATE"     # PUT /me/status with I20_RECEIVED + dso_rec_date
    PICK_START_DATE = "PICK_START_DATE"           # PUT /me/offer with SPECIFIC_DATE + preferred_start_date

class TimelineRange(BaseModel):
    id: str              # FILING_WINDOW | EAD_ARRIVAL | DSO_REC_DATE | START_DATE
    kind: RangeKind
    label: str           # "You can file Form I-765"
    start: date
    end: date
    note: str            # one sentence on what the range means / what changes it
    action: RangeAction
    related_task_ids: list[str]
```

Which ranges, when (all omitted when the needed nodes are missing, e.g. window closed, conflict, too early):

| id | kind | start – end | when shown |
|---|---|---|---|
| FILING_WINDOW | LEGAL_WINDOW | N2 – N4 | until the student has filed (narrows to R..R+30 once R is known) |
| EAD_ARRIVAL | ESTIMATE | filing date + min USCIS time – filing date + the student's USCIS time (default = official max) | before approval |
| DSO_REC_DATE | NEEDS_DATE | (I-20 request date or N1) + min school time – + max school time | R unknown and stage before I20_RECEIVED |
| START_DATE | NEEDS_DATE | P+1 – P+60 | no offer and start preference NOT_SURE |

"Filing date" = USCIS receipt date if filed, else N3. Min/max come from the existing `ProcessingTime` entries
(`min`, `max`, `unit`); business-day units use `app/opt/business_days.py`. Premium processing uses the premium
entry.

### Setup completeness

Computed by the frontend from the profile it already loads (no API change):
complete = profile exists **and** OPT selection is post-completion + first time **and** stage is set **and**
offer is set (`has_offer` answered with its required date/preference). Processing times are optional.

## Frontend

- **`/setup`** (new): steps 1–6 above, progress indicator "Step N of 6", Back/Continue, `Shell showNav={false}`.
  Reuses the field logic from `onboarding`, `opt/select`, `opt/status` and the offer/processing forms on
  `opt/timeline`. Each Continue calls the existing endpoint (`PUT /me/onboarding`, `/opt-selection`, `/status`,
  `/offer`, `/processing-times`). Step 5 "Skip" saves nothing.
- **`VerticalTimeline`** component (new, `components/`): one sorted column of task cards (at `due_at`, else
  `deadline_at`; tasks without a date at the end) and range blocks (at `start`), a "Today" divider, color legend,
  status chips (Done / Recommended date / Estimate / Your date). Each range shows its action; clicking opens the
  inline editor for that action and refreshes the plan after saving.
- **Routing**: `/onboarding` redirects to `/setup`. Login sends incomplete setups to `/setup`, complete ones to
  `/checklist`. App pages (`Shell` with nav) redirect to `/setup` when signed in and setup is incomplete. Start
  over sends to `/setup`. Restore from History: if the restored plan is incomplete, the student lands in `/setup`.
  Existing pre-prod accounts with partial data are sent to `/setup` at their first unfinished step (my call:
  no data migration needed).
- **`/opt/timeline`**: replace the "Timeline milestones" panel with `VerticalTimeline`; keep the existing input
  and processing-time panels.
- Next 16 keeps hidden pages mounted (`cacheComponents`): the wizard resets its local state when hidden, as the
  onboarding form already does.

## Testing

- Backend (pytest): each range's presence and dates for the PRD 6.4 example and edge cases (R known/unknown,
  no offer + NOT_SURE, premium, filed, window closed, conflict, too early). Existing tests stay green.
- Frontend: `tsc` + `npm run build`; browser run of a new student through all six steps, leaving at Step 3 and
  resuming, an out-of-scope answer at Step 2, and each range action on Step 6.

## Left to the builder

- Exact copy for range notes and step hints (plain English, PRD tone; no legal advice wording).
- Visual details within the existing green/cream palette; colors as in the approved mockup.
- Whether Step 6's editor is a popover or an inline expand, as long as it stays on the timeline.
