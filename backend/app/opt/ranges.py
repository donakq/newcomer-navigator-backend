"""Date ranges for the vertical timeline (design 2026-11-27-full-setup-and-vertical-timeline).

Derived from timeline nodes and the official processing-time min/max. The frontend only draws them.
"""

from datetime import date, timedelta

from app.opt.business_days import add_business_days
from app.opt.processing import processing_times
from app.opt.timeline import Risk, TimelineResult
from app.schemas.opt import (
    ProcessingTime,
    Profile,
    RangeAction,
    RangeKind,
    Stage,
    StartPreference,
    TimelineRange,
    YesNoNotSure,
)

START_WINDOW_DAYS = 60  # OPT start must be within P + 1 .. P + 60
BEFORE_RECOMMENDATION = (None, Stage.PLANNING, Stage.I20_REQUESTED)


def _add(day: date, n: int, unit: str) -> date:
    return add_business_days(day, n) if unit == "business_days" else day + timedelta(days=n)


def _unit_text(unit: str) -> str:
    return "business days" if unit == "business_days" else "days"


def build_ranges(profile: Profile, timeline: TimelineResult) -> list[TimelineRange]:
    # No ranges when the timeline itself has no usable dates (PRD 8.4).
    if not timeline.nodes or timeline.too_early or {Risk.CONFLICT, Risk.WINDOW_CLOSED} & set(timeline.risks):
        return []
    nodes = {n.id: n.date for n in timeline.nodes}
    times: dict[str, ProcessingTime] = {p.id: p for p in processing_times(profile)}
    dates = profile.stage_dates
    filed = dates.uscis_receipt_date is not None or profile.stage in (Stage.I765_FILED, Stage.APPROVED)
    offer = profile.offer
    out: list[TimelineRange] = []

    if nodes.get("N2") and nodes.get("N4") and not filed:
        out.append(TimelineRange(
            id="FILING_WINDOW", kind=RangeKind.LEGAL_WINDOW, label="You can file Form I-765",
            start=nodes["N2"], end=nodes["N4"],
            note=("The legal filing window: 30 days after your DSO recommendation, inside the federal window. "
                  if dates.dso_rec_date else
                  "The legal filing window. It narrows to 30 days after your DSO recommendation once you enter it. ")
                 + "Confirm with UW ISS.",
            action=RangeAction.CONFIRM_WITH_SCHOOL, related_task_ids=["T05"]))

    filing = dates.uscis_receipt_date or nodes.get("N3")
    if filing and profile.stage != Stage.APPROVED:
        premium = offer is not None and offer.premium_intent == YesNoNotSure.YES
        t = times["uscis_premium_business_days" if premium else "uscis_standard_days"]
        # Earliest = official minimum; latest = the student's own estimate (`used` = their pick, else the
        # conservative default, which is the official maximum).
        out.append(TimelineRange(
            id="EAD_ARRIVAL", kind=RangeKind.ESTIMATE, label="EAD card expected",
            start=_add(filing, t.min, t.unit), end=_add(filing, t.used, t.unit),
            note=f"Based on USCIS processing of {t.min}–{t.used} {_unit_text(t.unit)} after filing. "
                 "Adjust if you have better information.",
            action=RangeAction.ADJUST_PROCESSING, related_task_ids=["T06"]))

    base = dates.i20_request_date or nodes.get("N1")
    # The I-20 issue date already stands in for R on the timeline, so no estimate is needed then.
    if dates.dso_rec_date is None and dates.i20_issue_date is None and profile.stage in BEFORE_RECOMMENDATION and base:
        t = times["school_business_days"]
        out.append(TimelineRange(
            id="DSO_REC_DATE", kind=RangeKind.NEEDS_DATE, label="DSO recommendation date (expected)",
            start=_add(base, t.min, t.unit), end=_add(base, t.max, t.unit),
            note="We estimate this until you enter the date from your OPT I-20.",
            action=RangeAction.ENTER_DSO_REC_DATE, related_task_ids=["T03"]))

    if offer is not None and not offer.has_offer and offer.start_preference in (None, StartPreference.NOT_SURE):
        p = profile.program_end_date
        out.append(TimelineRange(
            id="START_DATE", kind=RangeKind.NEEDS_DATE, label="Choose your OPT start date",
            start=p + timedelta(days=1), end=p + timedelta(days=START_WINDOW_DAYS),
            note="Your start date must be within 60 days after your program end date.",
            action=RangeAction.PICK_START_DATE, related_task_ids=["T05"]))

    return sorted(out, key=lambda r: r.start)
