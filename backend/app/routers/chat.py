from uuid import UUID

from fastapi import APIRouter, Depends

from app.deps import current_user
from app.schemas.api import ChatRequest, ChatResponse
from app.services.chat import handle_chat
from app.services.store import Store, get_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest, uid: UUID = Depends(current_user), store: Store = Depends(get_store)):
    return handle_chat(store, uid, body.message)
