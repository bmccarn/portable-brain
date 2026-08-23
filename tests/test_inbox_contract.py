from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from portable_brain.cli import main

RunCli = Callable[..., int]


@pytest.fixture
def run_cli() -> RunCli:
    def run(*arguments: str) -> int:
        return main(list(arguments))

    return run


def drop_anything(brain: Path) -> dict[str, Path]:
    """Put material of every form into inbox/ the way a person would: no ceremony."""
    inbox = brain / "inbox"
    items = {
        "bare": inbox / "random-thought.md",
        "h1": inbox / "meeting.md",
        "fronted": inbox / "clipping.md",
        "text": inbox / "dump.txt",
        "image": inbox / "photo.png",
        "nested": inbox / "trip-photos" / "day-one.jpg",
        "hazard": inbox / "pasted-config.md",
    }
    items["bare"].write_text("just a quick thought about the trip\n", encoding="utf-8")
    items["h1"].write_text("# Standup notes\n\nShipped the thing.\n", encoding="utf-8")
    items["fronted"].write_text(
        "---\ntitle: Article clipping\n---\nBody.\n", encoding="utf-8"
    )
    items["text"].write_text("Some plain text dump\n", encoding="utf-8")
    items["image"].write_bytes(b"\x89PNG not really")
    items["nested"].parent.mkdir()
    items["nested"].write_bytes(b"\xff\xd8 not really")
    items["hazard"].write_text(
        "See [[old-note]] and [gone](missing.md)\npassword: definitely-not-safe\n",
        encoding="utf-8",
    )
    return items


def test_inbox_accepts_anything_and_never_fails_validation_or_indexing(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    items = drop_anything(brain)

    assert run_cli("validate", str(brain)) == 0
    err = capsys.readouterr().err
    assert "pasted-config.md: warning:" in err
    assert "probable secure material" in err
    assert "wikilink" in err.lower()
    assert "broken internal Markdown link" in err
    for name in (
        "random-thought.md",
        "meeting.md",
        "clipping.md",
        "dump.txt",
        "photo.png",
        "day-one.jpg",
    ):
        assert name not in err, f"{name} should produce no warning"

    assert run_cli("index", str(brain)) == 0
    inbox_index = (brain / "inbox" / "index.md").read_text(encoding="utf-8")
    assert "[random-thought.md](random-thought.md)" in inbox_index
    assert "[Standup notes](meeting.md)" in inbox_index
    assert "[Article clipping](clipping.md)" in inbox_index
    assert "[dump.txt](dump.txt)" in inbox_index
    assert "[photo.png](photo.png)" in inbox_index
    assert "## Trip Photos" in inbox_index
    assert "[day-one.jpg](trip-photos/day-one.jpg)" in inbox_index
    assert "[pasted-config.md](pasted-config.md)" in inbox_index
    assert "index.md" not in inbox_index.split("# Inbox index", 1)[1]
    root_index = (brain / "index.md").read_text(encoding="utf-8")
    assert f"[Inbox](inbox/index.md) — {len(items)} items" in root_index

    assert run_cli("inspect", str(brain)) == 0
    out = capsys.readouterr().out
    assert f"inbox: {len(items)}" in out
    assert "inbox (pending triage):" in out
    assert "inbox/trip-photos/day-one.jpg" in out
    assert "inbox/pasted-config.md" in out
    for path in items.values():
        assert path.exists(), "validation and indexing never touch inbox content"


def test_the_gate_is_on_the_way_out_not_the_way_in(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    bare = "just a quick thought\n"
    (brain / "inbox" / "thought.md").write_text(bare, encoding="utf-8")
    assert run_cli("validate", str(brain)) == 0

    (brain / "wiki" / "thought.md").write_text(bare, encoding="utf-8")
    assert run_cli("validate", str(brain)) == 1
    err = capsys.readouterr().err
    assert "wiki/thought.md" in err
    assert "inbox/thought.md" not in err
    assert run_cli("index", str(brain)) == 1


def test_triage_empties_inbox_and_inspect_counts_real_assets(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    items = drop_anything(brain)
    assert run_cli("index", str(brain)) == 0

    shutil.move(str(items["image"]), brain / "assets" / "photo.png")
    shutil.move(str(items["nested"]), brain / "assets" / "day-one.jpg")
    shutil.rmtree(items["nested"].parent)
    for key in ("bare", "h1", "fronted", "text", "hazard"):
        items[key].unlink()

    assert run_cli("validate", str(brain)) == 0
    err = capsys.readouterr().err
    assert "inbox/index.md: warning:" in err and "stale" in err
    assert run_cli("index", str(brain), "--check") == 1
    assert "stale" in capsys.readouterr().err
    assert run_cli("index", str(brain)) == 0
    assert run_cli("validate", str(brain)) == 0
    assert capsys.readouterr().err == ""
    assert "[Inbox](inbox/index.md) — 0 items" in (brain / "index.md").read_text(
        encoding="utf-8"
    )
    assert (
        (brain / "inbox" / "index.md")
        .read_text(encoding="utf-8")
        .rstrip()
        .endswith("# Inbox index")
    )

    assert run_cli("inspect", str(brain)) == 0
    out = capsys.readouterr().out
    assert "inbox: 0" in out
    assert "assets: 2" in out
    assert "inbox (pending triage):\ntypes:" in out


def test_inbox_generated_index_is_still_governed(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    (brain / "inbox" / "index.md").write_text(
        "---\ntype: Concept\ntitle: Hand-edited\n---\n# Nope\n", encoding="utf-8"
    )
    assert run_cli("validate", str(brain)) == 1
    assert "inbox/index.md" in capsys.readouterr().err
