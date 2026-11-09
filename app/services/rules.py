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


def evaluate(cond: Condition, profile: dict[str, Any]) -> bool:
    if "all" in cond:
        return all(evaluate(c, profile) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, profile) for c in cond["any"])
    if "not" in cond:
        return not evaluate(cond["not"], profile)
    value = profile.get(cond["field"])
    if value is None:  # unanswered questions never match
        return False
    if "eq" in cond:
        return value == cond["eq"]
    if "in" in cond:
        return value in cond["in"]
    raise ValueError(f"unknown condition: {cond}")


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
