"""Mock demo student for the OPT API contract.

Content (schools, UW Policy Pack, federal parameters, sources, task templates) is read from the
catalog YAML via app.opt.content, so the mock shows exactly what the team has filled in so far.
Only the user is fake: one demo student, PRD persona A (UW, Master, P = 2027-06-11, S = 2027-07-12).
Nothing is saved; this module goes away once the database and login exist.
"""

from datetime import date, datetime, timezone

from app.opt.content import OptContent, get_content
from app.opt.timeline import (
    DateState,
    DueType,
    TimelineInput,
    TimelineParams,
    TimelineResult,
    WindowStatus,
    compute_timeline,
    window_status,
)
from app.schemas.opt import (
    BannerKind,
    DegreeLevel,
    Document,
    GraduationBanner,
    Module,
    ModuleStatus,
    Offer,
    OptIntent,
    OptSelection,
    OptType,
    Plan,
    PlanTask,
    Profile,
    School,
    Source,
    Stage,
    StageDates,
    TaskLabel,
    TaskStatus,
    YesNoNotSure,
)

MODULE_TITLES = {
    "work_authorization": "Work authorization",
    "maintaining_status": "Maintaining status",
    "health_insurance": "Health insurance",
    "travel": "Travel",
    "taxes": "Taxes",
}
DONE_FOR_PREREQ = {TaskStatus.WAITING_EXTERNAL, TaskStatus.COMPLETED}


def policy_version(content: OptContent | None = None) -> str:
    policy = (content or get_content()).policy
    return f"{policy.id}-v{policy.version}"


def schools() -> list[School]:
    return [School(**s.model_dump()) for s in get_content().schools]


def school(school_id: str) -> School | None:
    return next((s for s in schools() if s.id == school_id), None)


def modules() -> list[Module]:
    links = get_content().policy.module_links
    return [
        Module(
            id=module_id,
            title=title,
            status=ModuleStatus.OPEN if module_id == "work_authorization" else ModuleStatus.COMING_SOON,
            link=links.get(module_id),
        )
        for module_id, title in MODULE_TITLES.items()
    ]


def source(source_id: str) -> Source:
    s = get_content().sources[source_id]
    return Source(id=s.id, title=s.title, url=s.url, publisher=s.publisher, last_reviewed=s.last_reviewed)


def documents(task_id: str) -> list[Document]:
    return [Document(**d.model_dump()) for d in get_content().tasks[task_id].documents]


def demo_profile() -> Profile:
    content = get_content()
    return Profile(
        email="demo@uw.edu",
        school=school("uw"),
        degree_level=DegreeLevel.MASTER,
        program_end_date=date(2027, 6, 11),
        timezone="America/Los_Angeles",
        opt_selection=OptSelection(
            opt_intent=OptIntent.AFTER_GRADUATION, first_time_at_level=True, opt_type=OptType.POST_COMPLETION
        ),
        stage=Stage.PLANNING,
        stage_dates=StageDates(),
        offer=Offer(
            has_offer=True,
            offer_start_date=date(2027, 7, 12),
            start_flexible=YesNoNotSure.NOT_SURE,
            premium_intent=YesNoNotSure.NO,
        ),
        policy_version=policy_version(content),
        policy_last_reviewed=content.policy.reviewed_at,
    )


def demo_params(profile: Profile) -> TimelineParams:
    content = get_content()
    return TimelineParams(
        t_school=content.policy.timeline.t_school_days,
        t_uscis_standard=content.federal.processing.t_uscis_standard_days,
        t_uscis_premium=content.federal.processing.t_uscis_premium_days,
        buffer=content.federal.buffer_days,
        school_window_open=content.policy.school_window_open(profile.program_end_date),
    )


def graduation_banner(program_end: date, today: date) -> GraduationBanner:
    window = window_status(program_end, today)
    kind = BannerKind(window.value)
    if window == WindowStatus.NOT_OPEN and (program_end - today).days > 365:
        kind = BannerKind.TOO_EARLY
    days_left = (program_end - today).days + 60 if window == WindowStatus.AFTER_PROGRAM_END else None
    return GraduationBanner(
        kind=kind,
        window_opens_on=date.fromordinal(program_end.toordinal() - 90),
        window_closes_on=date.fromordinal(program_end.toordinal() + 60),
        days_left=days_left,
    )


def _timeline(profile: Profile, today: date) -> TimelineResult:
    # No offer answer yet: plan forward from the filing window (PRD 6.3) until the student answers.
    offer = profile.offer or Offer(has_offer=False)
    dates = profile.stage_dates
    return compute_timeline(
        TimelineInput(
            program_end=profile.program_end_date,
            today=today,
            has_offer=offer.has_offer,
            offer_start=offer.offer_start_date,
            dso_rec=dates.dso_rec_date,
            i20_request=dates.i20_request_date,
            uscis_receipt=dates.uscis_receipt_date,
            requested_start=dates.requested_start_date,
            start_preference=offer.start_preference or "NOT_SURE",
            preferred_start=offer.preferred_start_date,
            premium=offer.premium_intent == YesNoNotSure.YES,
        ),
        demo_params(profile),
    )


def _label(deadline: date | None, status: TaskStatus, today: date) -> TaskLabel | None:
    """PRD F03: URGENT = <= 7 days to the hard deadline; OVERDUE = past it and not done."""
    if deadline is None or status == TaskStatus.COMPLETED:
        return None
    if deadline < today:
        return TaskLabel.OVERDUE
    return TaskLabel.URGENT if (deadline - today).days <= 7 else None


def build_tasks(timeline: TimelineResult, statuses: dict[str, TaskStatus], today: date) -> list[PlanTask]:
    nodes = {n.id: n for n in timeline.nodes}
    tasks = []
    for tpl in get_content().tasks.values():
        status = statuses.get(tpl.id, TaskStatus.NOT_STARTED)
        blocked_by = [p for p in tpl.prerequisites if statuses.get(p) not in DONE_FOR_PREREQ]
        if blocked_by and status == TaskStatus.NOT_STARTED:
            status = TaskStatus.BLOCKED
        node = nodes.get(tpl.timeline_node) if tpl.timeline_node else None
        deadline_node = nodes.get(tpl.deadline_node) if tpl.deadline_node else None
        if deadline_node is None and node is not None and node.due_type == DueType.FEDERAL:
            deadline_node = node
        deadline_at = deadline_node.date if deadline_node else None
        tasks.append(PlanTask(
            id=tpl.id,
            title=tpl.title,
            status=status,
            due_at=node.date if node else None,
            due_type=node.due_type if node else tpl.due_type,
            date_state=node.date_state if node else DateState.UNKNOWN,
            deadline_at=deadline_at,
            label=_label(deadline_at, status, today),
            blocked_by=blocked_by,
            node_ids=[n for n in (tpl.timeline_node, tpl.deadline_node) if n],
        ))
    return tasks


def build_plan(profile: Profile, statuses: dict[str, TaskStatus] | None = None, version: int = 1) -> Plan:
    today = date.today()  # TODO: use the user's timezone once login stores it
    timeline = _timeline(profile, today)
    return Plan(
        plan_id="plan-demo",
        version=version,
        status="ACTIVE",
        opt_type=OptType.POST_COMPLETION,
        policy_version=policy_version(),
        generated_at=datetime.now(timezone.utc),
        branch=timeline.branch,
        window=timeline.window,
        too_early=timeline.too_early,
        nodes=timeline.nodes,
        risk_labels=timeline.risks,
        warnings=["Mock data: one demo student, nothing is saved.", *get_content().warnings],
        tasks=build_tasks(timeline, statuses or {}, today),
    )
