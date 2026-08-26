"""Profile-resource and active-manifest loading for Portable Brain."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from copy import deepcopy
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

MANIFEST_RELATIVE_PATH = Path(".portable-brain") / "profile.yaml"
_REQUIRED_GROUPS = frozenset({"inbox", "sources", "wiki", "journal"})
_OPTIONAL_GROUPS = frozenset({"work"})
_ACTOR = re.compile(
    r"(?:human|process):[A-Za-z0-9][A-Za-z0-9._@+-]*|[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._+-]*\Z"
)
SUPPORTED_ADAPTERS = frozenset({"claude", "obsidian"})
_SUPPORTED_ADAPTERS = SUPPORTED_ADAPTERS


class ManifestError(ValueError):
    """Raised when a manifest cannot be used safely."""


def is_valid_actor(value: object) -> bool:
    return isinstance(value, str) and _ACTOR.fullmatch(value) is not None


def type_directory(manifest: Mapping[str, Any], type_name: str) -> Path:
    """Return the group-root-relative directory for one configured type."""
    definition = manifest["types"][type_name]
    group = Path(definition["group"])
    folder = definition["folder"]
    return group if folder == "." else group / folder


def _merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(base))
    for key, value in overlay.items():
        result[key] = (
            _merge(result[key], value)
            if isinstance(result.get(key), Mapping) and isinstance(value, Mapping)
            else deepcopy(value)
        )
    return result


def _yaml(text: str, source: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ManifestError(f"invalid YAML in {source}: {error}") from error
    if not isinstance(parsed, Mapping) or any(
        not isinstance(key, str) for key in parsed
    ):
        raise ManifestError(f"{source} must be a mapping with string keys")
    return dict(parsed)


def _resources() -> Traversable:
    try:
        return resources.files("portable_brain.resources").joinpath("profiles")
    except ModuleNotFoundError as error:
        raise ManifestError("package profile resources are unavailable") from error


def available_domains() -> tuple[str, ...]:
    reserved = {"core.yaml", "work.yaml"}
    return tuple(
        sorted(
            item.name[:-5]
            for item in _resources().iterdir()
            if item.is_file()
            and item.name.endswith(".yaml")
            and item.name not in reserved
        )
    )


def _profile(name: str) -> dict[str, Any]:
    resource = _resources().joinpath(f"{name}.yaml")
    if not resource.is_file():
        raise ManifestError(f"unknown domain profile: {name}")
    return _yaml(resource.read_text(encoding="utf-8"), f"profile {name}")


def domain_overlay(name: str) -> dict[str, Any]:
    """Return one packaged domain overlay (types only)."""
    if name not in available_domains():
        raise ManifestError(f"unknown domain: {name}")
    return _profile(name)


def work_overlay() -> dict[str, Any]:
    """Return the packaged work module: its group and its core work types."""
    return _profile("work")


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ManifestError(f"manifest field {field!r} must be a mapping")
    return value


def _folder(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or Path(value).is_absolute()
        or ".." in Path(value).parts
    ):
        raise ManifestError(f"{field} must be a safe non-empty relative folder")
    return value


def validate_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the frozen group-based manifest schema."""
    result = deepcopy(dict(manifest))
    for field, expected in {
        "schema_version": 1,
        "spec_version": "0.1",
        "okf_version": "0.2",
    }.items():
        if result.get(field) != expected:
            raise ManifestError(f"manifest field {field!r} must equal {expected!r}")
    actor = result.get("default_actor")
    if actor not in (None, "") and not is_valid_actor(actor):
        raise ManifestError(
            "manifest field 'default_actor' must be an OKF actor when configured"
        )
    groups = _mapping(result.get("groups"), "groups")
    allowed = _REQUIRED_GROUPS | _OPTIONAL_GROUPS
    if not _REQUIRED_GROUPS.issubset(groups) or not set(groups).issubset(allowed):
        raise ManifestError(
            "groups must include inbox, sources, wiki, journal; work is optional"
        )
    checked_groups: dict[str, dict[str, Any]] = {}
    for name, raw in groups.items():
        definition = _mapping(raw, f"groups.{name}")
        if (
            not isinstance(definition.get("description"), str)
            or not definition["description"].strip()
            or not isinstance(definition.get("strict"), bool)
        ):
            raise ManifestError(
                f"groups.{name} requires description and boolean strict"
            )
        checked_groups[name] = {
            "description": definition["description"],
            "strict": definition["strict"],
        }
    workflow = _mapping(result.get("workflow"), "workflow")
    states = _mapping(workflow.get("states"), "workflow.states")
    if not states or any(
        not isinstance(name, str)
        or not name
        or not isinstance(label, str)
        or not label.strip()
        for name, label in states.items()
    ):
        raise ManifestError("workflow.states must map non-empty names to labels")
    initial = workflow.get("initial_state")
    if not isinstance(initial, str) or initial not in states:
        raise ManifestError("workflow.initial_state must name workflow.states")
    closed = workflow.get("closed_states", ["done", "dropped"])
    if not isinstance(closed, list) or any(item not in states for item in closed):
        raise ManifestError("workflow.closed_states must be a list of workflow.states")
    required_blockers = workflow.get("requires_blocked_on", [])
    if not isinstance(required_blockers, list) or any(
        not isinstance(state, str) or state not in states for state in required_blockers
    ):
        raise ManifestError(
            "workflow.requires_blocked_on must be a list of workflow.states"
        )
    adapters = result.get("adapters", [])
    names = (
        set(adapters)
        if isinstance(adapters, list)
        else {key for key, value in adapters.items() if value is not False}
        if isinstance(adapters, Mapping)
        else None
    )
    if (
        names is None
        or any(not isinstance(name, str) for name in names)
        or not names.issubset(_SUPPORTED_ADAPTERS)
    ):
        raise ManifestError("manifest contains an unsupported adapter")
    domains = result.get("domains", [])
    if (
        not isinstance(domains, list)
        or any(
            not isinstance(name, str) or name not in available_domains()
            for name in domains
        )
        or len(domains) != len(set(domains))
    ):
        raise ManifestError(
            "manifest domains must be a unique list of supported domains"
        )
    modules = result.get("modules", ["work"] if "work" in checked_groups else [])
    if (
        not isinstance(modules, list)
        or any(name != "work" for name in modules)
        or len(modules) != len(set(modules))
    ):
        raise ManifestError(
            "manifest modules must be a unique list containing only work"
        )
    if ("work" in modules) != ("work" in checked_groups):
        raise ManifestError("the work module and work group must be enabled together")
    types = _mapping(result.get("types"), "types")
    checked_types: dict[str, dict[str, Any]] = {}
    for name, raw in types.items():
        definition = _mapping(raw, f"types.{name}")
        group = definition.get("group")
        folder = _folder(definition.get("folder"), f"types.{name}.folder")
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(group, str)
            or group not in checked_groups
        ):
            raise ManifestError(f"types.{name} must name a configured group")
        if group == "work" and Path(folder).parts[:1] == ("archive",):
            raise ManifestError(
                f"types.{name}.folder may not use the reserved work/archive directory"
            )
        if (
            group in {"sources", "work"}
            and folder != "."
            and any(
                existing["group"] == group and existing["folder"] == folder
                for existing in checked_types.values()
            )
        ):
            raise ManifestError(f"strict group {group} reuses folder {folder!r}")
        if not isinstance(definition.get("workflow"), bool) or definition[
            "workflow"
        ] != (group == "work"):
            raise ManifestError(
                f"types.{name}.workflow must be true exactly for work types"
            )
        sections = definition.get("sections", [])
        if (
            not isinstance(sections, list)
            or any(not isinstance(item, str) or not item.strip() for item in sections)
            or len(sections) != len(set(sections))
        ):
            raise ManifestError(
                f"types.{name}.sections must contain unique non-empty strings"
            )
        checked_types[name] = {
            "group": group,
            "folder": folder,
            "workflow": definition["workflow"],
            "sections": list(sections),
        }
    if "Journal" not in checked_types or checked_types["Journal"] != {
        "group": "journal",
        "folder": ".",
        "workflow": False,
        "sections": [],
    }:
        raise ManifestError("Journal must be journal/. with no workflow or sections")
    result["groups"] = checked_groups
    result["workflow"] = {
        "states": dict(states),
        "initial_state": initial,
        "closed_states": list(closed),
        "requires_blocked_on": list(required_blockers),
    }
    result["types"] = checked_types
    result["adapters"] = sorted(names)
    result["domains"] = list(domains)
    result["modules"] = list(modules)
    return result


def load_profiles(
    domains: Sequence[str] = (), *, include_work: bool = False
) -> dict[str, Any]:
    if len(set(domains)) != len(domains):
        raise ManifestError("each domain may be selected only once")
    unknown = set(domains) - set(available_domains())
    if unknown:
        raise ManifestError(f"unknown domain(s): {', '.join(sorted(unknown))}")
    result = _profile("core")
    if include_work:
        result = _merge(result, _profile("work"))
    for domain in domains:
        result = _merge(result, _profile(domain))
    if not include_work:
        types = _mapping(result.get("types"), "types")
        result["types"] = {
            name: definition
            for name, definition in types.items()
            if not isinstance(definition, Mapping) or definition.get("group") != "work"
        }
        groups = dict(_mapping(result.get("groups"), "groups"))
        groups.pop("work", None)
        result["groups"] = groups
    result["domains"] = list(domains)
    result["modules"] = ["work"] if include_work else []
    return validate_manifest(result)


def load_profile(name: str, *, include_work: bool = False) -> dict[str, Any]:
    if name == "work":
        return load_profiles((), include_work=True)
    return (
        load_profiles((), include_work=include_work)
        if name == "core"
        else load_profiles((name,), include_work=include_work)
    )


def load_manifest(target: str | Path) -> dict[str, Any]:
    path = Path(target) / MANIFEST_RELATIVE_PATH
    if not path.is_file():
        raise ManifestError(f"brain manifest does not exist: {path}")
    try:
        return validate_manifest(_yaml(path.read_text(encoding="utf-8"), str(path)))
    except OSError as error:
        raise ManifestError(f"cannot read brain manifest: {error}") from error
