"""Mock data for the OPT API contract.

Everything here is a placeholder until the database, login and the reviewed UW Policy Pack exist.
Dates are real: the demo plan runs through the timeline engine with PRD persona A
(P = 2027-06-11, offer start S = 2027-07-12). Policy values marked TODO(reviewer) are not verified.
"""

from datetime import date, datetime, timezone

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
    Office,
    OptIntent,
    OptSelection,
    OptType,
    Plan,
    PlanTask,
    PreferredChannel,
    Profile,
    School,
    Source,
    Stage,
    StageDates,
    SupportStatus,
    TaskLabel,
    TaskStatus,
    TemplateContent,
    YesNoNotSure,
)

POLICY_VERSION = "uw-2026.11-draft"

# TODO(reviewer): T_s, T_u and B come from the reviewed UW Policy Pack; these are the PRD 6.4 assumptions.
DEMO_PARAMS = TimelineParams(t_school=14, t_uscis_standard=90, t_uscis_premium=30, buffer=14)

UW = School(id="uw", school_name="University of Washington", support_status=SupportStatus.SUPPORTED)
SCHOOLS = [
    UW,
    School(id="wsu", school_name="Washington State University", support_status=SupportStatus.UNSUPPORTED),
    School(id="seattleu", school_name="Seattle University", support_status=SupportStatus.UNSUPPORTED),
]

# TODO(reviewer): fill from the UW ISS official contact page.
UW_OFFICE = Office(
    office_display_name="UW ISS",
    contact_email=None,
    phone=None,
    office_hours=None,
    contact_page_url=None,
    preferred_channel=PreferredChannel.EMAIL,
    advising_form_url=None,
)

MODULES = [
    Module(id="work_authorization", title="Work authorization", status=ModuleStatus.OPEN, link=None),
    Module(id="maintaining_status", title="Maintaining status", status=ModuleStatus.COMING_SOON, link=None),
    Module(id="health_insurance", title="Health insurance", status=ModuleStatus.COMING_SOON, link=None),
    Module(id="travel", title="Travel", status=ModuleStatus.COMING_SOON, link=None),
    Module(id="taxes", title="Taxes", status=ModuleStatus.COMING_SOON, link=None),
]

# Appendix A sources. URL None = not yet verified by the policy reviewer.
SOURCES = {
    "uw_opt": Source(title="UW ISS: Post-Completion OPT", url=None, last_reviewed=None),
    "uw_opt_faq": Source(title="UW ISS: OPT FAQ", url=None, last_reviewed=None),
    "uscis_i765": Source(title="USCIS: Form I-765", url="https://www.uscis.gov/i-765", last_reviewed=None),
    "cbp_i94": Source(title="CBP: I-94 website", url=None, last_reviewed=None),
    "uscis_case_status": Source(title="USCIS Case Status Online", url="https://egov.uscis.gov/", last_reviewed=None),
    "uscis_processing_times": Source(title="USCIS Processing Times", url=None, last_reviewed=None),
}

# TODO(reviewer): field hints come from the Policy Pack.
FIELD_HINTS = {
    "program_end_date": "Program End Date on your current I-20.",
    "dso_rec_date": "The OPT recommendation section on page 2 of your new OPT I-20.",
    "uscis_receipt_date": "Received Date on your Receipt Notice (Form I-797C).",
    "i20_request_date": "The submission record of your OPT request in MyISSS.",
}

# Task templates (PRD 5.1 and 5.2). Content is a draft until reviewed.
TASKS = {
    "T01": dict(
        title="Confirm which OPT process applies to you",
        prerequisites=[], node_ids=[], node=None,
        steps=["Confirm your Program End Date and that you need post-completion OPT.",
               "Read the full process from UW ISS to USCIS."],
        documents=[Document(name="Current I-20", where_to_get="Issued by UW")],
        sources=["uw_opt"],
    ),
    "T02": dict(
        title="Request your OPT I-20 from UW ISS",
        prerequisites=[], node_ids=["N1", "N1b"], node="N1",
        steps=["Submit the OPT request the way UW ISS requires (see the Policy Pack).",
               "Submit inside the school's request window.",
               "Wait for UW ISS to review it."],
        documents=[Document(name="Per UW ISS requirements", where_to_get="UW Policy Pack")],
        sources=["uw_opt"],
    ),
    "T03": dict(
        title="Confirm you received your OPT I-20",
        prerequisites=["T02"], node_ids=["N2"], node="N1b",
        steps=["Check the OPT recommendation and dates on the new I-20.",
               "Enter your DSO recommendation date here.",
               "If anything is wrong, contact UW ISS."],
        documents=[Document(name="New OPT I-20", where_to_get="Issued by UW")],
        sources=["uw_opt", "uw_opt_faq"],
    ),
    "T04": dict(
        title="Prepare your Form I-765 documents",
        prerequisites=[], node_ids=["N3", "N5"], node="N3",
        steps=["Gather documents following the USCIS instructions.",
               "Choose your OPT start date.",
               "Decide whether to use premium processing."],
        documents=[
            Document(name="New OPT I-20", where_to_get="Issued by UW"),
            Document(name="I-94", where_to_get="CBP I-94 website"),
            Document(name="Passport", where_to_get="Your own"),
            Document(name="Passport-style photos", where_to_get="Photo service"),
            Document(name="Previous I-20s or EAD cards, if any", where_to_get="Your records"),
            Document(name="Filing fee", where_to_get="See current USCIS instructions"),
        ],
        sources=["uscis_i765", "cbp_i94"],
    ),
    "T05": dict(
        title="File Form I-765 with USCIS",
        prerequisites=["T03"], node_ids=["N4"], node="N4",
        steps=["File online or by mail.",
               "Make sure USCIS receives it before your last filing date.",
               "Keep your Receipt Notice."],
        documents=[Document(name="All documents from T04", where_to_get="T04")],
        sources=["uscis_i765"],
    ),
    "T06": dict(
        title="Track your USCIS case",
        prerequisites=["T05"], node_ids=["N6", "N7"], node="N6",
        steps=["Check your case status with your receipt number.",
               "Watch for a Request for Evidence (RFE).",
               "When the EAD arrives, check the information on the card."],
        documents=[Document(name="Receipt Notice (I-797C)", where_to_get="Mailed by USCIS")],
        sources=["uscis_case_status", "uscis_processing_times"],
    ),
}

DONE_FOR_PREREQ = {TaskStatus.WAITING_EXTERNAL, TaskStatus.COMPLETED}


def demo_profile() -> Profile:
    return Profile(
        email="demo@uw.edu",
        school=UW,
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
        policy_version=POLICY_VERSION,
        policy_last_reviewed=None,
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
    offer, dates = profile.offer, profile.stage_dates
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
        DEMO_PARAMS,
    )


def _label(due_at: date | None, due_type: DueType, status: TaskStatus, today: date) -> TaskLabel | None:
    if due_at is None or due_type != DueType.FEDERAL or status == TaskStatus.COMPLETED:
        return None
    if due_at < today:
        return TaskLabel.OVERDUE
    return TaskLabel.URGENT if (due_at - today).days <= 7 else None


def build_tasks(timeline: TimelineResult, statuses: dict[str, TaskStatus], today: date) -> list[PlanTask]:
    nodes = {n.id: n for n in timeline.nodes}
    tasks = []
    for task_id, tpl in TASKS.items():
        status = statuses.get(task_id, TaskStatus.NOT_STARTED)
        blocked_by = [p for p in tpl["prerequisites"] if statuses.get(p) not in DONE_FOR_PREREQ]
        if blocked_by and status == TaskStatus.NOT_STARTED:
            status = TaskStatus.BLOCKED
        node = nodes.get(tpl["node"]) if tpl["node"] else None
        due_at = node.date if node else None
        due_type = node.due_type if node else DueType.UNKNOWN
        tasks.append(PlanTask(
            id=task_id,
            title=tpl["title"],
            status=status,
            due_at=due_at,
            due_type=due_type,
            date_state=node.date_state if node else DateState.UNKNOWN,
            label=_label(due_at, due_type, status, today),
            blocked_by=blocked_by,
            node_ids=tpl["node_ids"],
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
        policy_version=POLICY_VERSION,
        generated_at=datetime.now(timezone.utc),
        branch=timeline.branch,
        window=timeline.window,
        too_early=timeline.too_early,
        nodes=timeline.nodes,
        risk_labels=timeline.risks,
        warnings=["Policy values are unreviewed placeholders (mock data)."],
        tasks=build_tasks(timeline, statuses or {}, today),
    )
