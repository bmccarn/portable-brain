from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from portable_brain.cli import main

RunCli = Callable[..., int]
REPO = Path(__file__).parents[1]


@pytest.fixture
def run_cli() -> RunCli:
    def run(*arguments: str) -> int:
        return main(list(arguments))

    return run


def test_nursery_example_is_a_valid_fresh_brain_with_one_pending_inbox_item(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "nursery"
    shutil.copytree(REPO / "examples" / "nursery", brain)

    assert run_cli("validate", str(brain)) == 0
    assert capsys.readouterr().err == ""
    assert run_cli("index", str(brain), "--check") == 0
    assert run_cli("inspect", str(brain)) == 0
    out = capsys.readouterr().out
    assert "inbox: 1" in out and "inbox/grandma-voice-memo-transcript.txt" in out
    assert "assets: 2" in out and "sources: 3" in out and "journal: 3" in out

    for relative in (
        "assets/crib-assembly-manual.pdf",
        "assets/paint-swatch-sage.png",
        "sources/crib-assembly-manual.md",
        "wiki/nursery.md",
        "work/nursery-setup.md",
        "work/crib-placement.md",
        "journal/2026-08-10.md",
    ):
        assert (brain / relative).is_file(), relative
    assert (
        (brain / "assets" / "paint-swatch-sage.png").read_bytes().startswith(b"\x89PNG")
    )
    assert (
        (brain / "assets" / "crib-assembly-manual.pdf").read_bytes().startswith(b"%PDF")
    )
