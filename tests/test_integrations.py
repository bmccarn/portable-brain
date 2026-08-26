from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).parents[1]


def load_paperless_module():  # type: ignore[no-untyped-def]
    path = REPO / "integrations" / "paperless" / "paperless_to_inbox.py"
    spec = importlib.util.spec_from_file_location("paperless_to_inbox", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_paperless_queries_union_kinds_and_narrow_by_date() -> None:
    module = load_paperless_module()
    tags = {"insurance": 279}
    types = {"Auto Insurance": 64, "Insurance Notice": 160}
    correspondents = {"Progressive": 235}
    queries = module.build_queries(
        ["insurance"],
        ["Auto Insurance", "Insurance Notice"],
        ["Progressive"],
        "2026-08-01",
        tags,
        types,
        correspondents,
    )
    assert len(queries) == 3
    assert queries[0].startswith("documents/?tags__id__in=279&")
    assert "document_type__id__in=64,160" in queries[1]
    assert "correspondent__id__in=235" in queries[2]
    assert all(
        "added__date__gt=2026-08-01" in query and "fields=" in query
        for query in queries
    )
    assert module.build_queries([], [], [], None, tags, types, correspondents) == [
        f"documents/?ordering=created&page_size=100&fields={module.FIELDS}"
    ]
    with pytest.raises(SystemExit, match="unknown tag: nope"):
        module.build_queries(["nope"], [], [], None, tags, types, correspondents)


def test_paperless_script_requires_credentials_and_a_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_paperless_module()
    monkeypatch.delenv("PAPERLESS_TOKEN", raising=False)
    monkeypatch.delenv("PAPERLESS_URL", raising=False)
    with pytest.raises(SystemExit):
        module.main([str(tmp_path), "--all"])
    monkeypatch.setenv("PAPERLESS_TOKEN", "x")
    with pytest.raises(SystemExit):
        module.main([str(tmp_path), "--url", "https://example.invalid"])


def test_paperless_sidecar_cites_the_url_when_text_only_and_the_file_when_present() -> (
    None
):
    module = load_paperless_module()
    doc = {
        "id": 42,
        "title": "Water bill",
        "created": "2026-08-01",
        "added": "2026-08-02T10:00:00",
        "correspondent": 1,
        "document_type": 2,
        "tags": [3],
        "original_file_name": "bill.pdf",
        "page_count": 2,
    }
    names = {
        "correspondents": {1: "Utility Co"},
        "document_types": {2: "Utility Bill"},
        "tags": {3: "utilities"},
    }
    text_only = module.sidecar(
        doc, names, "https://paperless.example.net", None, "Amount due 42.00", []
    )
    assert (
        "file:" not in text_only
        and "paperless_url: https://paperless.example.net/documents/42/details"
        in text_only
    )
    assert "stays in Paperless" in text_only and "Amount due 42.00" in text_only
    with_file = module.sidecar(
        doc,
        names,
        "https://paperless.example.net",
        "2026-08-01-paperless-42-water-bill.pdf",
        "x",
        ["note"],
    )
    assert (
        "file: 2026-08-01-paperless-42-water-bill.pdf" in with_file
        and "## Paperless notes" in with_file
    )


def test_campaign_runner_is_valid_bash_and_refuses_non_brains(tmp_path: Path) -> None:
    script = REPO / "integrations" / "claude-code" / "triage-campaign.sh"
    assert subprocess.run(["bash", "-n", str(script)], check=False).returncode == 0
    result = subprocess.run(
        ["bash", str(script), str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2 and "not a brain" in result.stderr
