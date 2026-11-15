from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.schemas.catalog import Catalog, CatalogEvent, CatalogTask, Condition
from app.schemas.profile import Profile

CATALOG_DIR = Path(__file__).resolve().parent.parent / "catalog" / "legacy"
PROFILE_FIELDS = set(Profile.model_fields)


def _check_condition(cond: Condition, where: str) -> None:
    if not isinstance(cond, dict):
        raise ValueError(f"{where}: condition must be a mapping, got {cond!r}")
    if set(cond) == {"all"} or set(cond) == {"any"}:
        items = next(iter(cond.values()))
        if not isinstance(items, list) or not items:
            raise ValueError(f"{where}: 'all'/'any' needs a non-empty list")
        for c in items:
            _check_condition(c, where)
    elif set(cond) == {"not"}:
        _check_condition(cond["not"], where)
    elif set(cond) in ({"field", "eq"}, {"field", "in"}):
        if cond["field"] not in PROFILE_FIELDS:
            raise ValueError(f"{where}: unknown profile field {cond['field']!r}")
        if "in" in cond and not isinstance(cond["in"], list):
            raise ValueError(f"{where}: 'in' needs a list")
    else:
        raise ValueError(f"{where}: unsupported condition {cond!r}")


def _check_fields(fields: list[str], where: str) -> None:
    unknown = set(fields) - PROFILE_FIELDS
    if unknown:
        raise ValueError(f"{where}: unknown profile fields {sorted(unknown)}")


def load_catalog(root: Path) -> Catalog:
    tasks: dict[str, CatalogTask] = {}
    for path in sorted((root / "tasks").glob("*.yaml")):
        try:
            task = CatalogTask.model_validate(yaml.safe_load(path.read_text()))
        except ValidationError as e:
            raise ValueError(f"{path.name}: {e}") from e
        where = f"{path.name} ({task.id})"
        if task.id in tasks:
            raise ValueError(f"{where}: duplicate task id")
        step_ids = [s.id for s in task.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError(f"{where}: duplicate step id")
        _check_condition(task.when, where)
        for step in task.steps:
            if step.when is not None:
                _check_condition(step.when, f"{where} step {step.id}")
        _check_fields(task.personalize_on, where)
        tasks[task.id] = task

    for task in tasks.values():
        missing = set(task.depends_on) - set(tasks)
        if missing:
            raise ValueError(f"{task.id}: depends_on unknown tasks {sorted(missing)}")

    events: dict[str, CatalogEvent] = {}
    raw_events = yaml.safe_load((root / "events.yaml").read_text()) or []
    for raw in raw_events:
        try:
            event = CatalogEvent.model_validate(raw)
        except ValidationError as e:
            raise ValueError(f"events.yaml: {e}") from e
        if event.id in events:
            raise ValueError(f"events.yaml ({event.id}): duplicate event id")
        _check_fields(event.extract_fields, f"events.yaml ({event.id})")
        _check_fields(list(event.profile_updates), f"events.yaml ({event.id})")
        events[event.id] = event

    return Catalog(tasks=tasks, events=events)


@lru_cache
def get_catalog() -> Catalog:
    return load_catalog(CATALOG_DIR)
