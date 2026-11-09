"""User-state storage. InMemoryStore is for the prototype; a Postgres store comes later."""

from collections import defaultdict
from typing import Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel

from app.schemas.profile import Profile

TaskStatus = Literal["not_started", "in_progress", "done"]
TaskSource = Literal["rule", "chat", "manual"]


class UserTask(BaseModel):
    task_id: str
    status: TaskStatus
    source: TaskSource
    dismissed: bool = False
    maybe_not_applicable: bool = False


class Store(Protocol):
    def get_profile(self, uid: UUID) -> Profile: ...
    def save_profile(self, uid: UUID, profile: Profile) -> None: ...
    def get_user_tasks(self, uid: UUID) -> dict[str, UserTask]: ...
    def save_user_task(self, uid: UUID, task: UserTask) -> None: ...
    def delete_user_task(self, uid: UUID, task_id: str) -> None: ...
    def get_done_steps(self, uid: UUID, task_id: str) -> set[str]: ...
    def set_step(self, uid: UUID, task_id: str, step_id: str, done: bool) -> None: ...
    def append_message(self, uid: UUID, role: str, content: str, meta: dict[str, Any]) -> None: ...
    def get_messages(self, uid: UUID) -> list[dict[str, Any]]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._profiles: dict[UUID, Profile] = {}
        self._tasks: dict[UUID, dict[str, UserTask]] = defaultdict(dict)
        self._steps: dict[tuple[UUID, str], set[str]] = defaultdict(set)
        self._messages: dict[UUID, list[dict[str, Any]]] = defaultdict(list)

    def get_profile(self, uid: UUID) -> Profile:
        return self._profiles.get(uid, Profile())

    def save_profile(self, uid: UUID, profile: Profile) -> None:
        self._profiles[uid] = profile

    def get_user_tasks(self, uid: UUID) -> dict[str, UserTask]:
        return dict(self._tasks[uid])

    def save_user_task(self, uid: UUID, task: UserTask) -> None:
        self._tasks[uid][task.task_id] = task

    def delete_user_task(self, uid: UUID, task_id: str) -> None:
        self._tasks[uid].pop(task_id, None)

    def get_done_steps(self, uid: UUID, task_id: str) -> set[str]:
        return set(self._steps[(uid, task_id)])

    def set_step(self, uid: UUID, task_id: str, step_id: str, done: bool) -> None:
        steps = self._steps[(uid, task_id)]
        if done:
            steps.add(step_id)
        else:
            steps.discard(step_id)

    def append_message(self, uid: UUID, role: str, content: str, meta: dict[str, Any]) -> None:
        self._messages[uid].append({"role": role, "content": content, "meta": meta})

    def get_messages(self, uid: UUID) -> list[dict[str, Any]]:
        return list(self._messages[uid])


_store: Store = InMemoryStore()


def get_store() -> Store:
    return _store


def reset_store() -> None:
    global _store
    _store = InMemoryStore()
