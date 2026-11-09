from datetime import date
from typing import Any

from pydantic import BaseModel

# A rule condition, e.g. {"all": [{"field": "has_ssn", "eq": False}, ...]}.
# Shape is validated by app.catalog_loader.
Condition = dict[str, Any]


class SourceRef(BaseModel):
    url: str
    title: str | None = None
    verified_at: date


class CatalogStep(BaseModel):
    id: str
    title: str
    materials: list[str] = []
    sources: list[SourceRef] = []
    when: Condition | None = None


class CatalogTask(BaseModel):
    id: str
    version: int
    title: str
    when: Condition
    reason: str
    depends_on: list[str] = []
    personalize_on: list[str] = []
    steps: list[CatalogStep]


class CatalogEvent(BaseModel):
    id: str
    description: str
    profile_updates: dict[str, Any] = {}
    extract_fields: list[str] = []


class Catalog(BaseModel):
    tasks: dict[str, CatalogTask]
    events: dict[str, CatalogEvent]
