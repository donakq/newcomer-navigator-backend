"""Assistant step 1: redact, classify with the LLM, then route in code (design: OPT MVP AI Assistant Design).

The LLM is faked here; no test calls the real API.
"""

import pytest

from app.ai import classifier
from app.ai.classifier import Classification
from app.ai.client import LLMUnavailable
from app.ai.redact import redact

URL = "/api/assistant/messages"


def _label(**kw) -> Classification:
    base = dict(intent="NEXT_STEP", scope="IN", risk="NONE", topic=None, confidence=0.9, missing_slots=[])
    return Classification(**{**base, **kw})


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the LLM call: set `.label` (or `.error`) and read `.seen` for what the model received."""

    class Fake:
        label = _label()
        error: Exception | None = None
        seen: list[str] = []

    def fake_classify(message: str) -> Classification:
        Fake.seen.append(message)
        if Fake.error:
            raise Fake.error
        return Fake.label

    Fake.seen = []
    monkeypatch.setattr(classifier, "classify", fake_classify)
    return Fake


def _ask(client, message, page="checklist"):
    return client.post(URL, json={"message": message, "current_page": page}).json()


# --- Pre-check: personal numbers never reach the LLM ---


def test_redact_removes_personal_numbers():
    text = redact("SSN 123-45-6789, A-number A123456789, SEVIS N0012345678, I-94 12345678901")
    for secret in ("123-45-6789", "A123456789", "N0012345678", "12345678901"):
        assert secret not in text
    assert "[REDACTED]" in text


def test_llm_sees_redacted_message(client, fake_llm):
    _ask(client, "My SEVIS ID is N0012345678, what next?")
    assert fake_llm.seen and "N0012345678" not in fake_llm.seen[0]


# --- Routing is decided in code ---


def test_out_of_scope_uses_refusal_template_with_topic(client, fake_llm):
    fake_llm.label = _label(intent=None, scope="OUT", topic="H-1B")
    data = _ask(client, "How does the H-1B lottery work?")
    assert data["scope"] == "OUT"
    assert "only help with OPT" in data["answer"] and "H-1B" in data["answer"]
    assert [a["kind"] for a in data["actions"]] == ["OPEN_CONTACT_PANEL"]


def test_unsupported_opt_type_uses_template(client, fake_llm):
    fake_llm.label = _label(intent=None, scope="UNSUPPORTED_OPT", topic="STEM OPT")
    data = _ask(client, "Can I apply for the STEM extension?")
    assert data["scope"] == "UNSUPPORTED_OPT"
    assert "initial Post-Completion OPT only" in data["answer"]


def test_case_judgment_question_is_not_answered(client, fake_llm):
    fake_llm.label = _label(intent="RISK_ESCALATION", risk="CASE_JUDGMENT")
    data = _ask(client, "Will USCIS approve my OPT?")
    assert "can't predict whether USCIS" in data["answer"]
    assert data["intent"] == "RISK_ESCALATION"
    assert [a["kind"] for a in data["actions"]] == ["OPEN_CONTACT_PANEL"]


def test_evasion_request_is_refused(client, fake_llm):
    fake_llm.label = _label(intent="RISK_ESCALATION", risk="EVASION")
    assert "can't help you hide" in _ask(client, "Can I leave my old job off the form?")["answer"]


def test_needs_school_uses_unverifiable_template(client, fake_llm):
    fake_llm.label = _label(intent="OPT_RULES", risk="NEEDS_SCHOOL")
    assert "can't verify this information" in _ask(client, "Can I travel while my OPT is pending?")["answer"]


def test_low_confidence_asks_to_clarify_with_chips(client, fake_llm):
    fake_llm.label = _label(confidence=0.4)
    data = _ask(client, "the thing with the date", page="timeline")
    assert data["follow_up"]["kind"] == "CLARIFY"
    assert data["follow_up"]["chips"]


def test_missing_slot_asks_one_question(client, fake_llm):
    fake_llm.label = _label(intent="DEADLINE", missing_slots=["dso_rec_date", "offer_start_date"])
    data = _ask(client, "When is my deadline?")
    assert data["follow_up"]["kind"] == "ASK_SLOT"
    assert "DSO recommendation date" in data["follow_up"]["question"]


def test_in_scope_keeps_the_classified_intent(client, fake_llm):
    fake_llm.label = _label(intent="DOCUMENTS")
    data = _ask(client, "What documents do I need?")
    assert data["scope"] == "IN"
    assert data["intent"] == "DOCUMENTS"


def test_follows_the_students_language(client, fake_llm):
    fake_llm.label = _label(intent=None, scope="OUT", topic="H-1B")
    data = _ask(client, "H-1B 抽签怎么算？")
    assert data["language"] == "zh"
    assert "本应用目前只提供 OPT" in data["answer"]


# --- Fallback: the chat keeps working without the LLM ---


def test_llm_unavailable_falls_back_to_keyword_rules(client, fake_llm):
    fake_llm.error = LLMUnavailable("down")
    data = _ask(client, "How does the H-1B lottery work?")
    assert data["scope"] == "OUT"


def test_confidence_outside_0_1_is_clamped(client, fake_llm):
    fake_llm.label = _label(confidence=7.0)
    assert _ask(client, "What should I do next?")["confidence"] == 1.0


def test_does_not_ask_for_a_date_already_in_the_profile(client, auth, fake_llm):
    # The demo profile already has an offer start date (2027-07-12) but no DSO recommendation date.
    fake_llm.label = _label(intent="START_DATE", missing_slots=["offer_start_date"])
    data = client.post(URL, json={"message": "When should I start?", "current_page": "timeline"}, headers=auth).json()
    assert data["follow_up"] is None
    fake_llm.label = _label(intent="DEADLINE", missing_slots=["offer_start_date", "dso_rec_date"])
    data = client.post(URL, json={"message": "When is my deadline?", "current_page": "timeline"}, headers=auth).json()
    assert "DSO recommendation date" in data["follow_up"]["question"]
