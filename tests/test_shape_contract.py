from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from portable_brain.cli import main

RunCli = Callable[..., int]


@pytest.fixture
def run_cli() -> RunCli:
    def run(*arguments: str) -> int:
        return main(list(arguments))

    return run


def manifest_for(brain: Path) -> dict[str, object]:
    value = yaml.safe_load(
        (brain / ".portable-brain" / "profile.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_add_type_creates_manifest_entry_folder_and_template_and_new_works(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    assert (
        run_cli(
            "add-type",
            str(brain),
            "Policy",
            "--group",
            "wiki",
            "--folder",
            "policies",
            "--sections",
            "Summary",
            "Current term",
            "Coverage",
            "History",
            "Follow-ups",
            "References",
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "added type Policy (wiki/policies/)" in out
    types = manifest_for(brain)["types"]
    assert isinstance(types, dict)
    assert types["Policy"] == {
        "group": "wiki",
        "folder": "policies",
        "workflow": False,
        "sections": [
            "Summary",
            "Current term",
            "Coverage",
            "History",
            "Follow-ups",
            "References",
        ],
    }
    assert list(types)[-1] == "Policy"
    assert (brain / "wiki" / "policies").is_dir()
    template = (brain / "templates" / "policy.md").read_text(encoding="utf-8")
    assert "type: Template" in template and "## Current term" in template

    assert run_cli("new", str(brain), "Policy", "home", "--title", "Home") == 0
    note = brain / "wiki" / "policies" / "home.md"
    assert note.is_file() and "## Coverage" in note.read_text(encoding="utf-8")
    assert run_cli("validate", str(brain)) == 0
    assert run_cli("index", str(brain)) == 0
    assert "## Policies" in (brain / "wiki" / "index.md").read_text(encoding="utf-8")

    assert run_cli("add-type", str(brain), "Vehicle", "--group", "wiki") == 0
    vehicle = manifest_for(brain)["types"]["Vehicle"]  # type: ignore[index]
    assert vehicle["folder"] == "vehicle" and vehicle["sections"] == [
        "Summary",
        "Notes",
        "References",
    ]


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (("Concept", "--group", "wiki"), "already exists"),
        (("Template", "--group", "wiki"), "reserved"),
        (("Meeting", "--group", "journal"), "invalid choice: 'journal'"),
        (("Meeting", "--group", "inbox"), "invalid choice: 'inbox'"),
        (("Engagement", "--group", "work"), "enable-work"),
        (
            ("Bad", "--group", "wiki", "--folder", "../escape"),
            "safe non-empty relative folder",
        ),
    ],
)
def test_add_type_refusals(
    tmp_path: Path,
    run_cli: RunCli,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
    message: str,
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    before = (brain / ".portable-brain" / "profile.yaml").read_bytes()
    assert run_cli("add-type", str(brain), *arguments) == 2
    assert message in capsys.readouterr().err
    assert (brain / ".portable-brain" / "profile.yaml").read_bytes() == before


def test_remove_type_refuses_journal_and_used_types_then_removes_unused(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    assert run_cli("remove-type", str(brain), "Journal") == 2
    assert (
        run_cli(
            "add-type", str(brain), "Policy", "--group", "wiki", "--folder", "policies"
        )
        == 0
    )
    assert run_cli("new", str(brain), "Policy", "home", "--title", "Home") == 0
    assert run_cli("remove-type", str(brain), "Policy") == 2
    assert "used by 1 document" in capsys.readouterr().err
    (brain / "wiki" / "policies" / "home.md").unlink()
    assert run_cli("remove-type", str(brain), "Policy") == 0
    assert "Policy" not in manifest_for(brain)["types"]  # type: ignore[operator]
    assert not (brain / "templates" / "policy.md").exists()
    assert not (brain / "wiki" / "policies").exists()
    assert run_cli("validate", str(brain)) == 0


def test_add_domain_merges_overlay_and_skips_work_types_until_work_is_enabled(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--adapter", "obsidian") == 0
    assert run_cli("add-domain", str(brain), "travel") == 0
    assert "Itinerary" in capsys.readouterr().out
    manifest = manifest_for(brain)
    assert manifest["domains"] == ["travel"]
    types = manifest["types"]
    assert isinstance(types, dict) and "Itinerary" in types and "Trip" not in types
    assert (brain / "wiki" / "travel" / "itineraries").is_dir()
    assert (brain / "templates" / "itinerary.md").is_file()
    assert run_cli("add-domain", str(brain), "travel") == 2
    assert "already enabled" in capsys.readouterr().err

    assert run_cli("enable-work", str(brain)) == 0
    out = capsys.readouterr().out
    assert "Decision" in out and "Project" in out and "Trip" in out
    manifest = manifest_for(brain)
    assert manifest["modules"] == ["work"]
    assert list(manifest["groups"]) == ["inbox", "sources", "wiki", "journal", "work"]  # type: ignore[arg-type]
    assert (brain / "work" / "travel" / "trips").is_dir()
    assert (brain / "work" / "index.md").is_file()
    assert "[Work](work/index.md)" in (brain / "index.md").read_text(encoding="utf-8")
    assert (brain / "views" / "workflow.base").is_file()
    assert "Workflow" in (brain / "HOME.md").read_text(encoding="utf-8")
    assert run_cli("new", str(brain), "Trip", "lisbon", "--title", "Lisbon") == 0
    assert run_cli("validate", str(brain)) == 0
    assert run_cli("index", str(brain)) == 0
    assert "lisbon.md" in (brain / "work" / "index.md").read_text(encoding="utf-8")
    assert run_cli("enable-work", str(brain)) == 2
    assert (
        run_cli(
            "add-type",
            str(brain),
            "Engagement",
            "--group",
            "work",
            "--folder",
            "engagements",
        )
        == 0
    )
    engagement = manifest_for(brain)["types"]["Engagement"]  # type: ignore[index]
    assert engagement["workflow"] is True
    assert run_cli("new", str(brain), "Engagement", "acme", "--title", "Acme") == 0
    assert "pb_work_state: active" in (
        brain / "work" / "engagements" / "acme.md"
    ).read_text(encoding="utf-8")
    assert run_cli("validate", str(brain)) == 0


def test_add_type_refuses_reusing_a_strict_group_subfolder(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    assert (
        run_cli(
            "add-type",
            str(brain),
            "Transcript",
            "--group",
            "sources",
            "--folder",
            "transcripts",
        )
        == 0
    )
    assert (
        run_cli(
            "add-type",
            str(brain),
            "Recording",
            "--group",
            "sources",
            "--folder",
            "transcripts",
        )
        == 2
    )
    assert "reuses folder" in capsys.readouterr().err
    assert (
        run_cli("new", str(brain), "Transcript", "standup", "--title", "Standup") == 0
    )
    assert run_cli("validate", str(brain)) == 0
