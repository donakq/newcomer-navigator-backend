from fastapi import APIRouter

from app.errors import ApiError
from app.mock.opt_demo import SCHOOLS, UW, UW_OFFICE
from app.schemas.opt import Office, SchoolSearchResponse

router = APIRouter(prefix="/api/schools", tags=["schools"])


@router.get("", response_model=SchoolSearchResponse)
def search_schools(q: str = "") -> SchoolSearchResponse:
    needle = q.strip().lower()
    return SchoolSearchResponse(schools=[s for s in SCHOOLS if needle in s.school_name.lower()])


@router.get("/{school_id}/office", response_model=Office)
def school_office(school_id: str) -> Office:
    if school_id != UW.id:
        raise ApiError(404, "not_found", f"No office information for school {school_id!r}")
    return UW_OFFICE
