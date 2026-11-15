"""Mock AI Widget replies: just enough logic to return every contract shape.

The real version (intent classifier, retrieval, refusal rules) replaces this in W3.
"""

import re
import uuid

from app.mock.opt_demo import SOURCES, TASKS, UW_OFFICE, demo_profile
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

REFUSAL = {
    "en": "I can only help with OPT applications in this app. For questions about {topic}, "
          "please contact {office} or visit its website.",
    "zh": "这个应用只能回答 OPT 申请相关的问题。关于{topic}的问题，请联系 {office} 或访问其官网。",
}
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
    office = UW_OFFICE.office_display_name
    conversation_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
    contact = AssistantAction(kind="OPEN_CONTACT_PANEL", label="Contact My International Student Office", target=None)

    topic = next((k for k in OUT_OF_SCOPE if k in text), None)
    if topic:
        return AssistantResponse(
            conversation_id=conversation_id, intent=None, scope=Scope.OUT, confidence=0.95, language=lang,
            answer=REFUSAL[lang].format(topic=topic.upper() if topic.isascii() else topic, office=office),
            sources=[], follow_up=None, actions=[contact],
        )
    topic = next((k for k in UNSUPPORTED_OPT if k in text), None)
    if topic:
        return AssistantResponse(
            conversation_id=conversation_id, intent=None, scope=Scope.UNSUPPORTED_OPT, confidence=0.9,
            language=lang, answer=UNSUPPORTED[lang].format(topic=topic.upper(), office=office),
            sources=[SOURCES["uw_opt"]], follow_up=None, actions=[contact],
        )
    return AssistantResponse(
        conversation_id=conversation_id, intent=Intent.NEXT_STEP, scope=Scope.IN, confidence=0.9, language=lang,
        answer=NEXT_STEP[lang].format(office=office),
        sources=[SOURCES["uw_opt"]], follow_up=None,
        actions=[AssistantAction(kind="OPEN_TASK", label=TASKS["T02"]["title"], target="T02")],
    )


def draft(req: DsoDraftRequest) -> DsoDraftResponse:
    """Fixed structure (PRD 7.7): greeting, who I am, my situation, question, what I tried, thanks."""
    profile = demo_profile()
    task = TASKS.get(req.current_task_id or "")
    step = f" I am working on: {task['title']}." if task else ""
    lines = [
        f"Dear {UW_OFFICE.office_display_name},",
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
        recipient=UW_OFFICE.contact_email or UW_OFFICE.advising_form_url,
        subject=f"Question about my OPT application: {req.question_type.value.replace('_', ' ').title()}",
        body="\n".join(lines),
        placeholders=["YOUR FULL NAME", "YOUR STUDENT ID"],
    )
