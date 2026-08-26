from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
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


def split_frontmatter(path: Path) -> tuple[dict[str, object], str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, serialized, body = text.split("---\n", 2)
    value = yaml.safe_load(serialized)
    assert isinstance(value, dict)
    return value, body


def write_note(path: Path, frontmatter: dict[str, object], body: str) -> None:
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )


def types_in_group(
    manifest: dict[str, object], group: str
) -> list[tuple[str, dict[str, object]]]:
    types = manifest["types"]
    assert isinstance(types, dict)
    return [
        (name, definition)
        for name, definition in types.items()
        if isinstance(name, str)
        and isinstance(definition, dict)
        and definition["group"] == group
    ]


def note_path(brain: Path, definition: dict[str, object], slug: str) -> Path:
    group = definition["group"]
    folder = definition["folder"]
    assert isinstance(group, str) and isinstance(folder, str)
    directory = brain / group if folder == "." else brain / group / folder
    return directory / f"{slug}.md"


def create_note(
    brain: Path, run_cli: RunCli, group: str, slug: str, title: str
) -> tuple[Path, dict[str, object]]:
    type_name, definition = types_in_group(manifest_for(brain), group)[0]
    assert run_cli("new", str(brain), type_name, slug, "--title", title) == 0
    return note_path(brain, definition, slug), definition


def expect_invalid(
    brain: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str], path: Path
) -> str:
    assert run_cli("validate", str(brain)) == 1
    output = capsys.readouterr().err
    assert path.name in output
    return output


def test_wiki_accepts_unconfigured_conceptual_types_but_not_reserved_types(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software") == 0
    conceptual = brain / "wiki" / "architecture.md"
    write_note(
        conceptual,
        {"type": "Architecture", "title": "Architecture"},
        "# Architecture\n",
    )

    assert run_cli("validate", str(brain)) == 0

    reserved = brain / "wiki" / "not-a-source.md"
    write_note(
        reserved, {"type": "Source", "title": "Not a source"}, "# Not a source\n"
    )
    expect_invalid(brain, run_cli, capsys, reserved)


def test_sources_and_work_are_strict_and_pb_fields_are_work_only(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software", "--work") == 0
    source, _ = create_note(brain, run_cli, "sources", "design-doc", "Design document")
    wiki, _ = create_note(brain, run_cli, "wiki", "architecture", "Architecture")
    work, _ = create_note(brain, run_cli, "work", "release", "Release")

    source_data, source_body = split_frontmatter(source)
    source_data["pb_work_state"] = "active"
    write_note(source, source_data, source_body)
    expect_invalid(brain, run_cli, capsys, source)
    source_data.pop("pb_work_state")
    write_note(source, source_data, source_body)

    wiki_data, wiki_body = split_frontmatter(wiki)
    wiki_data["pb_owner"] = "human:tester"
    write_note(wiki, wiki_data, wiki_body)
    expect_invalid(brain, run_cli, capsys, wiki)
    wiki_data.pop("pb_owner")
    write_note(wiki, wiki_data, wiki_body)

    unconfigured = brain / "work" / "not-work.md"
    write_note(
        unconfigured, {"type": "Architecture", "title": "Not work"}, "# Not work\n"
    )
    expect_invalid(brain, run_cli, capsys, unconfigured)
    unconfigured.unlink()

    work_data, work_body = split_frontmatter(work)
    work_data["pb_work_state"] = "not-a-machine-state"
    write_note(work, work_data, work_body)
    expect_invalid(brain, run_cli, capsys, work)


def test_journal_requires_its_date_title_shape_and_time_checkblocks(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    assert (
        run_cli("new", str(brain), "Journal", "2026-08-22", "--title", "2026-08-22")
        == 0
    )
    journal = brain / "journal" / "2026-08-22.md"
    frontmatter, body = split_frontmatter(journal)
    assert frontmatter["type"] == "Journal"
    assert frontmatter["title"] == "2026-08-22"
    assert body.startswith("# 2026-08-22\n")
    assert re.search(r"^## \d\d:\d\d — Topic$", body, re.MULTILINE) is not None
    assert "actor: human:" in body
    assert run_cli("validate", str(brain)) == 0
    original = journal.read_bytes()
    assert (
        run_cli("new", str(brain), "Journal", "2026-08-22", "--title", "2026-08-22")
        == 2
    )
    assert journal.read_bytes() == original

    frontmatter["title"] = "Wrong day"
    write_note(journal, frontmatter, body)
    expect_invalid(brain, run_cli, capsys, journal)
    frontmatter["title"] = "2026-08-22"
    valid_session = (
        "# 2026-08-22\n\n## 09:00 — Design\n\nactor: human:tester\n\nNarrative.\n"
    )
    write_note(journal, frontmatter, valid_session + "\n- [ ] A task\n")
    expect_invalid(brain, run_cli, capsys, journal)


def test_journal_source_footnotes_must_join_declared_source_ids(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    create_note(brain, run_cli, "sources", "design-doc", "Design document")
    assert (
        run_cli("new", str(brain), "Journal", "2026-08-22", "--title", "2026-08-22")
        == 0
    )
    journal = brain / "journal" / "2026-08-22.md"
    frontmatter, _ = split_frontmatter(journal)
    frontmatter["sources"] = [{"id": "design-doc"}]
    valid_body = (
        "# 2026-08-22\n\n## 09:00 — Design\n\nactor: human:tester\n\nNarrative.\n\n"
        "[^design-doc]\n\n[^design-doc]: [Design](../sources/design-doc.md)\n"
    )
    write_note(journal, frontmatter, valid_body)
    assert run_cli("validate", str(brain)) == 0

    write_note(
        journal,
        frontmatter,
        "# 2026-08-22\n\n## 09:00 — Design\n\nactor: human:tester\n\nNarrative.\n\n[^design-doc]\n",
    )
    expect_invalid(brain, run_cli, capsys, journal)

    duplicate_body = (
        "# 2026-08-22\n\n## 09:00 — Design\n\nactor: human:tester\n\nNarrative.\n\n"
        "[^design-doc]\n\n[^design-doc]: [Design](../sources/design-doc.md)\n\n"
        "[^design-doc]: [Duplicate](../sources/design-doc.md)\n"
    )
    write_note(journal, frontmatter, duplicate_body)
    expect_invalid(brain, run_cli, capsys, journal)


def test_portable_rejects_unreachable_internal_source_resources(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    source, _ = create_note(brain, run_cli, "sources", "design-doc", "Design document")
    frontmatter, body = split_frontmatter(source)
    frontmatter["sources"] = [{"resource": "/missing.rtf"}]
    write_note(source, frontmatter, body)

    error = expect_invalid(brain, run_cli, capsys, source)
    assert "missing.rtf" in error


def test_malformed_sources_are_reported_without_crashing_validation(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    source, _ = create_note(brain, run_cli, "sources", "design-doc", "Design document")
    frontmatter, body = split_frontmatter(source)
    frontmatter["sources"] = 42
    write_note(source, frontmatter, body)

    error = expect_invalid(brain, run_cli, capsys, source)
    assert "sources entries require" in error


def test_portable_rejects_secret_material_without_rewriting_the_source(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    note = brain / "wiki" / "credentials.md"
    contents = (
        "---\ntype: Architecture\ntitle: Credentials\n---\napi_key: sk-not-a-real-key\n"
    )
    note.write_text(contents, encoding="utf-8")

    assert run_cli("validate", str(brain)) == 1
    assert "probable secure material" in capsys.readouterr().err.lower()
    assert note.read_text(encoding="utf-8") == contents
    assert run_cli("validate", str(brain), "--okf") == 0


@pytest.mark.parametrize("relative", ["README.md", "templates/concept.md"])
def test_system_and_template_documents_do_not_bypass_portable_safety(
    tmp_path: Path,
    run_cli: RunCli,
    capsys: pytest.CaptureFixture[str],
    relative: str,
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    path = brain / relative
    original = path.read_text(encoding="utf-8")
    path.write_text(
        original + "\n[missing](missing.md)\npassword: definitely-not-safe\n",
        encoding="utf-8",
    )

    error = expect_invalid(brain, run_cli, capsys, path)
    assert "broken internal Markdown link" in error
    assert "probable secure material" in error


def test_stable_wiki_and_work_documents_require_descriptions(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--work") == 0
    wiki, _ = create_note(brain, run_cli, "wiki", "durable-note", "Durable note")
    work, _ = create_note(brain, run_cli, "work", "tracked-work", "Tracked work")
    for path in (wiki, work):
        data, body = split_frontmatter(path)
        data["status"] = "stable"
        write_note(path, data, body)

    error = expect_invalid(brain, run_cli, capsys, wiki)
    assert "non-empty description" in error
    assert work.name in error

    for path in (wiki, work):
        data, body = split_frontmatter(path)
        data["description"] = f"Orientation for {data['title']}."
        write_note(path, data, body)
    assert run_cli("validate", str(brain)) == 0


def test_configured_sections_are_required_in_manifest_order(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "travel") == 0
    assert run_cli("new", str(brain), "Itinerary", "day-one", "--title", "Day one") == 0
    note = brain / "wiki" / "travel" / "itineraries" / "day-one.md"
    data, body = split_frontmatter(note)
    body = body.replace("## Summary\n", "").replace(
        "## Schedule\n", "## Summary\n\n## Schedule\n", 1
    )
    write_note(
        note,
        data,
        body.replace("## Summary\n\n## Schedule", "## Schedule\n\n## Summary", 1),
    )

    error = expect_invalid(brain, run_cli, capsys, note)
    assert "missing or out of order" in error


def test_wiki_sources_join_declared_ids_to_footnotes(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    create_note(brain, run_cli, "sources", "evidence", "Evidence")
    wiki, _ = create_note(brain, run_cli, "wiki", "synthesis", "Synthesis")
    data, body = split_frontmatter(wiki)
    data["sources"] = [{"id": "evidence"}]
    write_note(
        wiki,
        data,
        body
        + "\nClaim.[^evidence]\n\n[^evidence]: [Evidence](../sources/evidence.md)\n",
    )
    assert run_cli("validate", str(brain)) == 0

    write_note(wiki, data, body + "\nClaim.[^evidence]\n")
    error = expect_invalid(brain, run_cli, capsys, wiki)
    assert "matching footnote" in error or "lack definitions" in error


def test_blocked_work_requires_resolving_markdown_link_blockers(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--work") == 0
    wiki, _ = create_note(brain, run_cli, "wiki", "dependency", "Dependency")
    work, _ = create_note(brain, run_cli, "work", "release", "Release")
    data, body = split_frontmatter(work)
    data["pb_work_state"] = "blocked"
    data["pb_blocked_on"] = ["Dependency"]
    write_note(work, data, body)
    error = expect_invalid(brain, run_cli, capsys, work)
    assert "standard Markdown link" in error

    data["pb_blocked_on"] = ["[Dependency](../wiki/dependency.md)"]
    write_note(work, data, body)
    assert wiki.exists()
    assert run_cli("validate", str(brain)) == 0


def test_okf_validation_does_not_require_a_portable_manifest(
    tmp_path: Path, run_cli: RunCli
) -> None:
    bundle = tmp_path / "okf-bundle"
    bundle.mkdir()
    write_note(
        bundle / "anything.md",
        {"type": "Concept", "title": "Anything"},
        "# Anything\n\n[Portable does not govern this link](missing.md)\napi_key: not-a-real-key\n",
    )

    assert run_cli("validate", str(bundle), "--okf") == 0
    assert run_cli("validate", str(bundle), "--portable") == 2


@pytest.mark.parametrize(
    ("filename", "title", "body"),
    [
        ("Not_Kebab.md", "Title", "# Title\n"),
        ("bad-title.md", "Bad\nTitle", "# Title\n"),
        ("bad-link.md", "Bad link", "[escape](../outside.md)\n"),
    ],
)
def test_portable_rejects_unsafe_filenames_titles_and_internal_links(
    tmp_path: Path,
    run_cli: RunCli,
    capsys: pytest.CaptureFixture[str],
    filename: str,
    title: str,
    body: str,
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    note = brain / "wiki" / filename
    write_note(note, {"type": "Architecture", "title": title}, body)

    expect_invalid(brain, run_cli, capsys, note)


def test_okf_permits_core_shape_that_portable_rejects_as_an_incomplete_source(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    source = brain / "sources" / "incomplete.md"
    write_note(
        source, {"type": "Source", "title": "Incomplete source"}, "# Incomplete\n"
    )

    assert run_cli("validate", str(brain), "--portable") == 1
    assert run_cli("validate", str(brain), "--okf") == 0


@pytest.mark.parametrize(
    "token",
    [
        "AKIAIOSFODNN7EXAMPLE",
        "ghp_" + "a" * 36,
        "github_pat_" + "A" * 30,
        "xoxb-123456789012-abcdefghij",
        "AIza" + "A" * 35,
        "sk-ant-api03-" + "x" * 30,
        "sk_live_" + "Z" * 24,
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    ],
)
def test_portable_recognizes_well_known_provider_tokens(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str], token: str
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    note = brain / "wiki" / "creds.md"
    note.write_text(
        f"---\ntype: Architecture\ntitle: Creds\n---\n# Creds\n\nValue {token} pasted.\n",
        encoding="utf-8",
    )
    assert run_cli("validate", str(brain)) == 1
    assert "probable secure material" in capsys.readouterr().err

    note.unlink()
    (brain / "inbox" / "creds.md").write_text(
        f"Value {token} pasted.\n", encoding="utf-8"
    )
    assert run_cli("validate", str(brain)) == 0
    assert "warning" in capsys.readouterr().err


def test_new_journal_uses_local_measured_time(tmp_path: Path, run_cli: RunCli) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    before = datetime.now().astimezone()
    assert (
        run_cli("new", str(brain), "Journal", "2026-08-23", "--title", "2026-08-23")
        == 0
    )
    after = datetime.now().astimezone()
    data, body = split_frontmatter(brain / "journal" / "2026-08-23.md")
    heading = re.search(r"^## (\d\d:\d\d) — Topic$", body, re.MULTILINE)
    assert heading is not None
    assert heading.group(1) in {before.strftime("%H:%M"), after.strftime("%H:%M")}
    generated = data["generated"]
    assert isinstance(generated, dict)
    at = datetime.fromisoformat(str(generated["at"]))
    assert at.tzinfo is not None and at.utcoffset() == after.utcoffset()


def test_journal_times_that_run_backwards_or_past_the_clock_are_warnings(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    backwards = brain / "journal" / "2026-01-05.md"
    write_note(
        backwards,
        {"type": "Journal", "title": "2026-01-05"},
        "# 2026-01-05\n\n## 10:00 — first\n\nactor: human:t\n\nOne.\n\n## 09:00 — second\n\nactor: human:t\n\nTwo.\n",
    )
    assert run_cli("validate", str(brain)) == 0
    err = capsys.readouterr().err
    assert (
        "journal/2026-01-05.md: warning:" in err
        and "not in chronological order: 10:00 then 09:00" in err
    )

    now = datetime.now().astimezone()
    if now.strftime("%H:%M") < "23:58":
        today = brain / "journal" / f"{now.date().isoformat()}.md"
        write_note(
            today,
            {"type": "Journal", "title": now.date().isoformat()},
            f"# {now.date().isoformat()}\n\n## 23:59 — later\n\nactor: human:t\n\nGuessed.\n",
        )
        assert run_cli("validate", str(brain)) == 0
        assert "is later than now" in capsys.readouterr().err
