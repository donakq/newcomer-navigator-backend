"""In-memory store: used when DATABASE_URL is not set (local dev without Postgres, tests).

Hands out copies, so a request that fails part way leaves stored data untouched, like a database.
"""

import copy
import uuid

from app.store.base import UserState, hash_token, new_token


class MemoryStore:
    def __init__(self) -> None:
        self._users: dict[str, UserState] = {}  # by user_id
        self._sessions: dict[str, str] = {}  # token hash -> user_id

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
            for h in [h for h, u in self._sessions.items() if u == user_id]:
                del self._sessions[h]
