"""Mock AI Widget replies: just enough logic to return every contract shape.

The real version (intent classifier, retrieval, refusal rules) replaces this in W3.
"""

import re
import uuid

from app.mock.opt_demo import demo_profile, source
from app.opt.content import get_content
from app.schemas.opt import (
    AssistantAction,
    AssistantRequest,
    AssistantResponse,
    DraftTone,
    DsoDraftRequest,
    DsoDraftResponse,
    Intent,
    Scope,
)

CJK = re.compile(r"[一-鿿]")
OUT_OF_SCOPE = ("h-1b", "h1b", "green card", "绿卡", "cpt", "visa renewal", "签证续签")
UNSUPPORTED_OPT = ("stem", "pre-completion")

# Fallback until catalog/ai/templates.yaml has unsupported_opt filled in (TODO(PM)).
UNSUPPORTED = {
    "en": "{topic} is not supported in v1 yet. Please check the official {office} page.",
    "zh": "v1 暂不支持 {topic}，请查看 {office} 官方页面。",
}
NEXT_STEP = {
    "en": "Your next step is to request your OPT I-20 from {office} (task T02).",
    "zh": "你的下一步是向 {office} 申请 OPT I-20（任务 T02）。",
}


def _language(text: str) -> str:
    return "zh" if CJK.search(text) else "en"


def reply(req: AssistantRequest) -> AssistantResponse:
    lang = _language(req.message)
    text = req.message.lower()
    content = get_content()
    office = content.policy.office.office_display_name
    refusal = content.templates.refusal
    conversation_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
    contact = AssistantAction(kind="OPEN_CONTACT_PANEL", label="Contact My International Student Office", target=None)

    topic = next((k for k in OUT_OF_SCOPE if k in text), None)
    if topic:
        return AssistantResponse(
            conversation_id=conversation_id, intent=None, scope=Scope.OUT, confidence=0.95, language=lang,
            answer=(getattr(refusal, lang) or refusal.en).format(
                topic=topic.upper() if topic.isascii() else topic, office_display_name=office),
            sources=[], follow_up=None, actions=[contact],
        )
    topic = next((k for k in UNSUPPORTED_OPT if k in text), None)
    if topic:
        return AssistantResponse(
            conversation_id=conversation_id, intent=None, scope=Scope.UNSUPPORTED_OPT, confidence=0.9,
            language=lang,
            answer=(getattr(content.templates.unsupported_opt, lang) or UNSUPPORTED[lang]).format(
                topic=topic.upper(), office=office, office_display_name=office),
            sources=[source("uw-post-completion-opt")], follow_up=None, actions=[contact],
        )
    return AssistantResponse(
        conversation_id=conversation_id, intent=Intent.NEXT_STEP, scope=Scope.IN, confidence=0.9, language=lang,
        answer=NEXT_STEP[lang].format(office=office),
        sources=[source("uw-post-completion-opt")], follow_up=None,
        actions=[AssistantAction(kind="OPEN_TASK", label=content.tasks["T02"].title, target="T02")],
    )


def draft(req: DsoDraftRequest) -> DsoDraftResponse:
    """Fixed structure (PRD 7.7): greeting, who I am, my situation, question, what I tried, thanks."""
    profile = demo_profile()
    content = get_content()
    office = content.policy.office
    task = content.tasks.get(req.current_task_id or "")
    step = f" I am working on: {task.title}." if task else ""
    lines = [
        f"Dear {office.office_display_name},",
        "",
        "My name is [YOUR FULL NAME] (Student ID: [YOUR STUDENT ID]). I am applying for post-completion OPT.",
        f"My Program End Date is {profile.program_end_date:%B %d, %Y}, and my current stage is "
        f"{profile.stage.value.replace('_', ' ').lower()}.{step}",
        "",
        f"My question: {req.user_question}",
        "",
        "I have read the information on the UW ISS website.",
    ]
    if req.tone != DraftTone.SHORTER:
        lines += ["", "Thank you for your help.", "", "Best regards,", "[YOUR FULL NAME]"]
    return DsoDraftResponse(
        recipient=office.contact_email or office.advising_form_url,
        subject=f"Question about my OPT application: {req.question_type.value.replace('_', ' ').title()}",
        body="\n".join(lines),
        placeholders=[p.strip("[]") for p in content.templates.dso_draft.placeholders],
    )
