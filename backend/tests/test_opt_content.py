"""OPT content YAML (Data Spec section 2): loads and validates at startup."""

import shutil
from pathlib import Path

import pytest
import yaml

from app.opt.content import CONTENT_DIR, get_content, load_content


@pytest.fixture
def content_copy(tmp_path) -> Path:
    root = tmp_path / "catalog"
    shutil.copytree(CONTENT_DIR, root, ignore=shutil.ignore_patterns("legacy"))
    return root


def edit(path: Path, change) -> None:
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True))


def test_repo_content_loads():
    content = get_content()
    assert [s.id for s in content.schools][0] == "uw"
    assert content.policy.office.office_display_name == "UW ISS"
    assert list(content.tasks) == ["T01", "T02", "T03", "T04", "T05", "T06"]
    assert content.federal.processing.t_uscis_standard_days == 90
    assert "task_T02" in content.chips
    assert content.templates.refusal.en


def test_valid_copy_loads(content_copy):
    assert load_content(content_copy).policy.id == "uw-opt"


def test_unknown_source_id_rejected(content_copy):
    edit(content_copy / "tasks" / "T05.yaml", lambda d: d.update(source_ids=["no-such-source"]))
    with pytest.raises(ValueError, match="no-such-source"):
        load_content(content_copy)


def test_unknown_prerequisite_rejected(content_copy):
    edit(content_copy / "tasks" / "T05.yaml", lambda d: d.update(prerequisites=["T99"]))
    with pytest.raises(ValueError, match="T99"):
        load_content(content_copy)


def test_unknown_timeline_node_rejected(content_copy):
    edit(content_copy / "tasks" / "T05.yaml", lambda d: d.update(timeline_node="N9"))
    with pytest.raises(ValueError):
        load_content(content_copy)


def test_unknown_complete_requires_field_rejected(content_copy):
    edit(content_copy / "tasks" / "T03.yaml", lambda d: d.update(complete_requires=["passport_number"]))
    with pytest.raises(ValueError):
        load_content(content_copy)


def test_reviewed_active_requires_reviewer(content_copy):
    edit(content_copy / "policy" / "uw.yaml", lambda d: d.update(status="REVIEWED_ACTIVE"))
    with pytest.raises(ValueError, match="reviewer"):
        load_content(content_copy)


def test_form_channel_requires_form_url(content_copy):
    edit(content_copy / "policy" / "uw.yaml", lambda d: d["office"].update(preferred_channel="FORM"))
    with pytest.raises(ValueError, match="advising_form_url"):
        load_content(content_copy)


def test_field_hints_must_cover_four_dates(content_copy):
    edit(content_copy / "policy" / "uw.yaml", lambda d: d["field_hints"].pop("dso_rec_date"))
    with pytest.raises(ValueError, match="dso_rec_date"):
        load_content(content_copy)


def test_school_window_source_must_exist(content_copy):
    edit(content_copy / "policy" / "uw.yaml", lambda d: d["timeline"]["school_windows"][0].update(source_id="nope"))
    with pytest.raises(ValueError, match="nope"):
        load_content(content_copy)


def test_school_window_open_date():
    from datetime import date

    assert get_content().policy.school_window_open(date(2027, 6, 11)) == date(2027, 3, 13)
