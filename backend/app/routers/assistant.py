from fastapi import APIRouter, Depends

from app.store import UserState, get_store
from app.routers.me import current_state
from app.mock import opt_assistant
from app.schemas.opt import AssistantFeedbackRequest, AssistantFeedbackResponse, AssistantRequest, AssistantResponse

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/messages", response_model=AssistantResponse)
def send_message(body: AssistantRequest, _: UserState = Depends(current_state)) -> AssistantResponse:
    return opt_assistant.reply(body)


@router.post("/feedback", status_code=201, response_model=AssistantFeedbackResponse)
def send_feedback(body: AssistantFeedbackRequest, state: UserState = Depends(current_state)) -> AssistantFeedbackResponse:
    """Thumbs up / down on an answer, with optional reasons and a short comment."""
    return AssistantFeedbackResponse(id=get_store().add_feedback(state.user_id, body))
