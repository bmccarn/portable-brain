from __future__ import annotations

import getpass
import shutil
import tomllib
from collections.abc import Callable
from importlib import resources
from pathlib import Path

import pytest
import yaml

from portable_brain.cli import main

RunCli = Callable[..., int]


@pytest.fixture
def run_cli(capsys: pytest.CaptureFixture[str]) -> RunCli:
    def run(*arguments: str) -> int:
        return main(list(arguments))

    return run


def manifest_for(brain: Path) -> dict[str, object]:
    manifest = yaml.safe_load(
        (brain / ".portable-brain" / "profile.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(manifest, dict)
    return manifest


def types_in_group(
    manifest: dict[str, object], group: str
) -> list[tuple[str, dict[str, object]]]:
    types = manifest["types"]
    assert isinstance(types, dict)
    result: list[tuple[str, dict[str, object]]] = []
    for name, definition in types.items():
        assert isinstance(name, str) and isinstance(definition, dict)
        if definition["group"] == group:
            result.append((name, definition))
    return result


def note_path(brain: Path, definition: dict[str, object], slug: str) -> Path:
    group = definition["group"]
    folder = definition["folder"]
    assert isinstance(group, str) and isinstance(folder, str)
    directory = brain / group if folder == "." else brain / group / folder
    return directory / f"{slug}.md"


@pytest.mark.parametrize(
    "domains",
    [
        (),
        ("software",),
        ("personal",),
        ("research",),
        ("travel",),
        ("software", "personal", "research", "travel"),
    ],
)
def test_init_resolves_each_requested_domain_set_into_one_active_manifest(
    tmp_path: Path, run_cli: RunCli, domains: tuple[str, ...]
) -> None:
    brain = tmp_path / ("-".join(domains) or "base")
    arguments = ["init", str(brain)]
    if domains:
        arguments.extend(("--domains", *domains))

    assert run_cli(*arguments) == 0

    config = brain / ".portable-brain"
    assert sorted(path.name for path in config.glob("*.yaml")) == ["profile.yaml"]
    manifest = manifest_for(brain)
    for key in ("groups", "workflow", "types"):
        assert key in manifest

    groups = manifest["groups"]
    workflow = manifest["workflow"]
    types = manifest["types"]
    assert manifest["domains"] == list(domains)
    assert manifest["modules"] == []
    assert "profile" not in manifest
    assert isinstance(groups, dict)
    assert list(groups) == ["inbox", "sources", "wiki", "journal"]
    assert isinstance(workflow, dict)
    assert list(workflow) == [
        "states",
        "initial_state",
        "closed_states",
        "requires_blocked_on",
    ]
    assert workflow["initial_state"] == "active"
    assert workflow["closed_states"] == ["done", "dropped"]
    assert isinstance(types, dict)
    assert "Journal" in types
    for type_name, group in (
        ("Source", "sources"),
        ("Concept", "wiki"),
        ("Journal", "journal"),
    ):
        definition = types[type_name]
        assert isinstance(definition, dict)
        assert definition["group"] == group
        assert definition["folder"] == "."

    for directory in ("inbox", "sources", "wiki", "journal", "assets"):
        assert (brain / directory).is_dir()
    assert not (brain / "work").exists()
    work_types = types_in_group(manifest, "work")
    assert work_types == []

    for name, definition in types.items():
        assert isinstance(name, str) and isinstance(definition, dict)
        assert definition["group"] in groups
        assert isinstance(definition["folder"], str)
        assert isinstance(definition["workflow"], bool)
        assert isinstance(definition["sections"], list)

    assert all(definition["workflow"] is False for definition in types.values())


@pytest.mark.parametrize(
    "domains",
    [(), ("software",), ("software", "personal", "research", "travel")],
)
def test_work_is_an_explicit_composable_module(
    tmp_path: Path, run_cli: RunCli, domains: tuple[str, ...]
) -> None:
    brain = tmp_path / ("work-" + ("-".join(domains) or "core"))
    arguments = ["init", str(brain)]
    if domains:
        arguments.extend(("--domains", *domains))
    arguments.append("--work")

    assert run_cli(*arguments) == 0
    manifest = manifest_for(brain)
    assert manifest["domains"] == list(domains)
    assert manifest["modules"] == ["work"]
    assert "profile" not in manifest
    groups = manifest["groups"]
    assert isinstance(groups, dict)
    assert list(groups) == ["inbox", "sources", "wiki", "journal", "work"]
    assert (brain / "work").is_dir()
    work_types = {name for name, _ in types_in_group(manifest, "work")}
    assert {"Decision", "Project"}.issubset(work_types)
    if "software" in domains:
        assert {"Change", "Deployment", "Incident"}.issubset(work_types)
    if "personal" in domains:
        assert "Goal" in work_types
    if "research" in domains:
        assert {"Question", "Hypothesis", "Experiment"}.issubset(work_types)
    if "travel" in domains:
        assert "Trip" in work_types


def test_obsidian_work_views_exist_only_when_work_is_enabled(
    tmp_path: Path, run_cli: RunCli
) -> None:
    core = tmp_path / "core"
    work = tmp_path / "work"
    assert run_cli("init", str(core), "--adapter", "obsidian") == 0
    assert run_cli("init", str(work), "--work", "--adapter", "obsidian") == 0

    for name in ("workflow.base", "closed-work.base"):
        assert not (core / "views" / name).exists()
        assert (work / "views" / name).is_file()
    assert "Workflow" not in (core / "HOME.md").read_text(encoding="utf-8")
    assert "Workflow" in (work / "HOME.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["file.txt", ".hidden"])
def test_init_refuses_a_nonempty_target(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    brain = tmp_path / "existing"
    brain.mkdir()
    (brain / name).write_text("existing work", encoding="utf-8")

    assert run_cli("init", str(brain)) == 2
    assert "non-empty" in capsys.readouterr().err.lower()
    assert (brain / name).read_text(encoding="utf-8") == "existing work"


def test_new_creates_group_scoped_notes_and_refuses_overwrite(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software") == 0
    manifest = manifest_for(brain)
    wiki_type, wiki_definition = types_in_group(manifest, "wiki")[0]

    assert (
        run_cli("new", str(brain), wiki_type, "architecture", "--title", "Architecture")
        == 0
    )
    note = note_path(brain, wiki_definition, "architecture")
    assert note.is_file()
    original = note.read_text(encoding="utf-8")
    assert "type: " + wiki_type in original
    assert "title: Architecture" in original
    assert "pb_" not in original

    assert (
        run_cli("new", str(brain), wiki_type, "architecture", "--title", "Changed") == 2
    )
    assert "refusing to overwrite" in capsys.readouterr().err.lower()
    assert note.read_text(encoding="utf-8") == original
    assert (
        run_cli("new", str(brain), wiki_type, "Not_A_Slug", "--title", "Invalid") == 2
    )
    assert not note_path(brain, wiki_definition, "Not_A_Slug").exists()
    assert (
        run_cli("new", str(brain), wiki_type, "bad-title", "--title", "Bad\nTitle") == 2
    )


def test_inspect_reports_resolved_layers_and_configured_workflow(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert (
        run_cli("init", str(brain), "--domains", "software", "research", "--work") == 0
    )

    assert run_cli("inspect", str(brain)) == 0
    output = capsys.readouterr().out
    for layer in ("inbox", "sources", "wiki", "journal", "work", "assets"):
        assert layer in output
    for state in ("active", "done", "dropped"):
        assert state in output


def test_archive_requires_confirmation_preserves_the_note_and_refuses_collision(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software", "--work") == 0
    work_type, work_definition = next(
        item
        for item in types_in_group(manifest_for(brain), "work")
        if item[1]["folder"] == "."
    )
    assert run_cli("new", str(brain), work_type, "release", "--title", "Release") == 0
    original = note_path(brain, work_definition, "release")
    original_bytes = original.read_bytes()

    assert run_cli("archive", str(brain), "release") == 2
    assert original.exists()
    assert run_cli("archive", str(brain), "release", "yes") == 0
    archived = brain / "work" / "archive" / "release.md"
    assert not original.exists()
    assert archived.read_bytes() == original_bytes
    assert "release" in capsys.readouterr().out.lower()
    assert run_cli("archive", str(brain), "release", "yes") == 2
    assert archived.read_bytes() == original_bytes
    empty = tmp_path / "empty"
    assert run_cli("init", str(empty), "--domains", "software", "--work") == 0
    assert run_cli("archive", str(empty), "nothing", "yes") == 2


def test_packaged_scaffold_and_starter_keep_the_canonical_spec_in_sync(
    tmp_path: Path, run_cli: RunCli
) -> None:
    repository = Path(__file__).parents[1]
    scaffold = resources.files("portable_brain.resources.scaffold")
    for shared in (
        "LICENSE",
        "MIGRATIONS.md",
        "SECURITY.md",
        "SPEC.md",
        "START-HERE.md",
    ):
        assert (repository / shared).read_bytes() == scaffold.joinpath(
            shared
        ).read_bytes()

    generated = tmp_path / "generated"
    assert (
        run_cli(
            "init",
            str(generated),
            "--adapter",
            "obsidian",
            "claude",
            "--actor",
            "human:owner",
        )
        == 0
    )
    starter = repository / "starter"
    starter_files = sorted(
        path.relative_to(starter) for path in starter.rglob("*") if path.is_file()
    )
    generated_files = sorted(
        path.relative_to(generated) for path in generated.rglob("*") if path.is_file()
    )
    assert generated_files == starter_files
    for relative in starter_files:
        assert (generated / relative).read_bytes() == (starter / relative).read_bytes()

    copied = tmp_path / "copied"
    shutil.copytree(starter, copied)
    assert run_cli("validate", str(copied)) == 0


def test_every_packaged_resource_file_is_declared_in_package_data() -> None:
    repository = Path(__file__).parents[1]
    config = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))
    patterns = config["tool"]["setuptools"]["package-data"]["portable_brain"]
    package = repository / "src" / "portable_brain"
    shipped = [
        path
        for path in (package / "resources").rglob("*")
        if path.is_file() and path.suffix != ".py" and "__pycache__" not in path.parts
    ]
    assert shipped

    undeclared = sorted(
        relative.as_posix()
        for relative in (path.relative_to(package) for path in shipped)
        if not any(relative.match(pattern) for pattern in patterns)
    )
    assert not undeclared, f"resource files absent from package-data: {undeclared}"


def test_init_default_actor_is_current_human_user(
    tmp_path: Path, run_cli: RunCli
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain)) == 0
    manifest = manifest_for(brain)
    assert manifest["default_actor"] == f"human:{getpass.getuser()}"


def test_archive_mirrors_nested_work_and_refuses_type_folders(
    tmp_path: Path, run_cli: RunCli, capsys: pytest.CaptureFixture[str]
) -> None:
    brain = tmp_path / "brain"
    assert run_cli("init", str(brain), "--domains", "software", "travel", "--work") == 0
    assert (
        run_cli("new", str(brain), "Change", "add-logging", "--title", "Add logging")
        == 0
    )
    assert run_cli("new", str(brain), "Trip", "lisbon", "--title", "Lisbon") == 0
    assert run_cli("validate", str(brain)) == 0

    for folder in ("changes", "travel", "travel/trips"):
        assert run_cli("archive", str(brain), folder, "yes") == 2
        assert "configured type folder" in capsys.readouterr().err
        assert (brain / "work" / folder).is_dir()

    assert run_cli("archive", str(brain), "changes/add-logging", "yes") == 0
    assert (brain / "work" / "archive" / "changes" / "add-logging.md").is_file()
    assert run_cli("archive", str(brain), "travel/trips/lisbon.md", "yes") == 0
    assert (brain / "work" / "archive" / "travel" / "trips" / "lisbon.md").is_file()
    assert run_cli("validate", str(brain)) == 0
    assert run_cli("index", str(brain)) == 0
    work_index = (brain / "work" / "index.md").read_text(encoding="utf-8")
    assert "## Archive" in work_index and "add-logging.md" in work_index
    assert run_cli("archive", str(brain), "archive/changes/add-logging", "yes") == 2

    misplaced = brain / "work" / "archive" / "misplaced.md"
    shutil.move(
        str(brain / "work" / "archive" / "changes" / "add-logging.md"), misplaced
    )
    assert run_cli("validate", str(brain)) == 1
    assert "misplaced.md" in capsys.readouterr().err
