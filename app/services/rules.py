"""Rules engine: decides which tasks apply to a profile. Pure functions, no LLM."""

from collections.abc import Set
from typing import Any

from pydantic import BaseModel

from app.schemas.catalog import Catalog, CatalogStep, CatalogTask, Condition
from app.schemas.profile import Profile


class Recommendation(BaseModel):
    task_id: str
    reason: str
    blocked_by: list[str]


def _evaluate3(cond: Condition, profile: dict[str, Any]) -> bool | None:
    """Three-valued logic: None means "depends on an unanswered question"."""
    if "all" in cond:
        results = [_evaluate3(c, profile) for c in cond["all"]]
        if False in results:
            return False
        return None if None in results else True
    if "any" in cond:
        results = [_evaluate3(c, profile) for c in cond["any"]]
        if True in results:
            return True
        return None if None in results else False
    if "not" in cond:
        inner = _evaluate3(cond["not"], profile)
        return None if inner is None else not inner
    value = profile.get(cond["field"])
    if value is None:
        return None
    if "eq" in cond:
        return value == cond["eq"]
    if "in" in cond:
        return value in cond["in"]
    raise ValueError(f"unknown condition: {cond}")


def evaluate(cond: Condition, profile: dict[str, Any]) -> bool:
    """True only when the answers given so far definitely satisfy the condition."""
    return _evaluate3(cond, profile) is True


def recommend(
    profile: Profile, catalog: Catalog, done_task_ids: Set[str] = frozenset()
) -> list[Recommendation]:
    data = profile.model_dump()
    return [
        Recommendation(
            task_id=task.id,
            reason=task.reason,
            blocked_by=[d for d in task.depends_on if d not in done_task_ids],
        )
        for task in catalog.tasks.values()
        if evaluate(task.when, data)
    ]


def visible_steps(task: CatalogTask, profile: Profile) -> list[CatalogStep]:
    data = profile.model_dump()
    return [s for s in task.steps if s.when is None or evaluate(s.when, data)]
