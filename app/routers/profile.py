from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.schemas.api import ProfileResponse, ProfileUpdateRequest, ProfileUpdateResponse
from app.services.profile import update_profile
from app.services.store import Store, get_store

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("", response_model=ProfileResponse)
def read_profile(uid: UUID = Depends(current_user), store: Store = Depends(get_store)):
    return {"profile": store.get_profile(uid)}


@router.post("", response_model=ProfileUpdateResponse)
def write_profile(
    body: ProfileUpdateRequest, uid: UUID = Depends(current_user), store: Store = Depends(get_store)
):
    profile, diff = update_profile(store, uid, body.answers, source="rule")
    return {"profile": profile, "checklist_diff": diff}
