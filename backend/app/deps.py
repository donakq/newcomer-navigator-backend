from fastapi import Header

from app.errors import ApiError


def current_session(authorization: str | None = Header(None)) -> str:
    """OPT API auth: "Authorization: Bearer <token>" from /api/auth/email/verify.

    Only parses the header; routes look the token up (app.routers.me.current_state).
    """
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "unauthenticated", "Log in first")
    return token.strip()
