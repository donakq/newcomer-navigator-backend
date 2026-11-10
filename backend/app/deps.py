from uuid import UUID

from fastapi import Header

from app.errors import ApiError


def current_user(x_user_id: str | None = Header(None)) -> UUID:
    if not x_user_id:
        raise ApiError(400, "bad_user_id", "Missing X-User-Id header")
    try:
        return UUID(x_user_id)
    except ValueError:
        raise ApiError(400, "bad_user_id", "X-User-Id must be a UUID")
