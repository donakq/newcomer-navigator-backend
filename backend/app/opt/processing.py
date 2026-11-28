"""Processing-time choices: the official ranges from the catalog plus the student's own picks."""

from app.opt.content import get_content
from app.schemas.opt import ProcessingTime, Profile

PROCESSING_LABELS = {
    "school_business_days": "UW ISS processing of your OPT I-20",
    "uscis_standard_days": "USCIS processing (standard)",
    "uscis_premium_business_days": "USCIS processing (premium)",
}


def processing_times(profile: Profile) -> list[ProcessingTime]:
    """Ranges from the catalog plus the student's picks; the plan uses each one's `used` value."""
    content = get_content()
    ranges = {
        "school_business_days": content.policy.timeline.t_school,
        "uscis_standard_days": content.federal.processing.uscis_standard,
        "uscis_premium_business_days": content.federal.processing.uscis_premium,
    }
    out = []
    for field, r in ranges.items():
        chosen = getattr(profile.processing, field)
        out.append(ProcessingTime(
            id=field, label=PROCESSING_LABELS[field], min=r.min, max=r.max, default=r.default, unit=r.unit,
            chosen=chosen, used=chosen if chosen is not None else r.default, note=r.note, source_ids=r.source_ids,
        ))
    return out
