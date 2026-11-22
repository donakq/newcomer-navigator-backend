"""OPT MVP v1 API contract (PRD v1.3 sections 8.2 and 8.3). Dates are YYYY-MM-DD."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.opt.timeline import DateState, DueType, Node, Risk, StartPreference, WindowStatus

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


# --- Enums (PRD 8.2) ---


class SupportStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class PolicyStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REVIEWED_ACTIVE = "REVIEWED_ACTIVE"
    RETIRED = "RETIRED"


class ModuleStatus(str, Enum):
    OPEN = "OPEN"
    COMING_SOON = "COMING_SOON"


class DegreeLevel(str, Enum):
    BACHELOR = "BACHELOR"
    MASTER = "MASTER"
    PHD = "PHD"


class OptIntent(str, Enum):
    AFTER_GRADUATION = "AFTER_GRADUATION"
    WHILE_STUDYING = "WHILE_STUDYING"
    STEM_EXTENSION = "STEM_EXTENSION"
    NOT_SURE = "NOT_SURE"


class OptType(str, Enum):
    POST_COMPLETION = "POST_COMPLETION"
    PRE_COMPLETION = "PRE_COMPLETION"
    STEM = "STEM"


class Stage(str, Enum):
    PLANNING = "PLANNING"
    I20_REQUESTED = "I20_REQUESTED"
    I20_RECEIVED = "I20_RECEIVED"
    I765_FILED = "I765_FILED"
    APPROVED = "APPROVED"


class TaskStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class TaskLabel(str, Enum):
    URGENT = "URGENT"  # <= 7 days to the hard deadline
    OVERDUE = "OVERDUE"  # past the hard deadline, not done


class PreferredChannel(str, Enum):
    EMAIL = "EMAIL"
    FORM = "FORM"
    PORTAL = "PORTAL"


class YesNoNotSure(str, Enum):
    YES = "YES"
    NO = "NO"
    NOT_SURE = "NOT_SURE"


class Scope(str, Enum):
    IN = "IN"
    OUT = "OUT"
    UNSUPPORTED_OPT = "UNSUPPORTED_OPT"


class Intent(str, Enum):
    NEXT_STEP = "NEXT_STEP"
    OPT_BASICS = "OPT_BASICS"
    SCHOOL_PROCESS = "SCHOOL_PROCESS"
    DOCUMENTS = "DOCUMENTS"
    DEADLINE = "DEADLINE"
    START_DATE = "START_DATE"
    FORM_HELP = "FORM_HELP"
    TRACKING = "TRACKING"
    OPT_RULES = "OPT_RULES"
    RISK_ESCALATION = "RISK_ESCALATION"
    PRODUCT_HELP = "PRODUCT_HELP"
    CONTACT_DSO = "CONTACT_DSO"


class DraftQuestionType(str, Enum):
    CONFIRM_DATES = "CONFIRM_DATES"
    I20_STATUS = "I20_STATUS"
    DOCUMENTS = "DOCUMENTS"
    RFE_OR_DENIAL = "RFE_OR_DENIAL"
    OTHER = "OTHER"


class DraftTone(str, Enum):
    DEFAULT = "DEFAULT"
    SHORTER = "SHORTER"
    MORE_FORMAL = "MORE_FORMAL"


class BannerKind(str, Enum):
    TOO_EARLY = "TOO_EARLY"  # P is more than 12 months away
    NOT_OPEN = "NOT_OPEN"
    OPEN = "OPEN"
    AFTER_PROGRAM_END = "AFTER_PROGRAM_END"
    CLOSED = "CLOSED"


# --- Health ---


class HealthResponse(BaseModel):
    ok: bool
    version: str
    tasks: int  # number of OPT task templates loaded from catalog/


# --- Auth ---


class EmailStartRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)


class EmailStartResponse(BaseModel):
    resend_after_seconds: int
    code_expires_in_seconds: int


class EmailVerifyRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN)
    code: str = Field(pattern=r"^\d{6}$")
    tos_accepted: bool
    timezone: str = "America/Los_Angeles"


class EmailVerifyResponse(BaseModel):
    token: str  # send as "Authorization: Bearer <token>"
    expires_at: datetime
    is_new_user: bool


# --- Schools ---


class School(BaseModel):
    id: str
    school_name: str
    support_status: SupportStatus


class SchoolSearchResponse(BaseModel):
    schools: list[School]


class Office(BaseModel):
    office_display_name: str
    contact_email: str | None
    phone: str | None
    office_hours: str | None
    contact_page_url: str | None
    preferred_channel: PreferredChannel
    advising_form_url: str | None
    notes: str | None = None  # how to reach the office, response time


# --- Profile ---


class OnboardingRequest(BaseModel):
    school_id: str
    program_end_date: date
    degree_level: DegreeLevel


class OptSelection(BaseModel):
    opt_intent: OptIntent
    first_time_at_level: bool
    opt_type: OptType | None


class StageDates(BaseModel):
    i20_request_date: date | None = None
    dso_rec_date: date | None = None  # R
    i20_issue_date: date | None = None
    uscis_receipt_date: date | None = None
    requested_start_date: date | None = None


class Offer(BaseModel):
    has_offer: bool
    offer_start_date: date | None = None  # S
    start_flexible: YesNoNotSure | None = None
    start_preference: StartPreference | None = None
    preferred_start_date: date | None = None
    premium_intent: YesNoNotSure = YesNoNotSure.NOT_SURE


class ProcessingChoice(BaseModel):
    """Processing times the student picked; None = use the catalog default (the conservative maximum)."""

    school_business_days: int | None = None  # T_s
    uscis_standard_days: int | None = None  # T_u
    uscis_premium_business_days: int | None = None  # T_u with premium processing


class Profile(BaseModel):
    email: str
    school: School
    degree_level: DegreeLevel
    program_end_date: date  # P
    timezone: str
    opt_selection: OptSelection | None
    stage: Stage | None
    stage_dates: StageDates
    offer: Offer | None
    processing: ProcessingChoice = ProcessingChoice()
    policy_version: str
    policy_last_reviewed: date | None


class ProfileResponse(BaseModel):
    profile: Profile


class ProfilePatch(BaseModel):
    """Home edits. Changing P, stage dates or offer regenerates the plan."""

    degree_level: DegreeLevel | None = None
    program_end_date: date | None = None


class ProfilePatchResponse(BaseModel):
    profile: Profile
    plan_version: int


# --- Checklist overview ---


class GraduationBanner(BaseModel):
    kind: BannerKind
    window_opens_on: date  # P - 90
    window_closes_on: date  # P + 60
    days_left: int | None  # set for AFTER_PROGRAM_END


class Module(BaseModel):
    id: str
    title: str
    status: ModuleStatus
    link: str | None  # official page for COMING_SOON modules


class OptSummary(BaseModel):
    started: bool  # Select OPT done
    progress: float  # 0.0 - 1.0
    next_task_id: str | None


class ChecklistResponse(BaseModel):
    situation: Profile
    graduation_banner: GraduationBanner
    modules: list[Module]
    opt_summary: OptSummary


# --- Select OPT, Status, Offer ---


class OptSelectionRequest(BaseModel):
    opt_intent: OptIntent
    first_time_at_level: bool


class OptSelectionResponse(BaseModel):
    opt_type: OptType


class StatusRequest(StageDates):
    stage: Stage


class StatusResponse(BaseModel):
    stage: Stage
    stage_dates: StageDates


# --- Plan (Checklist + Timeline share it) ---


class PlanTask(BaseModel):
    id: str  # T01 .. T06
    title: str
    status: TaskStatus
    due_at: date | None  # date shown on the Checklist
    due_type: DueType
    date_state: DateState
    deadline_at: date | None  # hard deadline, when different from due_at (T05: N4)
    label: TaskLabel | None  # URGENT / OVERDUE, computed from the hard deadline
    blocked_by: list[str]
    node_ids: list[str]  # Timeline nodes this task owns


class ProcessingTime(BaseModel):
    """One processing time the student can adjust on the Timeline, and the value the plan used."""

    id: str  # matches the ProcessingChoice field: school_business_days | uscis_standard_days | ...
    label: str
    min: int
    max: int
    default: int
    unit: str  # calendar_days | business_days
    chosen: int | None  # None until the student picks
    used: int  # chosen, else default
    note: str | None
    source_ids: list[str]


class Plan(BaseModel):
    plan_id: str
    version: int
    status: str  # ACTIVE | ARCHIVED
    opt_type: OptType
    policy_version: str
    generated_at: datetime
    branch: str  # OFFER | NO_OFFER
    window: WindowStatus
    too_early: bool
    nodes: list[Node]
    risk_labels: list[Risk]
    processing: list[ProcessingTime]
    warnings: list[str]
    tasks: list[PlanTask]


# --- Task details ---


class Source(BaseModel):
    id: str
    title: str
    url: str | None  # None until the policy reviewer fills it in
    publisher: str  # UW_ISS | USCIS | DHS | CBP
    last_reviewed: date | None


class Document(BaseModel):
    name: str
    where_to_get: str | None


class TemplateContent(BaseModel):
    steps: list[str]
    documents: list[Document]


class TaskDetailResponse(BaseModel):
    task: PlanTask
    template_content: TemplateContent
    sources: list[Source]
    field_hints: dict[str, str]  # where to find each date on official documents


class TaskPatchRequest(StageDates):
    status: TaskStatus | None = None


class TaskPatchResponse(BaseModel):
    task: PlanTask
    plan_version: int


# --- Assistant ---


class AssistantRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    current_page: str  # home | checklist | select_opt | status | timeline | task
    current_task_id: str | None = None
    conversation_id: str | None = None


class FollowUp(BaseModel):
    kind: str  # CLARIFY | ASK_SLOT
    question: str | None
    chips: list[str]


class AssistantAction(BaseModel):
    kind: str  # OPEN_TASK | DRAFT_EMAIL | OPEN_CONTACT_PANEL
    label: str
    target: str | None


class AssistantResponse(BaseModel):
    conversation_id: str
    intent: Intent | None
    scope: Scope
    confidence: float
    language: str  # zh | en, follows the user's message
    answer: str
    sources: list[Source]
    follow_up: FollowUp | None
    actions: list[AssistantAction]


class DsoDraftRequest(BaseModel):
    question_type: DraftQuestionType
    user_question: str = Field(min_length=1, max_length=2000)
    current_task_id: str | None = None
    conversation_id: str | None = None
    tone: DraftTone = DraftTone.DEFAULT


class DsoDraftResponse(BaseModel):
    recipient: str | None  # email address or official form URL; the app never sends
    subject: str
    body: str
    placeholders: list[str]
