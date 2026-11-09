from uuid import UUID

from app.ai import client as llm
from app.schemas.api import ChatResponse, DsoDraft
from app.services.store import Store
from app.services.tasks import get_catalog_task, get_visible_step

CHAT_SYSTEM = (
    "You are a helpful assistant for international students who just arrived in the US. "
    "Keep replies under 80 words."
)
CHAT_FALLBACK = (
    "Sorry, the assistant is unavailable right now. "
    "Your checklist and task pages still work, and your DSO can answer questions about your situation."
)
DSO_PLACEHOLDERS = ["YOUR FULL NAME", "YOUR SEVIS ID"]


def handle_chat(store: Store, uid: UUID, message: str) -> ChatResponse:
    store.append_message(uid, "user", message, {})
    try:
        reply = llm.complete(CHAT_SYSTEM, message)
        meta = {"llm": True}
    except llm.LLMUnavailable as e:
        reply = CHAT_FALLBACK
        meta = {"llm": False, "error": str(e)}
    store.append_message(uid, "assistant", reply, meta)
    return ChatResponse(
        reply=reply, detected_events=[], profile_updates={}, checklist_diff=None, citations=[]
    )


def draft_dso_email(store: Store, uid: UUID, task_id: str, step_id: str, question: str | None) -> DsoDraft:
    """Fixed-template draft (the spec's fallback path); the LLM-written version comes later."""
    task = get_catalog_task(task_id)
    step = get_visible_step(task, store.get_profile(uid), step_id)

    questions = [question] if question else []
    questions.append(f"What do I need to do for this step: {step.title}?")
    question_lines = "\n".join(f"- {q}" for q in questions)
    body = (
        "Dear DSO,\n\n"
        f"I am working on: {task.title}. I have a question about this step: {step.title}.\n\n"
        f"{question_lines}\n\n"
        "Thank you for your help.\n\n"
        "Best regards,\n"
        "[YOUR FULL NAME]\n"
        "SEVIS ID: [YOUR SEVIS ID]"
    )
    return DsoDraft(
        subject=f"Question about {task.title}: {step.title}",
        body=body,
        questions=questions,
        bring_list=step.materials,
        placeholders=DSO_PLACEHOLDERS,
    )
