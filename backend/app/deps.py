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


def current_session(authorization: str | None = Header(None)) -> str:
    """OPT API auth: "Authorization: Bearer <token>" from /api/auth/email/verify.

    Mock: any non-empty bearer token is accepted until real sessions exist.
    """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "unauthenticated", "Log in first")
    return token.strip()
