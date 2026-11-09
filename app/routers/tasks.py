from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.schemas.api import StepUpdateRequest, TaskDetail
from app.services.store import Store, get_store
from app.services.tasks import get_task_detail, set_step_done

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskDetail)
def read_task(task_id: str, uid: UUID = Depends(current_user), store: Store = Depends(get_store)):
    return get_task_detail(store, uid, task_id)


@router.patch("/{task_id}/steps/{step_id}")
def update_step(
    task_id: str,
    step_id: str,
    body: StepUpdateRequest,
    uid: UUID = Depends(current_user),
    store: Store = Depends(get_store),
):
    return set_step_done(store, uid, task_id, step_id, body.done)
