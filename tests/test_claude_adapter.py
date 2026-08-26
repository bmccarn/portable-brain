from __future__ import annotations

import json
import os
import subprocess
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


def run_hook(
    brain: Path, tmp: Path, payload: dict[str, object], cwd: Path | None = None
) -> str:
    env = {**os.environ, "TMPDIR": str(tmp), "CLAUDE_PROJECT_DIR": str(cwd or brain)}
    result = subprocess.run(
        ["bash", str(brain / ".claude" / "hooks" / "session-end-gate.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd or brain,
        env=env,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_claude_adapter_ships_hook_settings_and_skills_that_validation_ignores(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--adapter", "claude", "obsidian") == 0
    manifest = yaml.safe_load(
        (brain / ".portable-brain" / "profile.yaml").read_text(encoding="utf-8")
    )
    assert manifest["adapters"] == ["claude", "obsidian"]

    settings = json.loads(
        (brain / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    command = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert "session-end-gate.sh" in command and "CLAUDE_PROJECT_DIR" in command
    hook = brain / ".claude" / "hooks" / "session-end-gate.sh"
    assert hook.is_file() and os.access(hook, os.X_OK)
    for name in ("setup", "triage", "sweep", "query", "session-end"):
        skill = brain / ".claude" / "skills" / name / "SKILL.md"
        text = skill.read_text(encoding="utf-8")
        assert text.startswith("---\nname: " + name + "\n")
        assert "description:" in text and "AGENTS.md" in text

    agents = (brain / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Setup" in agents and "## Owner's rules" in agents
    assert run_cli("validate", str(brain)) == 0
    assert capsys.readouterr().err == ""
    assert run_cli("index", str(brain), "--check") == 0
    assert "SKILL" not in (brain / "wiki" / "index.md").read_text(encoding="utf-8")

    plain = tmp_path / "plain"
    assert run_cli("init", str(plain)) == 0
    assert not (plain / ".claude").exists()


def test_session_end_gate_blocks_once_per_session_with_measured_state(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--adapter", "claude") == 0
    (brain / "inbox" / "a.txt").write_text("x", encoding="utf-8")
    (brain / "inbox" / "b.md").write_text("y", encoding="utf-8")
    sentinels = tmp_path / "sentinels"
    sentinels.mkdir()

    first = json.loads(run_hook(brain, sentinels, {"session_id": "abc-123"}))
    assert first["decision"] == "block"
    reason = first["reason"]
    assert "Inbox pending: 2" in reason
    assert "journal" in reason and "missing" in reason
    assert "session: claude-code abc-123" in reason
    assert "AGENTS.md" in reason and "once per session" in reason
    assert "dispel" not in reason.lower() and "DZTE" not in reason

    assert run_hook(brain, sentinels, {"session_id": "abc-123"}) == ""
    assert (
        run_hook(brain, sentinels, {"session_id": "other", "stop_hook_active": True})
        == ""
    )
    second = json.loads(run_hook(brain, sentinels, {"session_id": "other"}))
    assert second["decision"] == "block"

    nested = brain / "wiki"
    nested_run = json.loads(
        run_hook(brain, sentinels, {"session_id": "nested"}, cwd=nested)
    )
    assert str(brain) in nested_run["reason"]

    outside = tmp_path / "elsewhere"
    outside.mkdir()
    assert run_hook(brain, sentinels, {"session_id": "outside"}, cwd=outside) == ""
