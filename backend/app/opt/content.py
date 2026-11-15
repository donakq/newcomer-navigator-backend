"""OPT content data (Data Spec section 2): YAML under backend/catalog/, validated at startup.

Content is curated by the team and signed off by the policy reviewer. A broken file fails the deploy.
Until sign-off the Policy Pack status is REVIEW_REQUIRED; that loads (mock phase) but adds a warning.
"""

from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, PositiveInt, ValidationError

from app.opt.timeline import DueType
from app.schemas.opt import Office, PolicyStatus, PreferredChannel, SupportStatus

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "catalog"

NODE_IDS = {"N1", "N1b", "N2", "N3", "N4", "N5", "N6", "N7"}
STAGE_DATE_FIELDS = {"i20_request_date", "dso_rec_date", "i20_issue_date", "uscis_receipt_date", "requested_start_date"}
FIELD_HINT_KEYS = {"program_end_date", "dso_rec_date", "uscis_receipt_date", "i20_request_date"}


class SchoolEntry(BaseModel):
    id: str
    school_name: str
    support_status: SupportStatus


class SchoolWindow(BaseModel):
    rule: Literal["days_before_program_end"]
    days: int
    source_id: str


class PolicyTimeline(BaseModel):
    t_school_days: PositiveInt
    school_windows: list[SchoolWindow] = []
    source_ids: list[str]


class PolicyPack(BaseModel):
    id: str
    school_id: str
    version: int
    status: PolicyStatus
    reviewed_at: date | None
    reviewer: str | None
    timeline: PolicyTimeline
    office: Office
    module_links: dict[str, str | None]
    field_hints: dict[str, str]

    def school_window_open(self, program_end: date) -> date | None:
        """W_s for a student: the latest opening date among the school's window rules."""
        opens = [program_end - timedelta(days=w.days) for w in self.timeline.school_windows]
        return max(opens) if opens else None


class FederalRules(BaseModel):
    earliest_filing_days_before_end: int
    latest_filing_days_after_end: int
    filing_days_after_recommendation: int
    max_unemployment_days: int
    weekend_holiday_rule: str
    source_ids: list[str]


class FederalProcessing(BaseModel):
    t_uscis_standard_days: PositiveInt
    t_uscis_premium_days: PositiveInt
    source_ids: list[str]


class Federal(BaseModel):
    reviewed_at: date | None
    reviewer: str | None
    rules: FederalRules
    processing: FederalProcessing
    buffer_days: int


class SourceEntry(BaseModel):
    id: str
    title: str
    url: str | None
    publisher: Literal["UW_ISS", "USCIS", "DHS", "CBP"]
    scope: list[str]
    last_reviewed: date | None


class DocumentEntry(BaseModel):
    name: str
    where_to_get: str | None


class TaskTemplate(BaseModel):
    id: str
    policy_pack_id: str
    title: str
    order: int
    prerequisites: list[str]
    due_type: DueType
    timeline_node: str | None  # date shown on the Checklist
    deadline_node: str | None = None  # hard deadline, if different
    complete_requires: list[str]
    waiting_records: str | None
    steps: list[str]
    documents: list[DocumentEntry]
    source_ids: list[str]


class LangText(BaseModel):
    en: str | None
    zh: str | None


class DraftTemplate(BaseModel):
    question_types: list[str]
    structure: list[str]
    placeholders: list[str]


class Templates(BaseModel):
    refusal: LangText
    unverifiable: LangText
    unsupported_opt: LangText
    disclaimer: LangText
    dso_draft: DraftTemplate


class GlossaryEntry(BaseModel):
    term: str
    full_name: str | None
    definition_en: str | None
    definition_zh: str | None


class OptContent(BaseModel):
    schools: list[SchoolEntry]
    policy: PolicyPack
    federal: Federal
    sources: dict[str, SourceEntry]
    tasks: dict[str, TaskTemplate]  # in task order
    chips: dict[str, list[str]]
    templates: Templates
    glossary: list[GlossaryEntry]
    warnings: list[str]


def _read(path: Path, model):
    try:
        data = yaml.safe_load(path.read_text())
        if isinstance(data, list):
            return [model.model_validate(item) for item in data]
        return model.model_validate(data)
    except (ValidationError, yaml.YAMLError) as e:
        raise ValueError(f"{path.name}: {e}") from e


def _check_sources(ids: list[str], sources: dict, where: str) -> None:
    missing = [s for s in ids if s not in sources]
    if missing:
        raise ValueError(f"{where}: unknown source ids {missing}")


def load_content(root: Path) -> OptContent:
    schools = _read(root / "schools.yaml", SchoolEntry)
    policy = _read(root / "policy" / "uw.yaml", PolicyPack)
    federal = _read(root / "federal.yaml", Federal)
    source_list = _read(root / "sources.yaml", SourceEntry)
    task_list = sorted((_read(p, TaskTemplate) for p in sorted((root / "tasks").glob("T*.yaml"))), key=lambda t: t.order)
    chips = yaml.safe_load((root / "ai" / "chips.yaml").read_text())
    templates = _read(root / "ai" / "templates.yaml", Templates)
    glossary = _read(root / "ai" / "glossary.yaml", GlossaryEntry)

    sources = {s.id: s for s in source_list}
    if len(sources) != len(source_list):
        raise ValueError("sources.yaml: duplicate source id")

    # Policy Pack (Data Spec 2.2)
    if policy.school_id not in {s.id for s in schools}:
        raise ValueError(f"policy/uw.yaml: unknown school_id {policy.school_id!r}")
    if policy.status == PolicyStatus.REVIEWED_ACTIVE and not (policy.reviewed_at and policy.reviewer):
        raise ValueError("policy/uw.yaml: REVIEWED_ACTIVE requires reviewed_at and reviewer")
    office = policy.office
    if office.preferred_channel in (PreferredChannel.FORM, PreferredChannel.PORTAL) and not office.advising_form_url:
        raise ValueError("policy/uw.yaml: preferred_channel FORM/PORTAL requires advising_form_url")
    missing_hints = sorted(FIELD_HINT_KEYS - set(policy.field_hints))
    if missing_hints:
        raise ValueError(f"policy/uw.yaml: field_hints missing {missing_hints}")
    _check_sources(policy.timeline.source_ids, sources, "policy/uw.yaml timeline")
    _check_sources([w.source_id for w in policy.timeline.school_windows], sources, "policy/uw.yaml school_windows")
    _check_sources(federal.rules.source_ids + federal.processing.source_ids, sources, "federal.yaml")

    # Task templates (Data Spec 2.5)
    tasks = {t.id: t for t in task_list}
    if len(tasks) != len(task_list):
        raise ValueError("tasks: duplicate task id")
    for t in task_list:
        where = f"tasks/{t.id}.yaml"
        if t.policy_pack_id != policy.id:
            raise ValueError(f"{where}: policy_pack_id {t.policy_pack_id!r} != {policy.id!r}")
        unknown = [p for p in t.prerequisites if p not in tasks]
        if unknown:
            raise ValueError(f"{where}: unknown prerequisites {unknown}")
        for node in (t.timeline_node, t.deadline_node):
            if node is not None and node not in NODE_IDS:
                raise ValueError(f"{where}: unknown timeline node {node!r}")
        bad_fields = [f for f in t.complete_requires + [t.waiting_records] if f and f not in STAGE_DATE_FIELDS]
        if bad_fields:
            raise ValueError(f"{where}: unknown date fields {bad_fields}")
        _check_sources(t.source_ids, sources, where)

    warnings = []
    if policy.status != PolicyStatus.REVIEWED_ACTIVE:
        warnings.append(f"UW Policy Pack is {policy.status.value}: dates and contact details are not verified.")
    if federal.reviewer is None:
        warnings.append("Federal processing times are not reviewed.")

    return OptContent(
        schools=schools, policy=policy, federal=federal, sources=sources, tasks=tasks,
        chips=chips, templates=templates, glossary=glossary, warnings=warnings,
    )


@lru_cache
def get_content() -> OptContent:
    return load_content(CONTENT_DIR)
