"""In-memory store: used when DATABASE_URL is not set (local dev without Postgres, tests).

Hands out copies, so a request that fails part way leaves stored data untouched, like a database.
"""

import copy
import uuid
from datetime import datetime, timezone

from app.schemas.opt import AssistantFeedbackRequest, HistoryEntry
from app.store.base import UserState, apply_restore, clear_for_reset, hash_token, new_token


class MemoryStore:
    def __init__(self) -> None:
        self._users: dict[str, UserState] = {}  # by user_id
        self._sessions: dict[str, str] = {}  # token hash -> user_id
        self._history: dict[str, list[HistoryEntry]] = {}  # by user_id, oldest first
        self._feedback: dict[str, list[AssistantFeedbackRequest]] = {}  # by user_id

    def _by_email(self, email: str) -> UserState | None:
        return next((u for u in self._users.values() if u.email == email), None)

    def login(self, email: str, timezone: str) -> tuple[str, bool]:
        email = email.strip().lower()
        user = self._by_email(email)
        is_new = user is None
        if user is None:
            user = UserState(user_id=str(uuid.uuid4()), email=email, timezone=timezone)
            self._users[user.user_id] = user
        token = new_token()
        self._sessions[hash_token(token)] = user.user_id
        return token, is_new

    def state_for(self, token: str) -> UserState | None:
        user_id = self._sessions.get(hash_token(token))
        user = self._users.get(user_id) if user_id else None
        return copy.deepcopy(user) if user else None

    def save(self, state: UserState) -> None:
        if state.user_id in self._users:
            self._users[state.user_id] = copy.deepcopy(state)

    def logout(self, token: str) -> None:
        self._sessions.pop(hash_token(token), None)

    def delete_user(self, token: str) -> None:
        user_id = self._sessions.get(hash_token(token))
        if user_id:
            self._users.pop(user_id, None)
            self._history.pop(user_id, None)
            self._feedback.pop(user_id, None)
            for h in [h for h, u in self._sessions.items() if u == user_id]:
                del self._sessions[h]

    def _archive(self, state: UserState) -> None:
        if state.profile is not None:
            self._history.setdefault(state.user_id, []).append(HistoryEntry(
                id=str(uuid.uuid4()), archived_at=datetime.now(timezone.utc), plan_version=state.plan_version,
                profile=copy.deepcopy(state.profile), task_statuses=dict(state.task_statuses)))

    def reset(self, state: UserState) -> None:
        if state.user_id not in self._users:
            return
        self._archive(state)
        clear_for_reset(state)
        self.save(state)

    def restore(self, state: UserState, entry_id: str) -> bool:
        entries = self._history.get(state.user_id, [])
        entry = next((e for e in entries if e.id == entry_id), None)
        if entry is None or state.user_id not in self._users:
            return False
        entries.remove(entry)
        self._archive(state)
        apply_restore(state, entry)
        self.save(state)
        return True

    def history(self, user_id: str) -> list[HistoryEntry]:
        return copy.deepcopy(list(reversed(self._history.get(user_id, []))))

    def add_feedback(self, user_id: str, feedback: AssistantFeedbackRequest) -> str:
        self._feedback.setdefault(user_id, []).append(feedback.model_copy())
        return str(uuid.uuid4())
