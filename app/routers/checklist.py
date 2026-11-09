from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.schemas.api import ChecklistActionRequest
from app.services.checklist import add_or_dismiss, list_checklist
from app.services.store import Store, get_store

router = APIRouter(prefix="/api/checklist", tags=["checklist"])


@router.get("")
def read_checklist(uid: UUID = Depends(current_user), store: Store = Depends(get_store)):
    return {"tasks": list_checklist(store, uid)}


@router.post("/{task_id}")
def change_checklist(
    task_id: str,
    body: ChecklistActionRequest,
    uid: UUID = Depends(current_user),
    store: Store = Depends(get_store),
):
    return {"task": add_or_dismiss(store, uid, task_id, body.action)}
