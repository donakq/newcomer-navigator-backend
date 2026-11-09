"""Keeps each user's task list in sync with the rules engine."""

from typing import Literal
from uuid import UUID

from app.catalog_loader import get_catalog
from app.errors import ApiError
from app.schemas.api import ChecklistDiff, ChecklistItem
from app.schemas.catalog import CatalogTask
from app.schemas.profile import Profile
from app.services.rules import recommend, visible_steps
from app.services.store import Store, TaskStatus, UserTask


def task_progress(store: Store, uid: UUID, task: CatalogTask, profile: Profile) -> tuple[TaskStatus, float]:
    step_ids = {s.id for s in visible_steps(task, profile)}
    if not step_ids:
        return "not_started", 0.0
    done = store.get_done_steps(uid, task.id) & step_ids
    progress = len(done) / len(step_ids)
    if not done:
        return "not_started", progress
    return ("done" if progress == 1.0 else "in_progress"), progress


def recompute_checklist(
    store: Store, uid: UUID, profile: Profile, source: Literal["rule", "chat"]
) -> ChecklistDiff:
    catalog = get_catalog()
    existing = store.get_user_tasks(uid)
    applicable = {r.task_id for r in recommend(profile, catalog)}
    diff = ChecklistDiff()

    for task_id in catalog.tasks:
        current = existing.get(task_id)
        if task_id in applicable:
            if current is None:
                store.save_user_task(uid, UserTask(task_id=task_id, status="not_started", source=source))
                diff.added.append(task_id)
            elif current.maybe_not_applicable:
                store.save_user_task(uid, current.model_copy(update={"maybe_not_applicable": False}))
        elif current is not None and current.source != "manual" and not current.dismissed:
            if store.get_done_steps(uid, task_id):
                if not current.maybe_not_applicable:
                    store.save_user_task(uid, current.model_copy(update={"maybe_not_applicable": True}))
                    diff.flagged.append(task_id)
            else:
                store.delete_user_task(uid, task_id)
                diff.removed.append(task_id)
    return diff


def _active_tasks(store: Store, uid: UUID) -> dict[str, UserTask]:
    catalog = get_catalog()
    return {
        tid: t for tid, t in store.get_user_tasks(uid).items() if not t.dismissed and tid in catalog.tasks
    }


def _build_items(store: Store, uid: UUID, task_ids: list[str]) -> dict[str, ChecklistItem]:
    catalog = get_catalog()
    profile = store.get_profile(uid)
    active = _active_tasks(store, uid)
    states = {tid: task_progress(store, uid, catalog.tasks[tid], profile) for tid in active}
    # A dependency blocks only while it is on the user's list, still applies, and is not finished.
    blocking = {
        tid
        for tid, (status, _) in states.items()
        if status != "done" and not active[tid].maybe_not_applicable
    }
    items = {}
    for tid in task_ids:
        task = catalog.tasks[tid]
        status, progress = states.get(tid) or task_progress(store, uid, task, profile)
        user_task = store.get_user_tasks(uid).get(tid)
        items[tid] = ChecklistItem(
            id=tid,
            title=task.title,
            reason=task.reason,
            status=status,
            progress=progress,
            blocked_by=[d for d in task.depends_on if d in blocking],
            maybe_not_applicable=bool(user_task and user_task.maybe_not_applicable),
        )
    return items


def list_checklist(store: Store, uid: UUID) -> list[ChecklistItem]:
    ordered = [tid for tid in get_catalog().tasks if tid in _active_tasks(store, uid)]
    items = _build_items(store, uid, ordered)
    return [items[tid] for tid in ordered]


def add_or_dismiss(store: Store, uid: UUID, task_id: str, action: Literal["add", "dismiss"]) -> ChecklistItem:
    if task_id not in get_catalog().tasks:
        raise ApiError(404, "not_found", f"Unknown task {task_id!r}")
    current = store.get_user_tasks(uid).get(task_id) or UserTask(
        task_id=task_id, status="not_started", source="manual"
    )
    store.save_user_task(uid, current.model_copy(update={"dismissed": action == "dismiss"}))
    return _build_items(store, uid, [task_id])[task_id]
