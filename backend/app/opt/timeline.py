"""OPT timeline date engine (PRD v1.3 section 6). Pure functions: no I/O, no LLM.

Symbols follow the PRD: P = program end date, R = DSO recommendation date,
S = offer start date, T_s / T_u = school / USCIS processing days, B = buffer.
All dates are calendar days; "today" is the user's local date, passed in.
"""

from datetime import date, timedelta
from enum import Enum

from pydantic import BaseModel


class DueType(str, Enum):
    FEDERAL = "FEDERAL"
    SCHOOL = "SCHOOL"
    RECOMMENDED = "RECOMMENDED"
    EVENT_BASED = "EVENT_BASED"
    ESTIMATE = "ESTIMATE"
    USER_DECISION = "USER_DECISION"
    UNKNOWN = "UNKNOWN"


class DateState(str, Enum):
    USER_CONFIRMED = "USER_CONFIRMED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class Risk(str, Enum):
    AT_RISK = "AT_RISK"
    GAP_WARNING = "GAP_WARNING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    WINDOW_CLOSED = "WINDOW_CLOSED"
    CONFLICT = "CONFLICT"


class WindowStatus(str, Enum):
    NOT_OPEN = "NOT_OPEN"  # before P - 90
    OPEN = "OPEN"  # P - 90 .. P
    AFTER_PROGRAM_END = "AFTER_PROGRAM_END"  # P + 1 .. P + 60
    CLOSED = "CLOSED"  # after P + 60


class StartPreference(str, Enum):
    ASAP = "ASAP"
    SPECIFIC_DATE = "SPECIFIC_DATE"
    NOT_SURE = "NOT_SURE"


class TimelineParams(BaseModel):
    """Policy values; in production they come from the reviewed UW Policy Pack, never hard-coded."""

    t_school: int  # T_s
    t_uscis_standard: int  # T_u
    t_uscis_premium: int  # T_u with premium processing
    buffer: int  # B
    school_window_open: date | None = None  # W_s; None = no data, constraint skipped


class TimelineInput(BaseModel):
    program_end: date  # P
    today: date
    has_offer: bool
    offer_start: date | None = None  # S
    dso_rec: date | None = None  # R
    i20_request: date | None = None
    uscis_receipt: date | None = None
    requested_start: date | None = None  # start date written on the filed I-765
    start_preference: StartPreference = StartPreference.NOT_SURE
    preferred_start: date | None = None
    premium: bool = False


class Node(BaseModel):
    id: str  # N1, N1b, N2 .. N7
    date: date | None
    due_type: DueType
    date_state: DateState


class TimelineResult(BaseModel):
    branch: str  # OFFER | NO_OFFER
    window: WindowStatus
    nodes: list[Node]
    risks: list[Risk]
    too_early: bool = False

    def node(self, node_id: str) -> Node:
        return next(n for n in self.nodes if n.id == node_id)


def _days(n: int) -> timedelta:
    return timedelta(days=n)


def window_status(p: date, today: date) -> WindowStatus:
    if today < p - _days(90):
        return WindowStatus.NOT_OPEN
    if today <= p:
        return WindowStatus.OPEN
    if today <= p + _days(60):
        return WindowStatus.AFTER_PROGRAM_END
    return WindowStatus.CLOSED


def _sorted(nodes: list[Node]) -> list[Node]:
    # Dated nodes in date order; unknown dates keep their flow order at the end.
    return sorted(nodes, key=lambda n: (n.date is None, n.date or date.max))


def compute_timeline(inp: TimelineInput, params: TimelineParams) -> TimelineResult:
    p, r, today = inp.program_end, inp.dso_rec, inp.today
    filed = inp.uscis_receipt is not None
    branch = "OFFER" if inp.has_offer else "NO_OFFER"
    window = window_status(p, today)

    def result(nodes: list[Node], risks: list[Risk], too_early: bool = False) -> TimelineResult:
        return TimelineResult(branch=branch, window=window, nodes=_sorted(nodes), risks=risks, too_early=too_early)

    if inp.has_offer and inp.offer_start is None:
        raise ValueError("offer_start is required when has_offer is true")

    # PRD 8.4: window closed and nothing filed -> no timeline.
    if window == WindowStatus.CLOSED and not filed:
        return result([], [Risk.WINDOW_CLOSED])
    # PRD 6.2: starting on or before P is not post-completion OPT.
    if inp.has_offer and inp.offer_start <= p:
        return result([], [Risk.OUT_OF_SCOPE])

    risks: list[Risk] = []
    r_state = DateState.USER_CONFIRMED if r else DateState.PARTIAL

    n2_date = max(p - _days(90), r) if r else p - _days(90)
    n4_date = min(p + _days(60), r + _days(30)) if r else p + _days(60)
    # PRD 8.4: no legal filing date exists, or R is after USCIS already received the filing.
    conflict = r is not None and (r + _days(30) < p - _days(90) or (filed and r > inp.uscis_receipt))
    if conflict:
        risks.append(Risk.CONFLICT)

    # PRD 8.4: more than 12 months out -> only show when the filing window opens.
    if (p - today).days > 365:
        n2 = Node(id="N2", date=p - _days(90), due_type=DueType.FEDERAL, date_state=DateState.PARTIAL)
        return result([n2], risks, too_early=True)

    t_uscis = params.t_uscis_premium if inp.premium else params.t_uscis_standard

    # N3: recommended filing date.
    if conflict:
        n3_date = None
    elif inp.has_offer:
        n3_raw = inp.offer_start - _days(t_uscis + params.buffer)
        n3_date = max(n3_raw, n2_date)
        if not filed and (n3_raw < n2_date or n3_raw < today):
            risks.append(Risk.AT_RISK)
    else:
        n3_date = max(n2_date, today)

    # N1: target date to request the OPT I-20 from the school.
    if n3_date is None:
        n1_date = None
    elif inp.has_offer:
        floors = [p - _days(120 + params.t_school)]
        if params.school_window_open:
            floors.append(params.school_window_open)
        n1_date = max([n3_date - _days(params.t_school), *floors])
    else:
        n1_date = p - _days(90 + params.t_school)
        if params.school_window_open:
            n1_date = max(n1_date, params.school_window_open)
    # PRD 8.4: a back-calculated date already in the past means the plan is late.
    i20_pending = r is None and inp.i20_request is None
    if inp.has_offer and not filed and i20_pending and n1_date and n1_date < today and Risk.AT_RISK not in risks:
        risks.append(Risk.AT_RISK)
    if conflict:
        n1_state = DateState.CONFLICT
    elif params.school_window_open is None:
        n1_state = DateState.PARTIAL
    else:
        n1_state = r_state

    # N1b: when the OPT I-20 should arrive.
    if r:
        n1b = Node(id="N1b", date=r, due_type=DueType.EVENT_BASED, date_state=DateState.USER_CONFIRMED)
    else:
        requested = inp.i20_request or n1_date
        n1b = Node(
            id="N1b",
            date=requested + _days(params.t_school) if requested else None,
            due_type=DueType.ESTIMATE,
            date_state=DateState.USER_CONFIRMED if inp.i20_request else DateState.PARTIAL,
        )

    # N5: start date written on the I-765. Once filed it is fixed (PRD 6.2: changing S later does not recompute it).
    if inp.has_offer and inp.offer_start > p + _days(60):
        risks.append(Risk.GAP_WARNING)
    if filed and inp.requested_start:
        n5_date = inp.requested_start
    elif inp.has_offer:
        n5_date = min(inp.offer_start, p + _days(60))
    elif inp.start_preference == StartPreference.ASAP:
        n5_date = min(max(p + _days(1), today), p + _days(60))
    elif inp.start_preference == StartPreference.SPECIFIC_DATE:
        if inp.preferred_start is None or not (p + _days(1) <= inp.preferred_start <= p + _days(60)):
            raise ValueError("preferred_start must be between P + 1 and P + 60")
        n5_date = inp.preferred_start
    else:
        n5_date = None

    # N6: estimated EAD arrival; N7: earliest day the student can start working.
    filing_date = inp.uscis_receipt or n3_date
    n6_date = filing_date + _days(t_uscis) if filing_date else None
    n7_date = max(d for d in (n5_date, n6_date) if d) if n5_date and n6_date else None

    conflict_state = DateState.CONFLICT if conflict else None
    nodes = [
        Node(id="N1", date=n1_date, due_type=DueType.RECOMMENDED, date_state=n1_state),
        n1b,
        Node(id="N2", date=None if conflict else n2_date, due_type=DueType.FEDERAL,
             date_state=conflict_state or r_state),
        Node(id="N3", date=n3_date, due_type=DueType.RECOMMENDED, date_state=conflict_state or r_state),
        Node(id="N4", date=None if conflict else n4_date, due_type=DueType.FEDERAL,
             date_state=conflict_state or r_state),
        Node(id="N5", date=n5_date, due_type=DueType.USER_DECISION,
             date_state=DateState.USER_CONFIRMED if n5_date else DateState.UNKNOWN),
        Node(id="N6", date=n6_date, due_type=DueType.ESTIMATE,
             date_state=DateState.USER_CONFIRMED if filed else (DateState.PARTIAL if n6_date else DateState.UNKNOWN)),
        Node(id="N7", date=n7_date, due_type=DueType.EVENT_BASED,
             date_state=DateState.PARTIAL if n7_date else DateState.UNKNOWN),
    ]
    return result(nodes, risks)
