"""Logged-in user's OPT data (PRD 8.3).

Each request loads the user's state from the store, changes it, and saves it with _commit().
A request that fails before _commit() saves nothing.
"""

from datetime import date

from fastapi import APIRouter, Depends, Response

from app.deps import current_session
from app.errors import ApiError
from app.mock import opt_assistant, opt_demo
from app.mock.opt_demo import build_plan, documents, graduation_banner, modules, policy_version, school, source
from app.opt.content import TaskTemplate, get_content
from app.opt.timeline import StartPreference
from app.store import UserState, get_store
from app.schemas.opt import (
    ChecklistResponse,
    DsoDraftRequest,
    DsoDraftResponse,
    Offer,
    OnboardingRequest,
    OptIntent,
    OptSelection,
    OptSelectionRequest,
    OptSelectionResponse,
    OptSummary,
    OptType,
    Plan,
    ProcessingChoice,
    Profile,
    ProfilePatch,
    ProfilePatchResponse,
    ProfileResponse,
    Stage,
    StageDates,
    StatusRequest,
    StatusResponse,
    SupportStatus,
    TaskDetailResponse,
    TaskPatchRequest,
    TaskPatchResponse,
    TaskStatus,
    TemplateContent,
)

router = APIRouter(prefix="/api/me", tags=["me"])

# PRD F05: dates that must come with a stage.
STAGE_REQUIRED = {Stage.I20_RECEIVED: ["dso_rec_date"], Stage.I765_FILED: ["uscis_receipt_date", "requested_start_date"]}
# What each stage means for the tasks (PRD 5.1): the student has already done these.
STAGE_DONE = {
    Stage.PLANNING: {},
    Stage.I20_REQUESTED: {"T02": TaskStatus.WAITING_EXTERNAL},
    Stage.I20_RECEIVED: {"T02": TaskStatus.COMPLETED, "T03": TaskStatus.COMPLETED},
    Stage.I765_FILED: {t: TaskStatus.COMPLETED for t in ("T02", "T03", "T04", "T05")},
    Stage.APPROVED: {t: TaskStatus.COMPLETED for t in ("T02", "T03", "T04", "T05", "T06")},
}
# Recording one of these dates on a task moves the student to that stage (PRD F07).
DATE_STAGE = {"i20_request_date": Stage.I20_REQUESTED, "dso_rec_date": Stage.I20_RECEIVED,
              "uscis_receipt_date": Stage.I765_FILED}
STAGE_ORDER = list(Stage)


def current_state(token: str = Depends(current_session)) -> UserState:
    state = get_store().state_for(token)
    if state is None:
        raise ApiError(401, "unauthenticated", "Your session has expired. Log in again.")
    return state


def _profile(state: UserState) -> Profile:
    if state.profile is None:
        raise ApiError(404, "onboarding_required", "Finish onboarding first")
    return state.profile


def _require(body, fields: list[str]) -> None:
    missing = [f for f in fields if getattr(body, f) is None]
    if missing:
        raise ApiError(422, "missing_fields", f"Missing required fields: {', '.join(missing)}")


def _task_or_404(task_id: str) -> TaskTemplate:
    tpl = get_content().tasks.get(task_id)
    if tpl is None:
        raise ApiError(404, "not_found", f"Unknown task {task_id!r}")
    return tpl


def _plan(state: UserState) -> Plan:
    try:
        return build_plan(_profile(state), state.task_statuses, version=state.plan_version)
    except ValueError as e:  # timeline engine rejected the inputs
        raise ApiError(422, "invalid_timeline_input", str(e)) from e


def _apply_stage(state: UserState, stage: Stage) -> None:
    """Mark the tasks a stage implies; never downgrade a task that is already COMPLETED."""
    for task_id, status in STAGE_DONE[stage].items():
        if state.task_statuses.get(task_id) != TaskStatus.COMPLETED:
            state.task_statuses[task_id] = status


def _commit(state: UserState, plan_changed: bool = True) -> None:
    """Save the user's state; bump the plan version when anything the plan depends on changed."""
    if plan_changed:
        state.plan_version += 1
    get_store().save(state)


@router.put("/onboarding", response_model=ProfileResponse)
def onboarding(body: OnboardingRequest, state: UserState = Depends(current_state)) -> ProfileResponse:
    chosen = school(body.school_id)
    if chosen is None or chosen.support_status != SupportStatus.SUPPORTED:
        raise ApiError(409, "unsupported_school", "This school is not supported yet")
    content = get_content()
    state.profile = Profile(
        email=state.email, school=chosen, degree_level=body.degree_level, program_end_date=body.program_end_date,
        timezone=state.timezone, opt_selection=None, stage=None, stage_dates=StageDates(), offer=None,
        policy_version=policy_version(content), policy_last_reviewed=content.policy.reviewed_at,
    )
    state.task_statuses = {}
    _commit(state)
    return ProfileResponse(profile=state.profile)


@router.get("/profile", response_model=ProfileResponse)
def get_profile(state: UserState = Depends(current_state)) -> ProfileResponse:
    return ProfileResponse(profile=_profile(state))


@router.patch("/profile", response_model=ProfilePatchResponse)
def patch_profile(body: ProfilePatch, state: UserState = Depends(current_state)) -> ProfilePatchResponse:
    changes = body.model_dump(exclude_none=True)
    state.profile = _profile(state).model_copy(update=changes)
    _commit(state, plan_changed="program_end_date" in changes)
    return ProfilePatchResponse(profile=state.profile, plan_version=state.plan_version)


@router.delete("", status_code=204, response_class=Response)
def delete_account(token: str = Depends(current_session)) -> Response:
    get_store().delete_user(token)
    return Response(status_code=204)


@router.get("/checklist", response_model=ChecklistResponse)
def checklist(state: UserState = Depends(current_state)) -> ChecklistResponse:
    profile = _profile(state)
    plan = _plan(state)
    done = [t for t in plan.tasks if t.status == TaskStatus.COMPLETED]
    upcoming = next((t for t in plan.tasks if t.status not in (TaskStatus.COMPLETED, TaskStatus.BLOCKED)), None)
    return ChecklistResponse(
        situation=profile,
        graduation_banner=graduation_banner(profile.program_end_date, date.today()),
        modules=modules(),
        opt_summary=OptSummary(
            started=profile.opt_selection is not None,
            progress=len(done) / len(plan.tasks),
            next_task_id=upcoming.id if upcoming else None,
        ),
    )


@router.put("/opt-selection", response_model=OptSelectionResponse)
def opt_selection(body: OptSelectionRequest, state: UserState = Depends(current_state)) -> OptSelectionResponse:
    profile = _profile(state)
    if body.opt_intent != OptIntent.AFTER_GRADUATION or not body.first_time_at_level:
        raise ApiError(422, "out_of_scope", "v1 only supports a first-time post-completion OPT application")
    selection = OptSelection(opt_intent=body.opt_intent, first_time_at_level=True, opt_type=OptType.POST_COMPLETION)
    state.profile = profile.model_copy(update={"opt_selection": selection, "stage": profile.stage or Stage.PLANNING})
    state.task_statuses["T01"] = TaskStatus.COMPLETED  # Select OPT is how T01 gets done
    _commit(state)
    return OptSelectionResponse(opt_type=OptType.POST_COMPLETION)


@router.put("/status", response_model=StatusResponse)
def status(body: StatusRequest, state: UserState = Depends(current_state)) -> StatusResponse:
    profile = _profile(state)
    _require(body, STAGE_REQUIRED.get(body.stage, []))
    dates = StageDates(**body.model_dump(exclude={"stage"}))
    state.profile = profile.model_copy(update={"stage": body.stage, "stage_dates": dates})
    _apply_stage(state, body.stage)
    _commit(state)
    return StatusResponse(stage=body.stage, stage_dates=dates)


@router.put("/offer", response_model=Offer)
def offer(body: Offer, state: UserState = Depends(current_state)) -> Offer:
    profile = _profile(state)
    if body.has_offer:
        _require(body, ["offer_start_date"])
    else:
        _require(body, ["start_preference"])
        if body.start_preference == StartPreference.SPECIFIC_DATE:
            _require(body, ["preferred_start_date"])
    state.profile = profile.model_copy(update={"offer": body})
    _plan(state)  # reject inputs the timeline engine can't use, before keeping them
    _commit(state)
    return body


@router.put("/processing-times", response_model=ProcessingChoice)
def processing_times(body: ProcessingChoice, state: UserState = Depends(current_state)) -> ProcessingChoice:
    """The student's own processing-time estimates, each within the official range shown on the Timeline."""
    profile = _profile(state)
    ranges = {p.id: p for p in opt_demo.processing_times(profile)}
    for field, value in body.model_dump(exclude_none=True).items():
        r = ranges[field]
        if not r.min <= value <= r.max:
            raise ApiError(422, "out_of_range", f"{field} must be between {r.min} and {r.max}")
    state.profile = profile.model_copy(update={"processing": body})
    _commit(state)
    return body


@router.post("/opt-plan/generate", response_model=Plan)
def generate_plan(state: UserState = Depends(current_state)) -> Plan:
    _commit(state)
    return _plan(state)


@router.get("/opt-plan", response_model=Plan)
def get_plan(state: UserState = Depends(current_state)) -> Plan:
    return _plan(state)


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def task_detail(task_id: str, state: UserState = Depends(current_state)) -> TaskDetailResponse:
    tpl = _task_or_404(task_id)
    task = next(t for t in _plan(state).tasks if t.id == task_id)
    return TaskDetailResponse(
        task=task,
        template_content=TemplateContent(steps=tpl.steps, documents=documents(task_id)),
        sources=[source(s) for s in tpl.source_ids],
        field_hints=get_content().policy.field_hints,
    )


@router.patch("/tasks/{task_id}", response_model=TaskPatchResponse)
def patch_task(task_id: str, body: TaskPatchRequest, state: UserState = Depends(current_state)) -> TaskPatchResponse:
    tpl = _task_or_404(task_id)
    profile = _profile(state)
    current = next(t for t in _plan(state).tasks if t.id == task_id)
    if current.status == TaskStatus.BLOCKED and body.status:
        raise ApiError(409, "task_blocked", f"Finish {', '.join(current.blocked_by)} first")
    dates = profile.stage_dates.model_copy(update=body.model_dump(exclude={"status"}, exclude_none=True))
    if body.status == TaskStatus.COMPLETED:
        _require(dates, tpl.complete_requires)  # already-saved dates count
    stage = profile.stage or Stage.PLANNING
    for field, field_stage in DATE_STAGE.items():
        if getattr(body, field) and STAGE_ORDER.index(field_stage) > STAGE_ORDER.index(stage):
            stage = field_stage
    if stage != (profile.stage or Stage.PLANNING):
        _apply_stage(state, stage)  # same effect as choosing that stage on Status
    state.profile = profile.model_copy(update={"stage_dates": dates, "stage": stage})
    if body.status:
        state.task_statuses[task_id] = body.status
    _commit(state)
    plan = _plan(state)
    return TaskPatchResponse(task=next(t for t in plan.tasks if t.id == task_id), plan_version=plan.version)


@router.post("/dso-drafts", response_model=DsoDraftResponse)
def dso_draft(body: DsoDraftRequest, state: UserState = Depends(current_state)) -> DsoDraftResponse:
    return opt_assistant.draft(body, _profile(state))
