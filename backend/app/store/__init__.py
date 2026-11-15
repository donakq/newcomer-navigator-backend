"""Storage for users and their OPT data.

DATABASE_URL set -> Postgres (SqlStore); not set -> in memory (MemoryStore, data lost on restart).
"""

from app import config
from app.store.base import Store, UserState

_store: Store | None = None


def get_store() -> Store:
    global _store
    if _store is None:
        if config.DATABASE_URL:
            from app.store.sql import SqlStore

            _store = SqlStore(config.DATABASE_URL)
        else:
            from app.store.memory import MemoryStore

            _store = MemoryStore()
    return _store


def set_store(store: Store) -> None:
    """Tests: swap in a fresh store."""
    global _store
    _store = store


__all__ = ["Store", "UserState", "get_store", "set_store"]
