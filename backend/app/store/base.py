"""What the API needs from storage: users, login sessions, and each user's OPT state."""

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Protocol

from app.schemas.opt import Profile, TaskStatus

SESSION_DAYS = 30


@dataclass
class UserState:
    """One user's data. Routes load it, change it, then call Store.save()."""

    user_id: str
    email: str
    timezone: str = "America/Los_Angeles"
    profile: Profile | None = None  # None until onboarding
    task_statuses: dict[str, TaskStatus] = field(default_factory=dict)
    plan_version: int = 1


class Store(Protocol):
    def login(self, email: str, timezone: str) -> tuple[str, bool]:
        """Find or create the user by email and open a session. Returns (token, is_new_user)."""

    def state_for(self, token: str) -> UserState | None:
        """The user behind a live session token, or None if the token is unknown or expired."""

    def save(self, state: UserState) -> None: ...

    def logout(self, token: str) -> None: ...

    def delete_user(self, token: str) -> None:
        """Delete the session's user and all their data (PRD F02b)."""


def new_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    """Only token hashes are stored (Data Spec U3)."""
    return hashlib.sha256(token.encode()).hexdigest()
