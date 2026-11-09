from uuid import UUID

from app.catalog_loader import get_catalog
from app.errors import ApiError
from app.schemas.api import Source, Step, StepUpdateResponse, TaskDetail
from app.schemas.catalog import CatalogStep, CatalogTask
from app.schemas.profile import Profile
from app.services.checklist import task_progress
from app.services.rules import visible_steps
from app.services.store import Store, UserTask


def get_catalog_task(task_id: str) -> CatalogTask:
    task = get_catalog().tasks.get(task_id)
    if task is None:
        raise ApiError(404, "not_found", f"Unknown task {task_id!r}")
    return task


def get_visible_step(task: CatalogTask, profile: Profile, step_id: str) -> CatalogStep:
    step = next((s for s in visible_steps(task, profile) if s.id == step_id), None)
    if step is None:
        raise ApiError(404, "not_found", f"Unknown step {step_id!r} for task {task.id!r}")
    return step


def _to_step(step: CatalogStep, done: bool) -> Step:
    return Step(
        id=step.id,
        title=step.title,
        materials=step.materials,
        done=done,
        sources=[Source(**s.model_dump()) for s in step.sources],
    )


def get_task_detail(store: Store, uid: UUID, task_id: str) -> TaskDetail:
    task = get_catalog_task(task_id)
    profile = store.get_profile(uid)
    done = store.get_done_steps(uid, task_id)
    status, progress = task_progress(store, uid, task, profile)
    return TaskDetail(
        id=task.id,
        title=task.title,
        personalized=False,  # AI personalization comes in a later plan
        status=status,
        progress=progress,
        steps=[_to_step(s, s.id in done) for s in visible_steps(task, profile)],
    )


def set_step_done(store: Store, uid: UUID, task_id: str, step_id: str, done: bool) -> StepUpdateResponse:
    task = get_catalog_task(task_id)
    profile = store.get_profile(uid)
    step = get_visible_step(task, profile, step_id)
    store.set_step(uid, task_id, step_id, done)
    status, progress = task_progress(store, uid, task, profile)
    user_task = store.get_user_tasks(uid).get(task_id) or UserTask(
        task_id=task_id, status=status, source="manual"
    )
    store.save_user_task(uid, user_task.model_copy(update={"status": status}))
    return StepUpdateResponse(step=_to_step(step, done), task_status=status, progress=progress)
