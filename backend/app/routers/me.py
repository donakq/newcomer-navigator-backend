"""Logged-in user's OPT data (PRD 8.3). Mock: nothing is saved; writes are validated and echoed back."""

from datetime import date

from fastapi import APIRouter, Depends, Response

from app.deps import current_session
from app.errors import ApiError
from app.mock import opt_assistant
from app.mock.opt_demo import build_plan, demo_profile, documents, graduation_banner, modules, school, source
from app.opt.content import TaskTemplate, get_content
from app.opt.timeline import StartPreference
from app.schemas.opt import (
    ChecklistResponse,
    DsoDraftRequest,
    DsoDraftResponse,
    Offer,
    OnboardingRequest,
    OptIntent,
    OptSelectionRequest,
    OptSelectionResponse,
    OptSummary,
    OptType,
    Plan,
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

router = APIRouter(prefix="/api/me", tags=["me"], dependencies=[Depends(current_session)])

# PRD F05 / F07: dates that must come with a stage or a completed task.
STAGE_REQUIRED = {Stage.I20_RECEIVED: ["dso_rec_date"], Stage.I765_FILED: ["uscis_receipt_date", "requested_start_date"]}


def _require(body, fields: list[str]) -> None:
    missing = [f for f in fields if getattr(body, f) is None]
    if missing:
        raise ApiError(422, "missing_fields", f"Missing required fields: {', '.join(missing)}")


def _task_or_404(task_id: str) -> TaskTemplate:
    tpl = get_content().tasks.get(task_id)
    if tpl is None:
        raise ApiError(404, "not_found", f"Unknown task {task_id!r}")
    return tpl


@router.put("/onboarding", response_model=ProfileResponse)
def onboarding(body: OnboardingRequest) -> ProfileResponse:
    chosen = school(body.school_id)
    if chosen is None or chosen.support_status != SupportStatus.SUPPORTED:
        raise ApiError(409, "unsupported_school", "This school is not supported yet")
    profile = demo_profile().model_copy(update={
        "school": chosen, "program_end_date": body.program_end_date, "degree_level": body.degree_level,
        "opt_selection": None, "stage": None, "stage_dates": StageDates(), "offer": None,
    })
    return ProfileResponse(profile=profile)


@router.get("/profile", response_model=ProfileResponse)
def get_profile() -> ProfileResponse:
    return ProfileResponse(profile=demo_profile())


@router.patch("/profile", response_model=ProfilePatchResponse)
def patch_profile(body: ProfilePatch) -> ProfilePatchResponse:
    changes = body.model_dump(exclude_none=True)
    profile = demo_profile().model_copy(update=changes)
    return ProfilePatchResponse(profile=profile, plan_version=2 if "program_end_date" in changes else 1)


@router.delete("", status_code=204, response_class=Response)
def delete_account() -> Response:
    return Response(status_code=204)


@router.get("/checklist", response_model=ChecklistResponse)
def checklist() -> ChecklistResponse:
    profile = demo_profile()
    plan = build_plan(profile)
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
def opt_selection(body: OptSelectionRequest) -> OptSelectionResponse:
    if body.opt_intent != OptIntent.AFTER_GRADUATION or not body.first_time_at_level:
        raise ApiError(422, "out_of_scope", "v1 only supports a first-time post-completion OPT application")
    return OptSelectionResponse(opt_type=OptType.POST_COMPLETION)


@router.put("/status", response_model=StatusResponse)
def status(body: StatusRequest) -> StatusResponse:
    _require(body, STAGE_REQUIRED.get(body.stage, []))
    return StatusResponse(stage=body.stage, stage_dates=StageDates(**body.model_dump(exclude={"stage"})))


@router.put("/offer", response_model=Offer)
def offer(body: Offer) -> Offer:
    if body.has_offer:
        _require(body, ["offer_start_date"])
    else:
        _require(body, ["start_preference"])
        if body.start_preference == StartPreference.SPECIFIC_DATE:
            _require(body, ["preferred_start_date"])
    return body


@router.post("/opt-plan/generate", response_model=Plan)
def generate_plan() -> Plan:
    return build_plan(demo_profile())


@router.get("/opt-plan", response_model=Plan)
def get_plan() -> Plan:
    return build_plan(demo_profile())


@router.get("/tasks/{task_id}", response_model=TaskDetailResponse)
def task_detail(task_id: str) -> TaskDetailResponse:
    tpl = _task_or_404(task_id)
    task = next(t for t in build_plan(demo_profile()).tasks if t.id == task_id)
    return TaskDetailResponse(
        task=task,
        template_content=TemplateContent(steps=tpl.steps, documents=documents(task_id)),
        sources=[source(s) for s in tpl.source_ids],
        field_hints=get_content().policy.field_hints,
    )


@router.patch("/tasks/{task_id}", response_model=TaskPatchResponse)
def patch_task(task_id: str, body: TaskPatchRequest) -> TaskPatchResponse:
    tpl = _task_or_404(task_id)
    if body.status == TaskStatus.COMPLETED:
        _require(body, tpl.complete_requires)
    profile = demo_profile()
    dates = profile.stage_dates.model_copy(update=body.model_dump(exclude={"status"}, exclude_none=True))
    statuses = {task_id: body.status} if body.status else {}
    plan = build_plan(profile.model_copy(update={"stage_dates": dates}), statuses, version=2)
    return TaskPatchResponse(task=next(t for t in plan.tasks if t.id == task_id), plan_version=plan.version)


@router.post("/dso-drafts", response_model=DsoDraftResponse)
def dso_draft(body: DsoDraftRequest) -> DsoDraftResponse:
    return opt_assistant.draft(body)
