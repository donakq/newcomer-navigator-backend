"""Email + code login (PRD F01). Mock: no email is sent, the code is always 000000, users live in memory."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Response

from app.deps import current_session
from app.mock import session_store
from app.errors import ApiError
from app.schemas.opt import EmailStartRequest, EmailStartResponse, EmailVerifyRequest, EmailVerifyResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

MOCK_CODE = "000000"


@router.post("/email/start", response_model=EmailStartResponse)
def email_start(body: EmailStartRequest) -> EmailStartResponse:
    return EmailStartResponse(resend_after_seconds=60, code_expires_in_seconds=600)


@router.post("/email/verify", response_model=EmailVerifyResponse)
def email_verify(body: EmailVerifyRequest) -> EmailVerifyResponse:
    if not body.tos_accepted:
        raise ApiError(422, "validation_error", "You must accept the terms to continue")
    if body.code != MOCK_CODE:
        raise ApiError(401, "invalid_code", "The code is wrong or expired")
    token, is_new = session_store.login(body.email, body.timezone)
    return EmailVerifyResponse(
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        is_new_user=is_new,
    )


@router.post("/logout", status_code=204, response_class=Response)
def logout(token: str = Depends(current_session)) -> Response:
    session_store.logout(token)
    return Response(status_code=204)
