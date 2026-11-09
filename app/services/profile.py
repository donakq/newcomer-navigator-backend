from typing import Any, Literal
from uuid import UUID

from pydantic import ValidationError

from app.errors import ApiError
from app.schemas.api import ChecklistDiff
from app.schemas.profile import Profile
from app.services.checklist import recompute_checklist
from app.services.store import Store


def update_profile(
    store: Store, uid: UUID, patch: dict[str, Any], source: Literal["rule", "chat"]
) -> tuple[Profile, ChecklistDiff]:
    current = store.get_profile(uid)
    try:
        merged = Profile.model_validate({**current.model_dump(), **patch})
    except ValidationError as e:
        raise ApiError(422, "validation_error", e.errors()[0]["msg"]) from e
    store.save_profile(uid, merged)
    return merged, recompute_checklist(store, uid, merged, source)
