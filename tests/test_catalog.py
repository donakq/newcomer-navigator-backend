from pathlib import Path

import pytest

from app.catalog_loader import get_catalog, load_catalog

BASE_TASK = """
id: {id}
version: 1
title: T
when: {when}
reason: R
depends_on: {depends_on}
personalize_on: {personalize_on}
steps:
{steps}
"""
STEP = "  - id: {sid}\n    title: S\n"


def write_catalog(root: Path, tasks: list[dict], events: str = "[]") -> Path:
    (root / "tasks").mkdir(parents=True)
    for i, t in enumerate(tasks):
        text = BASE_TASK.format(
            id=t.get("id", f"t{i}"),
            when=t.get("when", "{field: in_us, eq: true}"),
            depends_on=t.get("depends_on", "[]"),
            personalize_on=t.get("personalize_on", "[]"),
            steps="".join(STEP.format(sid=s) for s in t.get("steps", ["s1"])),
        )
        (root / "tasks" / f"{i}.yaml").write_text(text)
    (root / "events.yaml").write_text(events)
    return root


def test_loads_repo_catalog():
    catalog = get_catalog()
    assert set(catalog.tasks) == {"ssn", "bank_account", "us_phone"}
    assert "GOT_JOB_OFFER" in catalog.events


def test_valid_fixture_loads(tmp_path):
    catalog = load_catalog(write_catalog(tmp_path, [{"id": "a"}]))
    assert list(catalog.tasks) == ["a"]


def test_duplicate_task_id_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"id": "a"}, {"id": "a"}]))


def test_duplicate_step_id_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"id": "a", "steps": ["s1", "s1"]}]))


def test_unknown_field_in_when_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"when": "{field: has_ssnn, eq: false}"}]))


def test_unknown_field_in_personalize_on_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"personalize_on": "[shoe_size]"}]))


def test_unknown_depends_on_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"id": "a", "depends_on": "[missing]"}]))


def test_bad_condition_operator_rejected(tmp_path):
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"when": "{field: has_ssn, gt: 1}"}]))


def test_event_extract_field_must_be_profile_field(tmp_path):
    events = "- id: E\n  description: d\n  extract_fields: [shoe_size]\n"
    with pytest.raises(ValueError):
        load_catalog(write_catalog(tmp_path, [{"id": "a"}], events))
