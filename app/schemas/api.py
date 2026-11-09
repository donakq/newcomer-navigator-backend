"""Request and response models: the API contract with the frontend."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.store import TaskStatus


class Source(BaseModel):
    url: str
    title: str | None = None
    verified_at: date


class ChecklistDiff(BaseModel):
    added: list[str] = []
    removed: list[str] = []
    flagged: list[str] = []


class ChecklistItem(BaseModel):
    id: str
    title: str
    reason: str
    status: TaskStatus
    progress: float
    blocked_by: list[str]
    maybe_not_applicable: bool


class Step(BaseModel):
    id: str
    title: str
    materials: list[str]
    applies: bool = True
    note: str | None = None
    warnings: list[str] = []
    done: bool
    sources: list[Source]


class TaskDetail(BaseModel):
    id: str
    title: str
    personalized: bool
    status: TaskStatus
    progress: float
    steps: list[Step]


class Citation(BaseModel):
    chunk_id: str
    source: Source


class ChatResponse(BaseModel):
    reply: str
    detected_events: list[str]
    profile_updates: dict[str, Any]
    checklist_diff: ChecklistDiff | None
    citations: list[Citation]


class DsoDraft(BaseModel):
    subject: str
    body: str
    questions: list[str]
    bring_list: list[str]
    placeholders: list[str]


class ProfileUpdateRequest(BaseModel):
    answers: dict[str, Any]


class ChecklistActionRequest(BaseModel):
    action: Literal["add", "dismiss"]


class StepUpdateRequest(BaseModel):
    done: bool


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class DsoDraftRequest(BaseModel):
    question: str | None = Field(None, max_length=2000)
