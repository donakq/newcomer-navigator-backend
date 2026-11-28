"""AI Widget replies. Step 1 (done): redact, classify with the LLM, route in code.
Step 2 (next): answers from reviewed sources replace the placeholder in-scope answers.
"""

import re
import uuid

from app.ai import classifier
from app.ai.classifier import Classification
from app.ai.client import LLMUnavailable
from app.ai.redact import redact
from app.mock.opt_demo import source
from app.opt.content import get_content
from app.schemas.opt import (
    AssistantAction,
    AssistantRequest,
    AssistantResponse,
    DraftTone,
    DsoDraftRequest,
    DsoDraftResponse,
    FollowUp,
    Intent,
    Profile,
    Scope,
)

CJK = re.compile(r"[一-鿿]")
OUT_OF_SCOPE = ("h-1b", "h1b", "green card", "绿卡", "cpt", "visa renewal", "签证续签")
UNSUPPORTED_OPT = ("stem", "pre-completion")

MAIN_SOURCE_ID = "uw-post-completion-opt"
CONTACT_LABEL = "Contact My International Student Office"
CLARIFY_BELOW = 0.7  # PRD: below this confidence, ask instead of answering
CLARIFY = {"en": "I want to make sure I answer the right question. Did you mean one of these?",
           "zh": "我想确认一下你的问题，你是想问下面哪一个？"}
SLOT_QUESTIONS = {
    "program_end_date": {"en": "What is the Program End Date on your current I-20?",
                         "zh": "你当前 I-20 上的项目结束日期（Program End Date）是哪天？"},
    "dso_rec_date": {"en": "What is your DSO recommendation date? It is on page 1 of your OPT I-20.",
                     "zh": "你的 DSO 推荐日期是哪天？可以在 OPT I-20 第一页找到。"},
    "offer_start_date": {"en": "When does your job offer start?", "zh": "你的工作 offer 从哪天开始？"},
    "uscis_receipt_date": {"en": "What is the receipt date on your Form I-797C receipt notice?",
                           "zh": "你的 I-797C 收据通知上的收件日期是哪天？"},
}
NEXT_STEP = {
    "en": "Your next step is to request your OPT I-20 from {office}.",
    "zh": "你的下一步是向 {office} 申请 OPT I-20。",
}


def _language(text: str) -> str:
    return "zh" if CJK.search(text) else "en"


def _keyword_label(text: str) -> Classification:
    """Fallback when the LLM is unavailable: the original keyword rules."""
    lowered = text.lower()
    topic = next((k for k in OUT_OF_SCOPE if k in lowered), None)
    if topic:
        return Classification(intent=None, scope=Scope.OUT, risk="NONE", confidence=0.95, missing_slots=[],
                              topic=topic.upper() if topic.isascii() else topic)
    topic = next((k for k in UNSUPPORTED_OPT if k in lowered), None)
    if topic:
        return Classification(intent=None, scope=Scope.UNSUPPORTED_OPT, risk="NONE", confidence=0.9,
                              missing_slots=[], topic=topic.upper())
    return Classification(intent=Intent.NEXT_STEP, scope=Scope.IN, risk="NONE", confidence=0.9,
                          missing_slots=[], topic=None)


def _known_slots(profile: Profile | None) -> set[str]:
    if profile is None:
        return set()
    dates = profile.stage_dates
    known = {"program_end_date"}
    if dates.dso_rec_date:
        known.add("dso_rec_date")
    if dates.uscis_receipt_date:
        known.add("uscis_receipt_date")
    if profile.offer and profile.offer.offer_start_date:
        known.add("offer_start_date")
    return known


def _chips(req: AssistantRequest) -> list[str]:
    chips = get_content().chips
    key = f"task_{req.current_task_id}" if req.current_page == "task" and req.current_task_id else {
        "home": "home", "timeline": "timeline", "select_opt": "select_opt"}.get(req.current_page, "checklist_opt")
    return chips.get(key) or chips["checklist_opt"]


def reply(req: AssistantRequest, profile: Profile | None = None) -> AssistantResponse:
    """Redact, label with the LLM (keyword rules if it is unavailable), then route in code."""
    lang = _language(req.message)
    content = get_content()
    templates = content.templates
    office = content.policy.office.office_display_name
    conversation_id = req.conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
    contact = AssistantAction(kind="OPEN_CONTACT_PANEL", label=CONTACT_LABEL, target=None)

    message = redact(req.message)
    try:
        label = classifier.classify(message)
    except LLMUnavailable:
        label = _keyword_label(message)
    confidence = min(max(label.confidence, 0.0), 1.0)

    def say(template, **fmt) -> str:
        return (getattr(template, lang) or template.en).format(office_display_name=office, **fmt)

    def respond(answer: str, *, intent=label.intent, scope=label.scope, sources=(), follow_up=None, actions=()):
        return AssistantResponse(conversation_id=conversation_id, intent=intent, scope=scope, confidence=confidence,
                                 language=lang, answer=answer, sources=list(sources), follow_up=follow_up,
                                 actions=list(actions))

    topic = label.topic or ("这个话题" if lang == "zh" else "this topic")
    if label.scope == Scope.OUT:
        return respond(say(templates.refusal, topic=topic), intent=None, actions=[contact])
    if label.scope == Scope.UNSUPPORTED_OPT:
        return respond(say(templates.unsupported_opt, topic=topic), intent=None,
                       sources=[source(MAIN_SOURCE_ID)], actions=[contact])
    risk_template = {"CASE_JUDGMENT": templates.case_judgment, "EVASION": templates.no_evasion,
                     "NEEDS_SCHOOL": templates.unverifiable}.get(label.risk)
    if risk_template:
        return respond(say(risk_template), actions=[contact])
    if confidence < CLARIFY_BELOW:
        return respond(CLARIFY[lang], follow_up=FollowUp(kind="CLARIFY", question=CLARIFY[lang], chips=_chips(req)))
    missing = [slot for slot in label.missing_slots if slot not in _known_slots(profile)]
    if missing:
        question = SLOT_QUESTIONS[missing[0]][lang]
        return respond(question, follow_up=FollowUp(kind="ASK_SLOT", question=question, chips=[]))

    # In scope. Step 2 (answers from reviewed sources) replaces these placeholder answers.
    if label.intent in (None, Intent.NEXT_STEP):
        return respond(NEXT_STEP[lang].format(office=office), sources=[source(MAIN_SOURCE_ID)],
                       actions=[AssistantAction(kind="OPEN_TASK", label=content.tasks["T02"].title, target="T02")])
    return respond(say(templates.unverifiable), sources=[source(MAIN_SOURCE_ID)], actions=[contact])


def draft(req: DsoDraftRequest, profile: Profile) -> DsoDraftResponse:
    """Fixed structure (PRD 7.7): greeting, who I am, my situation, question, what I tried, thanks."""
    content = get_content()
    office = content.policy.office
    task = content.tasks.get(req.current_task_id or "")
    step = f" I am working on: {task.title}." if task else ""
    lines = [
        f"Dear {office.office_display_name},",
        "",
        "My name is [YOUR FULL NAME] (Student ID: [YOUR STUDENT ID]). I am applying for post-completion OPT.",
        f"My Program End Date is {profile.program_end_date:%B %d, %Y}, and my current stage is "
        f"{(profile.stage or 'PLANNING').replace('_', ' ').lower()}.{step}",
        "",
        f"My question: {req.user_question}",
        "",
        f"I have read the information on the {office.office_display_name} website.",
    ]
    if req.tone != DraftTone.SHORTER:
        lines += ["", "Thank you for your help.", "", "Best regards,", "[YOUR FULL NAME]"]
    return DsoDraftResponse(
        recipient=office.contact_email or office.advising_form_url,
        subject=f"Question about my OPT application: {req.question_type.value.replace('_', ' ').title()}",
        body="\n".join(lines),
        placeholders=[p.strip("[]") for p in content.templates.dso_draft.placeholders],
    )
