"""Brain creation, authoring, validation, indexing, archival, and inspection."""

from __future__ import annotations

import getpass
import posixpath
import re
import shutil
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import yaml

from .frontmatter import FrontmatterError, dump_frontmatter, parse_frontmatter
from .manifest import (
    MANIFEST_RELATIVE_PATH,
    SUPPORTED_ADAPTERS,
    ManifestError,
    domain_overlay,
    is_valid_actor,
    load_manifest,
    load_profiles,
    type_directory,
    validate_manifest,
    work_overlay,
)

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
H1 = re.compile(r"^# (.+?)\s*$", re.MULTILINE)
SESSION = re.compile(r"^## ([01]\d|2[0-3]):[0-5]\d — (\S.*)$", re.MULTILINE)
CHECK = re.compile(r"^\s*(?:[-*+] |\d+\. )\[[ xX]\]", re.MULTILINE)
WIKI = re.compile(r"!?\[\[[^\]\n]+\]\]")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)")
FOOTDEF = re.compile(r"^\[\^([^\]\n]+)\]:\s*(\S.*?)\s*$", re.MULTILINE)
FOOTREF = re.compile(r"(?<!\!)\[\^([^\]\n]+)\]")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
INLINE = re.compile(r"`[^`\n]*`")
SYSTEM = frozenset(
    map(
        Path,
        (
            "AGENTS.md",
            "BOOTSTRAP.md",
            "CLAUDE.md",
            "HOME.md",
            "MIGRATIONS.md",
            "README.md",
            "SECURITY.md",
            "SPEC.md",
            "START-HERE.md",
        ),
    )
)
RESERVED = frozenset({"Journal", "Template", "System"})
SECRETS = (
    re.compile(
        r"(?i)\b(?:api[_-]?key|secret|access[_-]?token|refresh[_-]?token|private[_-]?key|password)\s*[:=]\s*['\"]?[^\s'\"]{8,}"
    ),
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+\S+"),
    # Well-known provider token shapes; each is specific enough to avoid prose false positives.
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(
        r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"
    ),  # GitHub
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),  # Slack
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),  # Google API key
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{24,}\b"),  # OpenAI / Anthropic
    re.compile(r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}\b"),  # Stripe
    re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
    ),  # JWT
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: Path
    message: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    issues: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues


class BrainValidationError(ValueError):
    def __init__(self, issues: Sequence[ValidationIssue]) -> None:
        self.issues = tuple(issues)
        super().__init__(f"brain has {len(issues)} validation issue(s)")


@dataclass(frozen=True, slots=True)
class IndexResult:
    path: Path
    content: str
    changed: bool


@dataclass(frozen=True, slots=True)
class Inspection:
    groups: tuple[tuple[str, int], ...]
    types: tuple[tuple[str, str], ...]
    follow_ups: tuple[Path, ...]
    indexes_fresh: bool
    inbox: tuple[Path, ...] = ()
    inbox_folders: tuple[InboxFolder, ...] = ()


@dataclass(frozen=True, slots=True)
class InboxFolder:
    """A cheap survey of one top-level inbox folder, for planning triage passes."""

    folder: str
    items: int
    kinds: tuple[tuple[str, int], ...]
    text_chars: int
    oldest: str
    newest: str


KINDS: dict[str, str] = {
    **dict.fromkeys((".md", ".markdown", ".txt", ".text", ".rtf"), "text"),
    ".pdf": "pdf",
    **dict.fromkeys(
        (
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".heic",
            ".heif",
            ".tif",
            ".tiff",
            ".bmp",
            ".svg",
        ),
        "image",
    ),
    **dict.fromkeys(
        (".m4a", ".mp3", ".wav", ".aac", ".ogg", ".flac", ".opus"), "audio"
    ),
    **dict.fromkeys((".mp4", ".mov", ".mkv", ".webm", ".avi"), "video"),
    **dict.fromkeys(
        (".csv", ".tsv", ".json", ".xlsx", ".xls", ".numbers", ".yaml", ".yml"), "data"
    ),
    **dict.fromkeys(
        (".docx", ".doc", ".pages", ".pptx", ".ppt", ".key", ".odt"), "office"
    ),
    **dict.fromkeys((".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"), "archive"),
    **dict.fromkeys((".eml", ".msg"), "email"),
}
TEXT_KINDS = frozenset({"text", "data", "email"})


def item_kind(path: Path) -> str:
    """Coarse kind of an inbox item, by extension."""
    return KINDS.get(path.suffix.lower(), path.suffix.lower().lstrip(".") or "other")


def inbox_folders(root: Path) -> tuple[InboxFolder, ...]:
    """Summarize pending inbox items by top-level folder: counts, kinds, text size, dates."""
    groups: dict[str, list[Path]] = {}
    inbox = root / "inbox"
    for path, _ in _inbox_entries(root):
        relative = path.relative_to(inbox)
        groups.setdefault(
            relative.parts[0] if len(relative.parts) > 1 else "", []
        ).append(path)
    summaries: list[InboxFolder] = []
    for folder in sorted(groups, key=lambda name: (name != "", name)):
        paths = groups[folder]
        kinds = Counter(item_kind(path) for path in paths)
        chars = 0
        for path in paths:
            if item_kind(path) in TEXT_KINDS:
                try:
                    chars += len(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
        local_tz = datetime.now().astimezone().tzinfo
        days = [
            datetime.fromtimestamp(path.stat().st_mtime, tz=local_tz).date().isoformat()
            for path in paths
        ]
        summaries.append(
            InboxFolder(
                folder,
                len(paths),
                tuple(sorted(kinds.items(), key=lambda item: (-item[1], item[0]))),
                chars,
                min(days),
                max(days),
            )
        )
    return tuple(summaries)


def _now() -> str:
    """Local time with an explicit offset, measured now."""
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _resources() -> Traversable:
    try:
        return resources.files("portable_brain.resources")
    except ModuleNotFoundError as error:
        raise ManifestError("package resources are unavailable") from error


def _copy(source: Traversable, destination: Path) -> None:
    if not source.is_dir():
        raise ManifestError(f"package resource is not a directory: {source.name}")
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            _copy(child, target)
        elif child.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(child.read_bytes())


def _yaml(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            dict(value), allow_unicode=True, default_flow_style=False, sort_keys=False
        ),
        encoding="utf-8",
    )


def _template_name(name: str) -> str:
    return (
        "-".join(
            item.lower()
            for item in re.findall(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+", name)
        )
        + ".md"
    )


def _journal(day: str, actor: str) -> str:
    time = (
        "HH:MM"
        if day == "YYYY-MM-DD"
        else datetime.now().astimezone().strftime("%H:%M")
    )
    return f"# {day}\n\n## {time} — Topic\n\n`actor: {actor}`\n\nWhat changed, why, and links to the concepts that own current state and follow-ups."


def _template(name: str, definition: Mapping[str, Any], actor: str) -> str:
    body = (
        _journal("YYYY-MM-DD", actor)
        if name == "Journal"
        else "\n".join(
            [
                "# Title",
                "",
                "Describe this note before filling its sections.",
                "",
                *[f"## {section}\n" for section in definition["sections"]],
            ]
        )
    )
    description = (
        "Describe the intended use of the daily journal."
        if name == "Journal"
        else "Describe the intended use of this template."
    )
    return dump_frontmatter(
        {"type": "Template", "title": f"{name} template", "description": description},
        body,
    )


def _type_path(root: Path, manifest: Mapping[str, Any], name: str) -> Path:
    return root / type_directory(manifest, name)


def init_brain(
    target: str | Path,
    *,
    domains: Sequence[str] = (),
    adapters: Sequence[str] = (),
    actor: str | None = None,
    include_work: bool = False,
    profile: str | None = None,
) -> Path:
    if profile is not None:
        if domains:
            raise ManifestError("use --domains instead of --profile")
        domains = () if profile == "core" else (profile,)
    for adapter in adapters:
        if adapter not in SUPPORTED_ADAPTERS:
            raise ManifestError(f"unsupported adapter: {adapter}")
    root = Path(target).expanduser()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ManifestError("refusing to initialize a non-empty target")
    manifest = load_profiles(domains, include_work=include_work)
    identity = actor or f"human:{getpass.getuser()}"
    if not is_valid_actor(identity):
        raise ManifestError("actor must be an OKF actor")
    manifest["default_actor"] = identity
    if adapters:
        manifest["adapters"] = sorted(set(manifest["adapters"]) | set(adapters))
    root.mkdir(parents=True, exist_ok=True)
    _copy(_resources().joinpath("scaffold"), root)
    _yaml(root / MANIFEST_RELATIVE_PATH, manifest)
    for group in manifest["groups"]:
        (root / group).mkdir(parents=True, exist_ok=True)
    (root / "assets").mkdir(exist_ok=True)
    (root / "assets" / ".gitkeep").touch()
    for name, definition in manifest["types"].items():
        _type_path(root, manifest, name).mkdir(parents=True, exist_ok=True)
    templates = root / "templates"
    templates.mkdir(exist_ok=True)
    for name, definition in manifest["types"].items():
        (templates / _template_name(name)).write_text(
            _template(name, definition, identity), encoding="utf-8"
        )
    for adapter in adapters:
        _copy(_resources().joinpath(adapter), root)
        if adapter == "obsidian" and include_work:
            _copy(_resources().joinpath("obsidian_work"), root)
    hooks = root / ".claude" / "hooks"
    if hooks.is_dir():
        for script in hooks.glob("*.sh"):
            script.chmod(script.stat().st_mode | 0o111)
    empty_groups: dict[str, list[tuple[Path, Mapping[str, Any]]]] = {
        name: [] for name in manifest["groups"]
    }
    for group in manifest["groups"]:
        (root / group / "index.md").write_text(
            _group_index(root, group, empty_groups[group]), encoding="utf-8"
        )
    (root / "index.md").write_text(
        _root_index(manifest, empty_groups), encoding="utf-8"
    )
    build_index(root)
    return root


def new_note(
    target: str | Path,
    type_name: str,
    slug: str,
    *,
    title: str,
    actor: str | None = None,
) -> Path:
    manifest = load_manifest(target)
    if not SLUG.fullmatch(slug):
        raise ManifestError("slug must be kebab-case")
    if (
        not isinstance(title, str)
        or not title.strip()
        or "\n" in title
        or "\r" in title
    ):
        raise ManifestError("title must be non-empty and single-line")
    definition = manifest["types"].get(type_name)
    if not isinstance(definition, Mapping):
        raise ManifestError(f"unknown type: {type_name}")
    identity = actor or manifest.get("default_actor")
    if not isinstance(identity, str) or not is_valid_actor(identity):
        raise ManifestError("actor must be an OKF actor")
    if definition["group"] == "journal":
        if type_name != "Journal" or not DAY.fullmatch(slug):
            raise ManifestError(
                "Journal entries require type Journal and a YYYY-MM-DD slug"
            )
        try:
            date.fromisoformat(slug)
        except ValueError as error:
            raise ManifestError("Journal slug must be a calendar date") from error
    destination = _type_path(Path(target), manifest, type_name) / f"{slug}.md"
    if destination.exists() or destination.is_symlink():
        raise ManifestError(f"refusing to overwrite existing note: {destination}")
    metadata: dict[str, Any] = {
        "type": type_name,
        "title": title,
        "status": "draft",
        "tags": [],
        "description": "",
        "generated": {"by": identity, "at": _now()},
    }
    if definition["workflow"]:
        metadata.update(
            {
                "pb_work_state": manifest["workflow"]["initial_state"],
                "pb_owner": identity,
            }
        )
    body = (
        _journal(slug, identity)
        if type_name == "Journal"
        else "\n".join(
            [
                f"# {title}",
                "",
                *[f"## {section}\n" for section in definition["sections"]],
            ]
        )
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(dump_frontmatter(metadata, body), encoding="utf-8")
    return destination


def _files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.md"), key=lambda item: item.as_posix()):
        if _visible(path.relative_to(root)):
            yield path


def _linkable(text: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        match = FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            fence = marker if fence is None else None if fence == marker else fence
            output.append("\n" if line.endswith("\n") else "")
        elif fence is None:
            output.append(INLINE.sub("", line))
        else:
            output.append("\n" if line.endswith("\n") else "")
    return "".join(output)


def _destination(raw: str, path: Path, root: Path) -> Path | None:
    parsed = urlsplit(unquote(raw))
    if parsed.scheme or parsed.netloc or raw.startswith(("#", "//")) or not parsed.path:
        return None
    candidate = (
        root / parsed.path.lstrip("/")
        if parsed.path.startswith("/")
        else path.parent / parsed.path
    )
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return Path("__outside__")
    return candidate


def _relationships(path: Path, text: str, root: Path, adapters: set[str]) -> list[str]:
    issues: list[str] = []
    relative = path.relative_to(root)
    for token in WIKI.findall(text):
        if (
            relative == Path("HOME.md")
            and "obsidian" in adapters
            and re.fullmatch(r"!\[\[views/[^/\]]+\.base\]\]", token)
        ):
            continue
        issues.append(f"Obsidian wikilink is not portable: {token}")
    for match in LINK.finditer(text):
        raw = match.group(1) or match.group(2)
        if not raw:
            continue
        if "\\" in raw:
            issues.append(f"internal Markdown link must use forward slashes: {raw}")
            continue
        candidate = _destination(raw, path, root)
        if candidate == Path("__outside__"):
            issues.append(f"internal Markdown link escapes the brain: {raw}")
        elif candidate is not None and not candidate.exists():
            issues.append(
                f"broken internal Markdown link: {raw} (target {posixpath.normpath(str(candidate.relative_to(root)))} does not exist)"
            )
    return issues


def _offset(value: object) -> bool:
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(value)
            if isinstance(value, str)
            else None
        )
    except ValueError:
        return False
    return (
        isinstance(parsed, datetime)
        and parsed.tzinfo is not None
        and parsed.utcoffset() is not None
    )


def _event(value: object, label: str, issues: list[str]) -> None:
    if not isinstance(value, Mapping):
        issues.append(f"{label} must be a mapping")
        return
    if not is_valid_actor(value.get("by")):
        issues.append(f"{label}.by must be an OKF actor")
    if not _offset(value.get("at")):
        issues.append(
            f"{label}.at must be an ISO-8601 timestamp with an explicit offset"
        )


def _metadata(data: Mapping[str, Any], issues: list[str]) -> None:
    title = data.get("title")
    if (
        not isinstance(title, str)
        or not title.strip()
        or "\n" in title
        or "\r" in title
    ):
        issues.append("frontmatter field 'title' must be non-empty and single-line")
    if "status" in data and data.get("status") not in {"draft", "stable", "deprecated"}:
        issues.append("frontmatter field 'status' must be draft, stable, or deprecated")
    if "tags" in data and (
        not isinstance(data.get("tags"), list)
        or any(not isinstance(item, str) for item in data["tags"])
    ):
        issues.append("frontmatter field 'tags' must be a list of strings")
    if "description" in data and (
        not isinstance(data["description"], str)
        or "\n" in data["description"]
        or "\r" in data["description"]
    ):
        issues.append("description must be a single-line string")
    if "generated" in data:
        _event(data["generated"], "generated", issues)
    if "verified" in data:
        value = data["verified"]
        if isinstance(value, Mapping):
            _event(value, "verified", issues)
        elif isinstance(value, list):
            for index, event in enumerate(value):
                _event(event, f"verified[{index}]", issues)
        else:
            issues.append("verified must be a mapping or list of mappings")
    if "sources" in data and (
        not isinstance(data["sources"], list)
        or any(
            not isinstance(item, Mapping)
            or (
                not item.get("id")
                and (
                    not isinstance(item.get("resource"), str)
                    or not item["resource"].strip()
                )
            )
            for item in data["sources"]
        )
    ):
        issues.append("sources entries require a resource or id")


def _group(relative: Path, manifest: Mapping[str, Any]) -> str | None:
    return (
        relative.parts[0]
        if relative.parts and relative.parts[0] in manifest["groups"]
        else None
    )


def _journal_issues(
    path: Path, body: str, data: Mapping[str, Any], issues: list[str]
) -> None:
    if not DAY.fullmatch(path.stem):
        issues.append("journal filename must be YYYY-MM-DD.md")
    else:
        try:
            date.fromisoformat(path.stem)
        except ValueError:
            issues.append("journal filename must be a calendar date")
    if data.get("title") != path.stem:
        issues.append("journal title must equal its date filename")
    h1 = H1.search(body)
    if h1 is None or h1.group(1) != path.stem:
        issues.append("journal must begin with an H1 matching its date")
    if CHECK.search(body):
        issues.append(
            "journal is append-only narrative and must not contain checkboxes"
        )
    sessions = list(SESSION.finditer(body))
    if not sessions:
        issues.append("journal requires at least one '## HH:MM — Topic' session block")
    for index, session in enumerate(sessions):
        block = body[
            session.end() : sessions[index + 1].start()
            if index + 1 < len(sessions)
            else len(body)
        ].strip()
        if "actor:" not in block or not any(
            line.strip() and "actor:" not in line for line in block.splitlines()
        ):
            issues.append("each journal session requires an actor line and narrative")


def _footnotes(
    path: Path, root: Path, body: str, data: Mapping[str, Any], issues: list[str]
) -> None:
    raw_sources = data.get("sources", [])
    sources = raw_sources if isinstance(raw_sources, list) else []
    definition_matches = FOOTDEF.findall(body)
    definitions = dict(definition_matches)
    if len(definitions) != len(definition_matches):
        issues.append("footnote definitions must be unique")
    references = set(FOOTREF.findall(body))
    declared = {
        str(source.get("id"))
        for source in sources
        if isinstance(source, Mapping) and source.get("id") is not None
    }
    if len(
        [
            source
            for source in sources
            if isinstance(source, Mapping) and source.get("id") is not None
        ]
    ) != len(declared):
        issues.append("sources must use unique ids")
    if len(declared) != len(definition_matches) and definition_matches:
        issues.append(
            "referenced source definitions must match declared sources one-for-one"
        )
    missing = references - set(definitions)
    unjoined = set(definitions) - declared
    undjoined = declared - set(definitions) if definition_matches else set()
    if missing:
        issues.append(
            f"footnote reference(s) lack definitions: {', '.join(sorted(missing))}"
        )
    if not definition_matches and declared:
        issues.append("declared source ids require matching footnote definitions")
    if unjoined:
        issues.append(
            f"footnote definitions are not declared source ids: {', '.join(sorted(unjoined))}"
        )
    if undjoined:
        issues.append(
            f"source ids must have matching footnote definitions: {', '.join(sorted(undjoined))}"
        )
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        raw = source.get("resource")
        if not isinstance(raw, str) or not raw.strip():
            continue
        candidate = _destination(raw, path, root)
        if candidate == Path("__outside__"):
            issues.append(f"source resource escapes the brain: {raw}")
        elif candidate is not None and not candidate.exists():
            issues.append(f"source resource does not resolve inside the brain: {raw}")


def _section_issues(body: str, sections: Sequence[str], issues: list[str]) -> None:
    headings = [
        match.group(1).strip()
        for match in re.finditer(r"^## (.+?)\s*$", body, re.MULTILINE)
    ]
    cursor = 0
    for section in sections:
        try:
            cursor = headings.index(section, cursor) + 1
        except ValueError:
            issues.append(
                f"configured section is missing or out of order: ## {section}"
            )


def _blocker_issues(
    path: Path, root: Path, blockers: object, issues: list[str]
) -> None:
    if not isinstance(blockers, list):
        return
    for blocker in blockers:
        if not isinstance(blocker, str) or not blocker.strip():
            continue
        match = LINK.fullmatch(blocker.strip())
        if match is None:
            issues.append("each pb_blocked_on item must be one standard Markdown link")
            continue
        raw = match.group(1) or match.group(2)
        candidate = _destination(raw, path, root) if raw else None
        if candidate == Path("__outside__"):
            issues.append(f"pb_blocked_on link escapes the brain: {raw}")
        elif candidate is None or not candidate.exists():
            issues.append(
                f"pb_blocked_on link does not resolve inside the brain: {raw}"
            )


def _validate_okf(path: Path, root: Path) -> list[str]:
    relative = path.relative_to(root)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["Markdown file is not valid UTF-8"]
    try:
        data, _ = parse_frontmatter(text)
    except FrontmatterError as error:
        return [str(error)]
    if relative == Path("index.md") and data.get("okf_version") == "0.2":
        return []
    kind = data.get("type")
    if not isinstance(kind, str) or not kind.strip():
        return ["frontmatter field 'type' must be a non-empty string"]
    issues: list[str] = []
    _metadata(data, issues)
    return issues


def _generated_index(relative: Path, manifest: Mapping[str, Any]) -> bool:
    """Root index.md and <group>/index.md are generated, derived material."""
    return relative == Path("index.md") or (
        relative.name == "index.md"
        and len(relative.parts) == 2
        and relative.parts[0] in manifest["groups"]
    )


def _stale_links(path: Path, root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Link problems in a generated index mean it is stale, not invalid; the remedy is regeneration."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return []
    return [
        f"{message}; the generated index is stale, run portable-brain index"
        for message in _relationships(
            path, _linkable(text), root, set(manifest["adapters"])
        )
    ]


def _validate(path: Path, root: Path, manifest: Mapping[str, Any]) -> list[str]:
    relative = path.relative_to(root)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["Markdown file is not valid UTF-8"]
    try:
        data, body = parse_frontmatter(text)
    except FrontmatterError as error:
        return [str(error)]
    issues: list[str] = (
        []
        if _generated_index(relative, manifest)
        else _relationships(path, _linkable(text), root, set(manifest["adapters"]))
    )
    if any(pattern.search(text) for pattern in SECRETS):
        issues.append("portable validation rejects probable secure material")
    if relative == Path("index.md"):
        if (
            set(data) != {"okf_version"}
            or data.get("okf_version") != "0.2"
            or "<!-- portable-brain:index -->" not in text
        ):
            issues.append("index.md must be the generated portable-brain root index")
        return issues
    if (
        relative.name == "index.md"
        and len(relative.parts) == 2
        and relative.parts[0] in manifest["groups"]
    ):
        if data.get("type") != "System" or "<!-- portable-brain:index -->" not in text:
            issues.append(
                "group index must be generated portable-brain System document"
            )
        return issues
    if relative in SYSTEM:
        if not isinstance(data.get("type"), str) or not str(data.get("type")).strip():
            issues.append("frontmatter field 'type' must be a non-empty string")
        _metadata(data, issues)
        return issues
    if relative.parts and relative.parts[0] == "templates":
        if data.get("type") != "Template":
            issues.append("templates must declare type: Template")
        _metadata(data, issues)
        return issues
    kind = data.get("type")
    if not isinstance(kind, str) or not kind.strip():
        return [*issues, "frontmatter field 'type' must be a non-empty string"]
    group = _group(relative, manifest)
    # work/archive/ mirrors work/: an archived document keeps its type folder beneath it.
    routed = (
        Path(relative.parts[0], *relative.parts[2:])
        if group == "work"
        and len(relative.parts) > 2
        and relative.parts[1] == "archive"
        else relative
    )
    matching_types = {
        name
        for name, definition in manifest["types"].items()
        if definition["group"] == group
        and (
            definition["folder"] == "."
            or routed.parent == type_directory(manifest, name)
            or type_directory(manifest, name) in routed.parents
        )
    }
    if group is None:
        return [*issues, "Markdown document is outside configured groups"]
    if group == "journal":
        if kind != "Journal":
            issues.append("journal accepts only type: Journal")
        _journal_issues(path, body, data, issues)
    elif group in {"sources", "work"} and kind not in matching_types:
        issues.append(f"{group} is strict: path must use its configured type")
    elif group == "wiki" and kind in {"Journal", "Template", "System", "Source"}:
        issues.append("wiki group cannot use a reserved type")
    if group != "journal" and not SLUG.fullmatch(path.stem):
        issues.append("group document filename must be a kebab-case slug")
    _metadata(data, issues)
    h1 = H1.search(body)
    if (
        group in {"wiki", "work"}
        and data.get("status") == "stable"
        and (
            not isinstance(data.get("description"), str)
            or not str(data.get("description")).strip()
        )
    ):
        issues.append("stable wiki and work documents require a non-empty description")
    if group != "journal" and h1 is None:
        issues.append("concept document must contain an H1")
    if h1 is not None and group != "journal" and h1.group(1) != data.get("title"):
        issues.append("document H1 must exactly match frontmatter title")
    if group in {"sources", "wiki", "journal"}:
        _footnotes(path, Path(root), body, data, issues)
    definition = manifest["types"].get(kind)
    if isinstance(definition, Mapping) and definition.get("group") == group:
        _section_issues(body, definition["sections"], issues)
    fields = {key for key in data if key.startswith("pb_")}
    if group != "work" and fields:
        issues.append("only configured work types may declare pb_* fields")
    if group == "work":
        state = data.get("pb_work_state")
        if not isinstance(state, str) or state not in manifest["workflow"]["states"]:
            issues.append("work types require pb_work_state from workflow.states")
        if not is_valid_actor(data.get("pb_owner")):
            issues.append("work types require pb_owner as an OKF actor")
        blockers = data.get("pb_blocked_on")
        requires_blockers = manifest["workflow"]["requires_blocked_on"]
        if state in requires_blockers and (
            not isinstance(blockers, list)
            or not blockers
            or any(not isinstance(item, str) or not item.strip() for item in blockers)
        ):
            issues.append("work state requires non-empty pb_blocked_on")
        elif (
            state not in requires_blockers
            and blockers is not None
            and (
                not isinstance(blockers, list)
                or not blockers
                or any(
                    not isinstance(item, str) or not item.strip() for item in blockers
                )
            )
        ):
            issues.append("pb_blocked_on must be a non-empty list of blockers")
        _blocker_issues(path, root, blockers, issues)
        if state in manifest["workflow"]["closed_states"] and not _offset(
            data.get("pb_closed_on")
        ):
            issues.append("closed work requires pb_closed_on with an explicit offset")
    return issues


def validate_brain(target: str | Path, *, mode: str = "portable") -> ValidationResult:
    if mode not in {"portable", "okf"}:
        raise ManifestError("validation mode must be portable or okf")
    root = Path(target)
    if not root.is_dir():
        raise ManifestError(f"validation target is not a directory: {root}")
    manifest = load_manifest(root) if mode == "portable" else None
    issues: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    for path in _files(root):
        relative = path.relative_to(root)
        if (
            manifest is not None
            and _group(relative, manifest) == "inbox"
            and relative != Path("inbox/index.md")
        ):
            warnings.extend(
                ValidationIssue(relative, message)
                for message in _inbox_warnings(path, root, manifest)
            )
        else:
            issues.extend(
                ValidationIssue(relative, message)
                for message in (
                    _validate(path, root, manifest)
                    if manifest is not None
                    else _validate_okf(path, root)
                )
            )
            if manifest is not None and _generated_index(relative, manifest):
                warnings.extend(
                    ValidationIssue(relative, message)
                    for message in _stale_links(path, root, manifest)
                )
            if (
                manifest is not None
                and _group(relative, manifest) == "journal"
                and relative.name != "index.md"
            ):
                warnings.extend(
                    ValidationIssue(relative, message)
                    for message in _journal_time_warnings(path)
                )
    return ValidationResult(tuple(issues), tuple(warnings))


def _visible(relative: Path) -> bool:
    return not any(part.startswith(".") for part in relative.parts)


def _inbox_metadata(path: Path) -> Mapping[str, Any]:
    """Best-effort navigation label for an untriaged inbox item; never a shape requirement."""
    if path.suffix.lower() != ".md":
        return {"title": path.name}
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {"title": path.name}
    try:
        data, body = parse_frontmatter(text)
    except FrontmatterError:
        data, body = {}, text
    title = data.get("title")
    h1 = H1.search(body)
    label = (
        title.strip()
        if isinstance(title, str) and title.strip() and "\n" not in title
        else h1.group(1)
        if h1
        else path.name
    )
    return {**data, "title": label}


def _inbox_entries(root: Path) -> list[tuple[Path, Mapping[str, Any]]]:
    """Every pending inbox item of any file type, excluding the generated index and dotfiles."""
    inbox = root / "inbox"
    if not inbox.is_dir():
        return []
    return [
        (path, _inbox_metadata(path))
        for path in sorted(inbox.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
        and _visible(path.relative_to(inbox))
        and path.relative_to(inbox) != Path("index.md")
    ]


HEADING_TIME = re.compile(r"^## (\d\d:\d\d) — ", re.MULTILINE)


def _journal_time_warnings(path: Path) -> list[str]:
    """Journal headings must be measured: warn when they run backwards or past the clock."""
    try:
        _, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, FrontmatterError):
        return []
    times = HEADING_TIME.findall(body)
    warnings: list[str] = []
    for earlier, later in zip(times, times[1:]):
        if later < earlier:
            warnings.append(
                f"journal headings are not in chronological order: {earlier} then {later}; "
                "times must be measured, not estimated"
            )
            break
    now = datetime.now().astimezone()
    if path.stem == now.date().isoformat():
        clock = now.strftime("%H:%M")
        future = [time for time in times if time > clock]
        if future:
            warnings.append(
                f"journal heading {future[0]} is later than now ({clock}); "
                "times must be measured, not estimated"
            )
    return warnings


def _inbox_warnings(path: Path, root: Path, manifest: Mapping[str, Any]) -> list[str]:
    """Untriaged inbox Markdown has no required shape; only carry-forward hazards are reported, as warnings."""
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["inbox Markdown is not valid UTF-8 text"]
    warnings = _relationships(path, _linkable(text), root, set(manifest["adapters"]))
    if any(pattern.search(text) for pattern in SECRETS):
        warnings.append(
            "inbox item contains probable secure material; redact or discard it before triage moves it onward"
        )
    return warnings


def _grouped(
    root: Path, manifest: Mapping[str, Any]
) -> dict[str, list[tuple[Path, Mapping[str, Any]]]]:
    result: dict[str, list[tuple[Path, Mapping[str, Any]]]] = {
        name: [] for name in manifest["groups"]
    }
    for path in _files(root):
        relative = path.relative_to(root)
        if relative.name == "index.md" or relative.parts[:1] == ("templates",):
            continue
        group = _group(relative, manifest)
        if group == "inbox":
            continue
        if group:
            try:
                data, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, FrontmatterError):
                continue
            result[group].append((path, data))
    result["inbox"] = _inbox_entries(root)
    return result


def _label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _group_index(
    root: Path, group: str, entries: Sequence[tuple[Path, Mapping[str, Any]]]
) -> str:
    lines = [
        "---",
        "type: System",
        f"title: {group.title()} index",
        "status: stable",
        "tags: []",
        "---",
        "<!-- portable-brain:index -->",
        "",
        f"# {group.title()} index",
        "",
    ]
    tree: dict[str, Any] = {"entries": [], "children": {}}
    for path, data in entries:
        relative = path.relative_to(Path(root) / group)
        node = tree
        for part in relative.parent.parts:
            node = node["children"].setdefault(part, {"entries": [], "children": {}})
        node["entries"].append((path, data))

    def render(
        node: Mapping[str, Any], depth: int, parents: tuple[str, ...] = ()
    ) -> None:
        ordered = sorted(
            node["entries"],
            key=lambda item: (
                (str(item[1].get("title") or "")).casefold(),
                item[0].as_posix(),
            ),
            reverse=group == "journal",
        )
        for path, data in ordered:
            summary = data.get("description")
            entry = f"- [{_label(str(data.get('title') or path.stem))}]({path.relative_to(Path(root) / group).as_posix()})"
            lines.append(
                f"{entry} — {_label(summary)}"
                if isinstance(summary, str) and summary.strip()
                else entry
            )
        if ordered and node["children"]:
            lines.append("")
        children = node["children"]
        for index, name in enumerate(sorted(children, key=str.casefold)):
            path_parts = (*parents, name)
            level = min(depth + 2, 6)
            label = (
                name.replace("-", " ").title()
                if level < 6
                else " / ".join(part.replace("-", " ").title() for part in path_parts)
            )
            lines.extend((f"{'#' * level} {label}", ""))
            render(children[name], depth + 1, path_parts)
            if index + 1 < len(children):
                lines.append("")

    render(tree, 0)
    return "\n".join(lines).rstrip() + "\n"


def _root_index(
    manifest: Mapping[str, Any], grouped: Mapping[str, Sequence[object]]
) -> str:
    lines = [
        "---",
        'okf_version: "0.2"',
        "---",
        "<!-- portable-brain:index -->",
        "",
        "# Brain index",
        "",
    ]
    for name in manifest["groups"]:
        count = len(grouped[name])
        noun = "item" if name == "inbox" else "document"
        lines.append(
            f"- [{name.title()}]({name}/index.md) — {count} {noun}{'s' if count != 1 else ''}"
        )
    return "\n".join(lines).rstrip() + "\n"


def build_index(target: str | Path, *, check: bool = False) -> IndexResult:
    root = Path(target)
    manifest = load_manifest(root)
    result = validate_brain(root)
    if not result.valid:
        raise BrainValidationError(result.issues)
    grouped = _grouped(root, manifest)
    root_content = _root_index(manifest, grouped)
    changed = False
    for group, entries in grouped.items():
        path = root / group / "index.md"
        content = _group_index(root, group, entries)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        changed = changed or current != content
        if current != content and not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    path = root / "index.md"
    current = path.read_text(encoding="utf-8") if path.exists() else None
    changed = changed or current != root_content
    if current != root_content and not check:
        path.write_text(root_content, encoding="utf-8")
    return IndexResult(path, root_content, changed)


def _work_type_directories(manifest: Mapping[str, Any]) -> set[Path]:
    """Work-relative directories owned by configured work types; never archive targets."""
    return {
        Path(definition["folder"])
        for definition in manifest["types"].values()
        if definition["group"] == "work" and definition["folder"] != "."
    }


def archive_brain(
    target: str | Path, item: str, confirmation: str | None = None
) -> Path | None:
    """Move one work document or directory beneath work/archive/, mirroring its path."""
    relative = Path(item.removesuffix(".md"))
    if not relative.parts or any(not SLUG.fullmatch(part) for part in relative.parts):
        raise ManifestError(
            "archive item must be a work-relative path of kebab-case segments"
        )
    if confirmation != "yes":
        raise ManifestError("archive requires literal confirmation: yes")
    manifest = load_manifest(target)
    if "work" not in manifest["groups"]:
        raise ManifestError("brain has no work group")
    if relative.parts[0] == "archive":
        raise ManifestError("item is already under work/archive")
    for type_dir in _work_type_directories(manifest):
        if relative == type_dir or relative in type_dir.parents:
            raise ManifestError(
                f"refusing to archive configured type folder {type_dir.as_posix()!r}; "
                "archive the documents inside it instead"
            )
    root = Path(target)
    directory = root / "work" / relative
    document = root / "work" / f"{relative.as_posix()}.md"
    candidates = [
        path
        for path in (directory, document)
        if path.exists() and not path.is_symlink()
    ]
    if not candidates:
        raise ManifestError(f"work target does not exist: {item}")
    if len(candidates) != 1:
        raise ManifestError("refusing ambiguous archive target")
    source = candidates[0]
    if source.is_dir():
        destination = root / "work" / "archive" / relative
    elif source.is_file():
        destination = root / "work" / "archive" / f"{relative.as_posix()}.md"
    else:
        raise ManifestError("archive target must be a regular work file or directory")
    if destination.exists() or destination.is_symlink():
        raise ManifestError(f"refusing to overwrite archived work: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))
    return destination


def inspect_brain(target: str | Path) -> Inspection:
    root = Path(target)
    manifest = load_manifest(root)
    grouped = _grouped(root, manifest)
    assets = root / "assets"
    grouped["assets"] = (
        [
            (path, {})
            for path in sorted(assets.rglob("*"), key=lambda item: item.as_posix())
            if path.is_file() and _visible(path.relative_to(assets))
        ]
        if assets.is_dir()
        else []
    )
    pending = tuple(path.relative_to(root) for path, _ in grouped["inbox"])
    follows = tuple(
        sorted(
            path.relative_to(root)
            for path, data in grouped.get("work", [])
            if data.get("pb_work_state") not in manifest["workflow"]["closed_states"]
        )
    )
    return Inspection(
        tuple((name, len(entries)) for name, entries in grouped.items()),
        tuple(
            (name, definition["group"])
            for name, definition in manifest["types"].items()
        ),
        follows,
        not build_index(root, check=True).changed,
        pending,
        inbox_folders(root),
    )


DEFAULT_SECTIONS: dict[str, tuple[str, ...]] = {
    "wiki": ("Summary", "Notes", "References"),
    "sources": ("Citation", "Source material", "Notes"),
    "work": ("Summary", "Current state", "Follow-ups", "Log", "References"),
}


def _folder_slug(name: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", name.lower())) or "items"


def _write_manifest(root: Path, manifest: Mapping[str, Any]) -> None:
    _yaml(root / MANIFEST_RELATIVE_PATH, manifest)


def _materialize_type(root: Path, manifest: Mapping[str, Any], name: str) -> Path:
    """Create a configured type's folder and template."""
    definition = manifest["types"][name]
    _type_path(root, manifest, name).mkdir(parents=True, exist_ok=True)
    templates = root / "templates"
    templates.mkdir(exist_ok=True)
    actor = manifest.get("default_actor") or f"human:{getpass.getuser()}"
    template = templates / _template_name(name)
    template.write_text(_template(name, definition, actor), encoding="utf-8")
    return template


def add_type(
    target: str | Path,
    name: str,
    *,
    group: str,
    folder: str | None = None,
    sections: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Add one configured type: manifest entry, folder, and template."""
    root = Path(target)
    manifest = load_manifest(root)
    if not isinstance(name, str) or not name.strip() or "\n" in name or "\r" in name:
        raise ManifestError("type name must be a non-empty single line")
    name = name.strip()
    if name in manifest["types"]:
        raise ManifestError(f"type already exists: {name}")
    if name in RESERVED:
        raise ManifestError(f"{name} is a reserved type")
    if group == "journal":
        raise ManifestError("journal accepts only the Journal type")
    if group == "inbox":
        raise ManifestError("inbox has no configured types; anything may land there")
    if group not in manifest["groups"]:
        hint = "; run portable-brain enable-work first" if group == "work" else ""
        raise ManifestError(f"group is not configured: {group}{hint}")
    definition = {
        "group": group,
        "folder": folder if folder is not None else _folder_slug(name),
        "workflow": group == "work",
        "sections": list(sections)
        if sections is not None
        else list(DEFAULT_SECTIONS[group]),
    }
    candidate = deepcopy(dict(manifest))
    candidate["types"] = {**manifest["types"], name: definition}
    manifest = validate_manifest(candidate)
    _write_manifest(root, manifest)
    _materialize_type(root, manifest, name)
    return dict(manifest["types"][name])


def remove_type(target: str | Path, name: str) -> None:
    """Remove a configured type that no document uses; keeps the folder if not empty."""
    root = Path(target)
    manifest = load_manifest(root)
    if name not in manifest["types"]:
        raise ManifestError(f"unknown type: {name}")
    if name == "Journal":
        raise ManifestError("Journal is required by every brain")
    used = sorted(
        path.relative_to(root)
        for group, entries in _grouped(root, manifest).items()
        if group != "inbox"
        for path, data in entries
        if data.get("type") == name
    )
    if used:
        raise ManifestError(
            f"type {name} is used by {len(used)} document(s), e.g. {used[0]}; "
            "move or retype them first"
        )
    directory = _type_path(root, manifest, name)
    candidate = deepcopy(dict(manifest))
    candidate["types"] = {k: v for k, v in manifest["types"].items() if k != name}
    manifest = validate_manifest(candidate)
    _write_manifest(root, manifest)
    template = root / "templates" / _template_name(name)
    if template.exists():
        template.unlink()
    if directory.parent != root and directory.is_dir() and not any(directory.iterdir()):
        directory.rmdir()


def add_domain(target: str | Path, name: str) -> list[str]:
    """Enable a packaged domain overlay in an existing brain; returns the types added."""
    root = Path(target)
    manifest = load_manifest(root)
    if name in manifest["domains"]:
        raise ManifestError(f"domain is already enabled: {name}")
    overlay = domain_overlay(name)
    include_work = "work" in manifest["groups"]
    types = dict(manifest["types"])
    added: list[str] = []
    for type_name, raw in overlay.get("types", {}).items():
        if not isinstance(raw, Mapping):
            raise ManifestError(f"domain {name} has an invalid type {type_name}")
        if raw.get("group") == "work" and not include_work:
            continue
        if type_name in types:
            raise ManifestError(
                f"domain {name} defines type {type_name}, which already exists; "
                "remove it first"
            )
        types[type_name] = dict(raw)
        added.append(type_name)
    candidate = deepcopy(dict(manifest))
    candidate["types"] = types
    candidate["domains"] = [*manifest["domains"], name]
    manifest = validate_manifest(candidate)
    _write_manifest(root, manifest)
    for type_name in added:
        _materialize_type(root, manifest, type_name)
    return added


def enable_work(target: str | Path) -> list[str]:
    """Enable the strict work module in an existing brain; returns the types added."""
    root = Path(target)
    manifest = load_manifest(root)
    if "work" in manifest["groups"]:
        raise ManifestError("the work module is already enabled")
    result = validate_brain(root)
    if not result.valid:
        raise BrainValidationError(result.issues)
    work = work_overlay()
    groups = dict(manifest["groups"])
    groups["work"] = dict(work["groups"]["work"])
    types = dict(manifest["types"])
    added: list[str] = []
    overlays = [work.get("types", {})]
    overlays.extend(
        domain_overlay(domain).get("types", {}) for domain in manifest["domains"]
    )
    for overlay in overlays:
        for type_name, raw in overlay.items():
            if (
                isinstance(raw, Mapping)
                and raw.get("group") == "work"
                and type_name not in types
            ):
                types[type_name] = dict(raw)
                added.append(type_name)
    candidate = deepcopy(dict(manifest))
    candidate["groups"] = groups
    candidate["types"] = types
    candidate["modules"] = ["work"]
    manifest = validate_manifest(candidate)
    _write_manifest(root, manifest)
    (root / "work").mkdir(exist_ok=True)
    for type_name in added:
        _materialize_type(root, manifest, type_name)
    if "obsidian" in manifest["adapters"]:
        _copy(_resources().joinpath("obsidian_work"), root)
    build_index(root)
    return added
