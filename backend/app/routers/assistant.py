from fastapi import APIRouter, Depends

from app.mock.session_store import UserState
from app.routers.me import current_state
from app.mock import opt_assistant
from app.schemas.opt import AssistantRequest, AssistantResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/messages", response_model=AssistantResponse)
def send_message(body: AssistantRequest, _: UserState = Depends(current_state)) -> AssistantResponse:
    return opt_assistant.reply(body)
