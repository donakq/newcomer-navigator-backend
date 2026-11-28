"""What the API needs from storage: users, login sessions, and each user's OPT state."""

import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Protocol

from app.config import DEFAULT_TIMEZONE
from app.schemas.opt import AssistantFeedbackRequest, HistoryEntry, Profile, TaskStatus

SESSION_DAYS = 30


@dataclass
class UserState:
    """One user's data. Routes load it, change it, then call Store.save()."""

    user_id: str
    email: str
    timezone: str = DEFAULT_TIMEZONE
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

    def reset(self, state: UserState) -> None:
        """Start over: archive the current profile and task statuses as a history entry (if onboarded),
        then clear them so the user goes back to onboarding. Done in one transaction."""

    def history(self, user_id: str) -> list[HistoryEntry]:
        """Archived plans, newest first."""

    def restore(self, state: UserState, entry_id: str) -> bool:
        """Make one of the user's archived plans current again, in one transaction. The plan that was
        current (if any) goes to history; the restored entry leaves it. False if the entry is not theirs."""

    def add_feedback(self, user_id: str, feedback: AssistantFeedbackRequest) -> str:
        """Store one rating of an assistant answer. Returns its id."""


def new_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    """Only token hashes are stored (Data Spec U3)."""
    return hashlib.sha256(token.encode()).hexdigest()


def apply_restore(state: UserState, entry: HistoryEntry) -> None:
    """Load an archived plan into the live state. Policy info is refreshed to the current catalog."""
    from app.mock.opt_demo import policy_version
    from app.opt.content import get_content

    content = get_content()
    state.profile = entry.profile.model_copy(update={
        "policy_version": policy_version(content), "policy_last_reviewed": content.policy.reviewed_at})
    state.task_statuses = dict(entry.task_statuses)
    state.plan_version += 1


def clear_for_reset(state: UserState) -> None:
    """What starting over does to the live state: back to before onboarding, new plan version."""
    state.profile = None
    state.task_statuses = {}
    state.plan_version += 1
