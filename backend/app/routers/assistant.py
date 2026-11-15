from fastapi import APIRouter, Depends

from app.deps import current_session
from app.mock import opt_assistant
from app.schemas.opt import AssistantRequest, AssistantResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/messages", response_model=AssistantResponse)
def send_message(body: AssistantRequest, _: str = Depends(current_session)) -> AssistantResponse:
    return opt_assistant.reply(body)
