from fastapi import APIRouter

from app.errors import ApiError
from app.mock import opt_demo
from app.opt.content import get_content
from app.schemas.opt import Office, SchoolSearchResponse

router = APIRouter(prefix="/api/schools", tags=["schools"])


@router.get("", response_model=SchoolSearchResponse)
def search_schools(q: str = "") -> SchoolSearchResponse:
    needle = q.strip().lower()
    return SchoolSearchResponse(schools=[s for s in opt_demo.schools() if needle in s.school_name.lower()])


@router.get("/{school_id}/office", response_model=Office)
def school_office(school_id: str) -> Office:
    policy = get_content().policy
    if school_id != policy.school_id:
        raise ApiError(404, "not_found", f"No office information for school {school_id!r}")
    return policy.office
