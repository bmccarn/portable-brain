from __future__ import annotations

import re
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


def type_in_group(brain: Path, group: str) -> tuple[str, dict[str, object]]:
    types = manifest_for(brain)["types"]
    assert isinstance(types, dict)
    for name, definition in types.items():
        if (
            isinstance(name, str)
            and isinstance(definition, dict)
            and definition["group"] == group
        ):
            return name, definition
    raise AssertionError(f"No type configured for {group}")


def note_path(brain: Path, definition: dict[str, object], slug: str) -> Path:
    group = definition["group"]
    folder = definition["folder"]
    assert isinstance(group, str) and isinstance(folder, str)
    directory = brain / group if folder == "." else brain / group / folder
    return directory / f"{slug}.md"


def add_note(brain: Path, run_cli: RunCli, group: str, slug: str, title: str) -> Path:
    type_name, definition = type_in_group(brain, group)
    assert run_cli("new", str(brain), type_name, slug, "--title", title) == 0
    return note_path(brain, definition, slug)


def test_index_writes_a_clean_layer_root_and_deterministic_group_catalogs(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software") == 0
    add_note(brain, run_cli, "wiki", "second-note", "Second note")
    add_note(brain, run_cli, "wiki", "first-note", "First note")
    assert (
        run_cli("new", str(brain), "Journal", "2026-08-22", "--title", "2026-08-22")
        == 0
    )

    assert run_cli("index", str(brain)) == 0
    root_once = (brain / "index.md").read_text(encoding="utf-8")
    wiki_once = (brain / "wiki" / "index.md").read_text(encoding="utf-8")
    journal_once = (brain / "journal" / "index.md").read_text(encoding="utf-8")
    assert run_cli("index", str(brain)) == 0

    assert (brain / "index.md").read_text(encoding="utf-8") == root_once
    assert (brain / "wiki" / "index.md").read_text(encoding="utf-8") == wiki_once
    assert (brain / "journal" / "index.md").read_text(encoding="utf-8") == journal_once
    for group in ("inbox", "sources", "wiki", "journal"):
        assert f"{group}/" in root_once
    assert "work/" not in root_once
    assert "First note" not in root_once
    assert "Second note" not in root_once
    assert "[First note](first-note.md)" in wiki_once
    assert "[Second note](second-note.md)" in wiki_once
    assert wiki_once.index("First note") < wiki_once.index("Second note")
    assert "2026-08-22" not in root_once
    assert "2026-08-22" not in wiki_once
    assert "[2026-08-22](2026-08-22.md)" in journal_once
    for index in (root_once, wiki_once, journal_once):
        assert "[[" not in index
    for group, document in (
        ("wiki", brain / "wiki" / "index.md"),
        ("journal", brain / "journal" / "index.md"),
    ):
        links = re.findall(
            r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")
        )
        assert all((document.parent / link).exists() for link in links)


def test_group_index_entries_carry_descriptions_and_omit_them_when_absent(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software") == 0
    described = add_note(brain, run_cli, "wiki", "described-note", "Described note")
    add_note(brain, run_cli, "wiki", "bare-note", "Bare note")

    original = described.read_text(encoding="utf-8")
    described.write_text(
        original.replace("description: ''", "description: Where seams live", 1),
        encoding="utf-8",
    )
    assert "description: Where seams live" in described.read_text(encoding="utf-8")

    assert run_cli("index", str(brain)) == 0
    wiki = (brain / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "- [Described note](described-note.md) — Where seams live" in wiki
    assert "- [Bare note](bare-note.md)\n" in wiki


def test_index_check_reports_stale_then_fresh_group_indexes(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software") == 0
    assert run_cli("index", str(brain), "--check") == 0

    add_note(brain, run_cli, "wiki", "newly-added", "Newly added")
    assert run_cli("index", str(brain), "--check") == 1
    assert "stale" in capsys.readouterr().err.lower()

    assert run_cli("index", str(brain)) == 0
    assert run_cli("index", str(brain), "--check") == 0


def test_group_indexes_preserve_nested_domain_structure(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "travel") == 0
    assert run_cli("new", str(brain), "Itinerary", "day-one", "--title", "Day one") == 0

    assert run_cli("index", str(brain)) == 0
    wiki = (brain / "wiki" / "index.md").read_text(encoding="utf-8")
    assert "## Travel" in wiki
    assert "### Itineraries" in wiki
    assert "[Day one](travel/itineraries/day-one.md)" in wiki
    assert (
        wiki.index("## Travel") < wiki.index("### Itineraries") < wiki.index("Day one")
    )


def test_index_fails_closed_without_rewriting_any_catalog_on_invalid_brain(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    assert run_cli("index", str(brain)) == 0
    root_before = (brain / "index.md").read_bytes()
    wiki_before = (brain / "wiki" / "index.md").read_bytes()

    invalid = brain / "wiki" / "Not_Kebab.md"
    invalid.write_text(
        "---\ntype: Architecture\ntitle: Invalid\n---\n# Invalid\n", encoding="utf-8"
    )
    assert run_cli("index", str(brain)) == 1
    assert invalid.name in capsys.readouterr().err
    assert (brain / "index.md").read_bytes() == root_before
    assert (brain / "wiki" / "index.md").read_bytes() == wiki_before


def test_deleting_a_cataloged_note_never_blocks_reindexing(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    note = add_note(brain, run_cli, "wiki", "gone-soon", "Gone soon")
    assert run_cli("index", str(brain)) == 0
    assert "gone-soon.md" in (brain / "wiki" / "index.md").read_text(encoding="utf-8")

    note.unlink()
    assert run_cli("validate", str(brain)) == 0
    err = capsys.readouterr().err
    assert "wiki/index.md: warning:" in err and "stale" in err
    assert run_cli("index", str(brain)) == 0
    assert "gone-soon.md" not in (brain / "wiki" / "index.md").read_text(
        encoding="utf-8"
    )
    assert run_cli("validate", str(brain)) == 0
    assert capsys.readouterr().err == ""
