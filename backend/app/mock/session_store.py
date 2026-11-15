"""In-memory users and sessions for the mock OPT API.

Each email gets its own profile and task statuses, so a connected frontend behaves like the real
app. Everything is lost when the process restarts (and on Vercel, when the function is recycled);
Postgres replaces this module.
"""

import secrets
from dataclasses import dataclass, field

from app.schemas.opt import Profile, TaskStatus


@dataclass
class UserState:
    email: str
    timezone: str = "America/Los_Angeles"
    profile: Profile | None = None  # None until onboarding
    task_statuses: dict[str, TaskStatus] = field(default_factory=dict)
    plan_version: int = 1


_users: dict[str, UserState] = {}  # by email
_tokens: dict[str, str] = {}  # token -> email


def login(email: str, timezone: str) -> tuple[str, bool]:
    email = email.strip().lower()
    is_new = email not in _users
    if is_new:
        _users[email] = UserState(email=email, timezone=timezone)
    token = secrets.token_urlsafe(24)
    _tokens[token] = email
    return token, is_new


def state_for(token: str) -> UserState | None:
    email = _tokens.get(token)
    return _users.get(email) if email else None


def logout(token: str) -> None:
    _tokens.pop(token, None)


def delete_user(token: str) -> None:
    email = _tokens.get(token)
    if email:
        _users.pop(email, None)
        for t in [t for t, e in _tokens.items() if e == email]:
            del _tokens[t]


def reset() -> None:
    _users.clear()
    _tokens.clear()
