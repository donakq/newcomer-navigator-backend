# API Skeleton + Rules Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every endpoint in the design returns real, schema-valid responses driven by a YAML task catalog and a rules engine, so the frontend can build against a deployed API before the database and AI scenarios exist.

**Architecture:** FastAPI routers call small service modules. Content (tasks, steps, events) is loaded from `catalog/` YAML at startup and validated with Pydantic. User state goes through a `Store` interface; this plan ships an in-memory implementation (a later plan adds Postgres behind the same interface). AI is limited to one smoke call in `/api/chat`; the four AI scenarios are a later plan.

**Tech Stack:** Python 3.11, FastAPI 0.162.2, Pydantic 2.14.3, PyYAML 6.0.3, anthropic 2.6.0, pytest 9.2.0, httpx 0.28.1.

**Spec:** `DS_ML/docs/system-design/Case Studies/Newcomer Navigator/Newcomer Navigator Backend Design.md` and `Newcomer Navigator Data Model.md` (Obsidian vault). Section numbers below refer to those pages.

## Global Constraints

- Every request carries header `X-User-Id` (UUID v4). Missing or malformed → HTTP 400.
- All errors use the body `{"error": {"code": str, "message": str}}`, including FastAPI validation errors (code `validation_error`, HTTP 422).
- Never store or echo SSN, passport, I-20 or SEVIS numbers. Profile fields are booleans/enums/dates only (Data Model §2).
- Profile fields default to `None` meaning "unknown". A condition never matches a `None` value (see Task 3).
- Task/step ids come only from the catalog; any id not in the catalog → HTTP 404, code `not_found`.
- Pin exact dependency versions in `requirements*.txt`.
- Run tests with `.venv/bin/pytest -q` from the repo root.

## Review Focus

1. **Unknown profile answers** — a student who skipped "Do you have an SSN?" must not be told to get one or told they are done; `None` matches no condition. Pinned in Task 3.
2. **Dismissed tasks coming back** — after a student dismisses a task, a later profile update must not re-add it. Pinned in Task 5.
3. **Started tasks disappearing** — a task with any completed step that no longer matches the rules stays and is flagged `maybe_not_applicable`. Pinned in Task 5.
4. **Missing/garbage `X-User-Id`** — returns 400 in the error format, not a 500 or a silent new user. Pinned in Task 1.
5. **Broken catalog YAML** — duplicate task ids, duplicate step ids, unknown profile field in `when` or `personalize_on`, or `depends_on` pointing to a missing task must fail at load time (tests), not at request time. Pinned in Task 2.

---

## File Structure

```
app/
  errors.py              # ApiError + exception handlers (error format)
  deps.py                # current_user dependency (X-User-Id)
  schemas/
    profile.py           # Profile
    api.py               # Source, ChecklistDiff, ChecklistItem, Step, TaskDetail, Citation, ChatRequest, ChatResponse, DsoDraft, ...
    catalog.py           # Condition, CatalogStep, CatalogTask, CatalogEvent, Catalog
  catalog_loader.py      # load_catalog(path) -> Catalog, get_catalog()
  services/
    rules.py             # evaluate, recommend
    store.py             # Store protocol + InMemoryStore + get_store()
    checklist.py         # recompute_checklist, list_checklist, add_or_dismiss
    profile.py           # update_profile
    tasks.py             # get_task_detail, set_step_done
    chat.py              # handle_chat, draft_dso_email
  ai/client.py           # complete(system, user, model) -> str
  routers/               # profile.py checklist.py tasks.py chat.py (exist, empty)
catalog/
  tasks/ssn.yaml  bank_account.yaml  us_phone.yaml   # placeholder content, marked TODO
  events.yaml
tests/
  test_errors.py test_catalog.py test_rules.py test_checklist.py
  test_store.py test_profile_api.py test_tasks_api.py test_chat_api.py
  conftest.py            # client fixture with fresh InMemoryStore + header helper
```

---

### Task 1: Error format and identity

**Files:**
- Create: `app/errors.py`, `app/deps.py`, `tests/conftest.py`, `tests/test_errors.py`
- Modify: `app/main.py` (register handlers)

**Interfaces:**
- Produces: `class ApiError(Exception)` with `__init__(self, status: int, code: str, message: str)`; `register_error_handlers(app: FastAPI) -> None`; `current_user(x_user_id: str | None = Header(None)) -> UUID` (raises `ApiError(400, "bad_user_id", ...)`).
- Produces (tests): fixture `client` (TestClient on `app`), helper `H = {"X-User-Id": "<fixed uuid4>"}` in `conftest.py`.

- [ ] **Step 1: Write failing tests** in `tests/test_errors.py`:
  - `test_missing_user_id_returns_400`: add a throwaway route in the test (`@app.get("/api/_whoami")` depending on `current_user`) or call `/api/profile` once Task 4 lands — for now mount a test-only route via `app.get` inside the test module. Assert `status_code == 400` and `json()["error"]["code"] == "bad_user_id"`.
  - `test_malformed_user_id_returns_400`: header `X-User-Id: not-a-uuid` → same assertions.
  - `test_valid_user_id_passes`: header `H` → 200 and body echoes the UUID string.
  - `test_validation_error_uses_error_format`: POST a body with wrong type to a test-only route with a Pydantic body → 422 and `json()["error"]["code"] == "validation_error"`.
- [ ] **Step 2: Run** `.venv/bin/pytest tests/test_errors.py -q` → FAIL (import error).
- [ ] **Step 3: Implement** `ApiError`, handlers for `ApiError` and `RequestValidationError` (message = first error's `msg`), and `current_user` using `uuid.UUID(value)` in try/except. Call `register_error_handlers(app)` in `app/main.py`.
- [ ] **Step 4: Run** `.venv/bin/pytest -q` → all PASS.
- [ ] **Step 5: Commit** `git commit -am "feat: error format and X-User-Id identity"` (add new files first).

---

### Task 2: Catalog schemas, loader, placeholder content

**Files:**
- Create: `app/schemas/profile.py`, `app/schemas/catalog.py`, `app/catalog_loader.py`, `catalog/tasks/ssn.yaml`, `catalog/tasks/bank_account.yaml`, `catalog/tasks/us_phone.yaml`, `tests/test_catalog.py`
- Modify: `catalog/events.yaml`

**Interfaces:**
- Produces: `Profile` exactly as Data Model §2 (all fields optional, `visa: Literal["F-1"] = "F-1"`, `state: Literal["WA"] = "WA"`), with `model_config = ConfigDict(extra="forbid")`.
- Produces: `Condition = dict[str, Any]` (validated by loader, see Step 3); `CatalogStep(id: str, title: str, materials: list[str] = [], sources: list[SourceRef] = [], when: Condition | None = None)`; `SourceRef(url: str, title: str | None = None, verified_at: date)`; `CatalogTask(id, version: int, title, when: Condition, reason: str, depends_on: list[str] = [], personalize_on: list[str] = [], steps: list[CatalogStep])`; `CatalogEvent(id, description, profile_updates: dict[str, Any] = {}, extract_fields: list[str] = [])`; `Catalog(tasks: dict[str, CatalogTask], events: dict[str, CatalogEvent])`.
- Produces: `load_catalog(root: Path) -> Catalog` (raises `ValueError` with the offending file/id in the message); `get_catalog() -> Catalog` (cached, loads `<repo>/catalog`).

- [ ] **Step 1: Write failing tests** in `tests/test_catalog.py` (use `tmp_path` to write small YAML fixtures):
  - `test_loads_repo_catalog`: `get_catalog()` contains task ids `{"ssn", "bank_account", "us_phone"}` and event `"GOT_JOB_OFFER"`.
  - `test_duplicate_task_id_rejected`, `test_duplicate_step_id_rejected`
  - `test_unknown_field_in_when_rejected` (e.g. `{field: has_ssnn, eq: false}`)
  - `test_unknown_field_in_personalize_on_rejected`
  - `test_unknown_depends_on_rejected`
  - `test_bad_condition_operator_rejected` (e.g. `{field: has_ssn, gt: 1}`)
  - `test_event_extract_field_must_be_profile_field`
  Each rejection test asserts `pytest.raises(ValueError)`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Allowed condition shapes: `{"all": [...]}`, `{"any": [...]}`, `{"not": {...}}`, `{"field": f, "eq": v}`, `{"field": f, "in": [...]}`; `f` must be in `Profile.model_fields`. Validate recursively in the loader. One YAML file per task under `catalog/tasks/`; `events.yaml` is a list.
- [ ] **Step 4: Write placeholder content.** Every file starts with `# TODO(content): placeholder — replace with team-verified content`. Use these rules (structure only, wording is placeholder):
  - `ssn`: `when: all[has_ssn eq false, has_job_offer eq true]`, `personalize_on: [job_type, arrival_date, school]`, steps `cpt_authorization` (`when: {field: job_type, eq: CPT}`), `dso_letter`, `ssa_visit`.
  - `us_phone`: `when: all[in_us eq true, has_us_phone eq false]`, steps `choose_plan`, `activate_sim`.
  - `bank_account`: `when: all[in_us eq true, has_bank_account eq false]`, `depends_on: [us_phone]`, steps `choose_bank`, `prepare_documents`, `open_account`.
  - `events.yaml`: `ARRIVED_US` (`profile_updates: {in_us: true}`, `extract_fields: [arrival_date]`), `GOT_JOB_OFFER` (`{has_job_offer: true}`, `[job_type]`), `GOT_SSN` (`{has_ssn: true}`), `GOT_PHONE` (`{has_us_phone: true}`), `OPENED_BANK_ACCOUNT` (`{has_bank_account: true}`).
  - Every step gets one `sources` entry with `url: https://example.com/TODO` and `verified_at: 2026-11-08`.
- [ ] **Step 5: Run** `.venv/bin/pytest -q` → PASS.
- [ ] **Step 6: Commit** `feat: task catalog schema, loader, placeholder content`.

---

### Task 3: Rules engine

**Files:**
- Create: `app/services/rules.py`, `tests/test_rules.py`

**Interfaces:**
- Consumes: `Catalog`, `CatalogTask`, `Profile` (Task 2).
- Produces: `evaluate(cond: Condition, profile: dict[str, Any]) -> bool`; `Recommendation(task_id: str, reason: str, blocked_by: list[str])` (Pydantic or dataclass); `recommend(profile: Profile, catalog: Catalog, done_task_ids: set[str] = frozenset()) -> list[Recommendation]` (ordered by catalog file name); `visible_steps(task: CatalogTask, profile: Profile) -> list[CatalogStep]`.

- [ ] **Step 1: Write failing tests:**
  - `test_eq_none_never_matches`: `evaluate({"field": "has_ssn", "eq": False}, {"has_ssn": None}) is False` and same for missing key.
  - `test_in_none_never_matches`
  - `test_all_any_not` (one assert each)
  - `test_new_arrival_gets_phone_and_bank`: `Profile(in_us=True, has_us_phone=False, has_bank_account=False)` → ids `["bank_account", "us_phone"]` (catalog order), and `bank_account.blocked_by == ["us_phone"]`.
  - `test_blocked_by_clears_when_dependency_done`: same profile, `done_task_ids={"us_phone"}` → `bank_account.blocked_by == []`.
  - `test_job_offer_without_ssn_gets_ssn`: `Profile(has_ssn=False, has_job_offer=True)` → `"ssn"` present with the YAML `reason`.
  - `test_unknown_ssn_status_gets_no_ssn_task`: `Profile(has_job_offer=True)` → `"ssn"` absent.
  - `test_cpt_step_only_for_cpt`: `visible_steps(ssn, Profile(job_type="CPT"))` ids start with `"cpt_authorization"`; with `job_type="on_campus"` it is absent.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** (pure functions, no I/O). `blocked_by` = `depends_on` entries not in `done_task_ids`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: rules engine`.

---

### Task 4: Store and API schemas

**Files:**
- Create: `app/services/store.py`, `app/schemas/api.py`
- Modify: `tests/conftest.py` (fixture resets store)

**Interfaces:**
- Produces: `UserTask(task_id: str, status: Literal["not_started","in_progress","done"], source: Literal["rule","chat","manual"], dismissed: bool = False, maybe_not_applicable: bool = False)`.
- Produces: `class Store(Protocol)` with `get_profile(uid) -> Profile`, `save_profile(uid, p: Profile) -> None`, `get_user_tasks(uid) -> dict[str, UserTask]`, `save_user_task(uid, t: UserTask) -> None`, `delete_user_task(uid, task_id) -> None`, `get_done_steps(uid, task_id) -> set[str]`, `set_step(uid, task_id, step_id, done: bool) -> None`, `append_message(uid, role: str, content: str, meta: dict) -> None`; `InMemoryStore` implementing it; `get_store() -> Store` (module singleton, FastAPI dependency); `reset_store() -> None` for tests.
- Produces: API models exactly as Data Model §4.1: `Source`, `ChecklistDiff(added, removed, flagged)`, `ChecklistItem`, `Step`, `TaskDetail`, `Citation`, `ChatResponse`, `DsoDraft`; plus `ProfileUpdateRequest(answers: dict[str, Any])`, `ChecklistActionRequest(action: Literal["add","dismiss"])`, `StepUpdateRequest(done: bool)`, `ChatRequest(message: str = Field(min_length=1, max_length=2000))`, `DsoDraftRequest(question: str | None = Field(None, max_length=2000))`.

- [ ] **Step 1: Write failing test** `tests/test_store.py::test_in_memory_roundtrip`: save profile, save a `UserTask`, `set_step(..., True)` then `False`, assert reads reflect each write and two user ids don't see each other's data.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: store interface, in-memory store, API schemas`.

---

### Task 5: Profile and checklist endpoints

**Files:**
- Create: `app/services/checklist.py`, `app/services/profile.py`, `tests/test_checklist.py`, `tests/test_profile_api.py`
- Modify: `app/routers/profile.py`, `app/routers/checklist.py`

**Interfaces:**
- Consumes: `recommend`, `visible_steps` (Task 3); `Store`, API models (Task 4); `current_user` (Task 1).
- Produces: `recompute_checklist(store, uid, profile, source: Literal["rule","chat"]) -> ChecklistDiff`; `list_checklist(store, uid) -> list[ChecklistItem]` (services call `get_catalog()` themselves; no catalog parameter); `update_profile(store, uid, patch: dict, source) -> tuple[Profile, ChecklistDiff]`; `task_progress(store, uid, task, profile) -> tuple[status, float]` (done visible steps ÷ visible steps; 0.0 when none).
- Endpoints: `GET /api/profile` → `{"profile": Profile}`; `POST /api/profile` body `ProfileUpdateRequest` → `{"profile", "checklist_diff"}`; `GET /api/checklist` → `{"tasks": [ChecklistItem]}` (dismissed excluded); `POST /api/checklist/{task_id}` body `ChecklistActionRequest` → `{"task": ChecklistItem}`.

- [ ] **Step 1: Write failing tests:**
  - `test_profile_merge_not_overwrite`: POST `{in_us: true}` then `{has_ssn: false}` → GET shows both.
  - `test_unknown_profile_field_422`: POST `{answers: {ssn_number: "123"}}` → 422 `validation_error`.
  - `test_profile_post_returns_diff`: new user POSTs `{in_us: true, has_us_phone: false, has_bank_account: false}` → `checklist_diff.added == ["bank_account", "us_phone"]`.
  - `test_unmatched_not_started_task_removed`: then POST `{has_us_phone: true}` → `"us_phone"` in `removed`, not in GET checklist.
  - `test_started_task_flagged_not_removed`: mark a `us_phone` step done (via `store.set_step` directly), then POST `{has_us_phone: true}` → `"us_phone"` in `flagged`, still listed with `maybe_not_applicable: true`.
  - `test_dismissed_task_not_readded`: dismiss `bank_account`, POST an unrelated field → `bank_account` not in `added`, not in GET checklist.
  - `test_manual_add_unknown_task_404`.
  - `test_checklist_item_fields`: item for `bank_account` has `reason` from YAML, `blocked_by == ["us_phone"]`, `progress == 0.0`, `status == "not_started"`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** A task counts as "done" for `blocked_by` when its status is `done`. A task counts as "started" when `get_done_steps` is non-empty (do not rely on the stored status). In `update_profile`, catch Pydantic `ValidationError` from merging and raise `ApiError(422, "validation_error", <first msg>)`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: profile and checklist endpoints`.

---

### Task 6: Task detail and step progress endpoints

**Files:**
- Create: `app/services/tasks.py`, `tests/test_tasks_api.py`
- Modify: `app/routers/tasks.py`

**Interfaces:**
- Consumes: Tasks 3–5.
- Produces: `get_task_detail(store, uid, task_id) -> TaskDetail` (`personalized=False`, `note=None`, `warnings=[]` until the AI plan); `set_step_done(store, uid, task_id, step_id, done) -> dict` returning `{"step": Step, "task_status": str, "progress": float}`.
- Endpoints: `GET /api/tasks/{task_id}` → `TaskDetail`; `PATCH /api/tasks/{task_id}/steps/{step_id}` body `StepUpdateRequest`.

- [ ] **Step 1: Write failing tests:**
  - `test_task_detail_shape`: GET `ssn` for a CPT profile → `personalized is False`, step ids `["cpt_authorization", "dso_letter", "ssa_visit"]`, each step has `sources[0].verified_at == "2026-11-08"`.
  - `test_unknown_task_404`, `test_unknown_step_404`, `test_hidden_step_404` (PATCH `cpt_authorization` for an on_campus profile → 404).
  - `test_progress_updates`: PATCH first `us_phone` step `done: true` → `task_status == "in_progress"`, `progress == 0.5`; second → `"done"`, `1.0`; un-check → `"in_progress"`.
  - `test_completing_dependency_unblocks`: finish both `us_phone` steps → GET checklist `bank_account.blocked_by == []`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement**; PATCH also writes the derived status into the user's `UserTask` (creating it with `source="manual"` if absent).
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: task detail and step progress endpoints`.

---

### Task 7: Chat and DSO draft stubs with one real LLM call

**Files:**
- Create: `app/ai/client.py`, `app/services/chat.py`, `tests/test_chat_api.py`
- Modify: `app/routers/chat.py`, `app/routers/tasks.py`, `app/config.py`

**Interfaces:**
- Produces: `complete(system: str, user: str, model: str = config.FAST_MODEL, max_tokens: int = 512) -> str` using `anthropic.Anthropic(api_key=config.LLM_API_KEY).messages.create(...)`, returning the first text block; raises `LLMUnavailable` when the key is empty or the call fails. Add `FAST_MODEL = os.getenv("FAST_MODEL", "claude-haiku-5-5")` to config.
- Produces: `handle_chat(store, uid, message) -> ChatResponse`; `draft_dso_email(store, uid, task_id, step_id, question) -> DsoDraft`.
- Endpoints: `POST /api/chat` body `ChatRequest` → `ChatResponse`; `POST /api/tasks/{task_id}/steps/{step_id}/dso-draft` body `DsoDraftRequest` → `DsoDraft`.

- [ ] **Step 1: Write failing tests** (monkeypatch `app.ai.client.complete`; no network in tests):
  - `test_chat_uses_llm_reply`: patch to return `"hi"` → `reply == "hi"`, `detected_events == []`, `checklist_diff is None`, `citations == []`; store has 2 messages (user + assistant).
  - `test_chat_falls_back_without_llm`: patch to raise `LLMUnavailable` → 200, `reply` equals the fixed fallback string defined as `CHAT_FALLBACK` in `app/services/chat.py`.
  - `test_chat_empty_message_422`, `test_chat_too_long_422` (2001 chars).
  - `test_dso_draft_template`: for `ssn`/`dso_letter` → `subject` contains the task title, `placeholders == ["YOUR FULL NAME", "YOUR SEVIS ID"]`, body contains `"[YOUR SEVIS ID]"`, `bring_list` equals the step's `materials`.
  - `test_dso_draft_unknown_step_404`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement.** Chat: system prompt one line ("You are a helpful assistant for international students. Keep replies under 80 words."), pass the message through `complete`. DSO draft: fixed English template only (this is the spec's fallback path, §4.6); the user's `question`, if given, becomes `questions[0]`.
- [ ] **Step 4: Run** → PASS. **Step 5: Manual smoke** (only if a key is available): `LLM_API_KEY=... .venv/bin/uvicorn app.main:app` and POST `/api/chat` with header `X-User-Id` → a real reply.
- [ ] **Step 6: Commit** `feat: chat and DSO draft endpoints (stub + LLM smoke call)`.

---

### Task 8: Deploy to Vercel and hand off to frontend

No code tests; done when the deployed URLs below respond. Steps that need an account login are done by the human.

- [ ] **Step 1 (human):** Import `donakq/newcomer-navigator-backend` at vercel.com/new. Set env vars `LLM_API_KEY`, `CORS_ORIGINS` (frontend dev + prod origins).
- [ ] **Step 2:** `curl https://<deployment>/api/health` → `{"ok":true,...}`; open `https://<deployment>/docs` → all endpoints listed.
- [ ] **Step 3:** `curl -X POST https://<deployment>/api/profile -H "X-User-Id: <uuid4>" -H "Content-Type: application/json" -d '{"answers":{"in_us":true,"has_us_phone":false,"has_bank_account":false}}'` → `added` contains `us_phone`.
- [ ] **Step 4:** Add to README: deployed URL, `/docs` link, and the warning that the in-memory store resets whenever Vercel recycles the function (data is not persistent until the Postgres plan).
- [ ] **Step 5: Commit and push** `docs: deployment notes`.

---

## Next Plans (not in this plan)

1. **Postgres store** — `PostgresStore` implementing `Store` on Neon (Data Model §1.3 DDL), same tests run against it.
2. **AI scenarios** — event extraction (§4.3), task personalization + cache (§4.4), grounded Q&A (§4.5), LLM-written DSO drafts (§4.6).
3. **Source ingestion** — `scripts/ingest_sources.py` (§3.10).
4. **Content pipeline** — `scripts/sheet_to_yaml.py` once the team's Google Sheet format is fixed (§3.3).

## Parallel Non-Code Work (team)

- Pick the 1–2 MVP tasks from user interviews and fill in real steps, materials and official source URLs in a shared sheet, using the YAML fields in Data Model §3 as columns.
- Frontend can start immediately from the schemas in Task 4 and the deployed `/docs` after Task 8.
