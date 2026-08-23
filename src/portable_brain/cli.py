"""Command-line adapter for Portable Brain."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .core import (
    BrainValidationError,
    ValidationIssue,
    archive_brain,
    build_index,
    init_brain,
    inspect_brain,
    new_note,
    validate_brain,
)
from .frontmatter import FrontmatterError
from .manifest import (
    SUPPORTED_ADAPTERS,
    ManifestError,
    available_domains,
    load_manifest,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="portable-brain")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="initialize an empty portable brain")
    init.add_argument("target", metavar="TARGET", type=Path)
    init.add_argument("--domains", choices=available_domains(), nargs="*", default=[])
    init.add_argument("--work", action="store_true", help="enable strict work tracking")
    init.add_argument(
        "--adapter",
        dest="adapters",
        choices=sorted(SUPPORTED_ADAPTERS),
        nargs="*",
        default=[],
        help="optional adapters, e.g. --adapter obsidian claude",
    )
    init.add_argument("--actor")
    archive = commands.add_parser(
        "archive",
        help="move a work document or directory beneath work/archive/, mirroring its path",
    )
    archive.add_argument("target", metavar="TARGET", type=Path)
    archive.add_argument(
        "item",
        metavar="ITEM",
        help="work-relative path, e.g. kitchen-remodel or changes/add-logging",
    )
    archive.add_argument("yes", metavar="yes", help="type yes to confirm the archive")
    create = commands.add_parser("new", help="create a configured note")
    create.add_argument("target", metavar="TARGET", type=Path)
    create.add_argument("type_name", metavar="TYPE")
    create.add_argument("slug", metavar="SLUG")
    create.add_argument("--title", required=True)
    create.add_argument("--actor")
    validate = commands.add_parser("validate", help="validate brain documents")
    validate.add_argument("target", metavar="TARGET", type=Path)
    mode = validate.add_mutually_exclusive_group()
    mode.add_argument("--portable", action="store_const", const="portable", dest="mode")
    mode.add_argument("--okf", action="store_const", const="okf", dest="mode")
    validate.set_defaults(mode="portable")
    index = commands.add_parser("index", help="write or check deterministic indexes")
    index.add_argument("target", metavar="TARGET", type=Path)
    index.add_argument("--check", action="store_true")
    inspect = commands.add_parser(
        "inspect", help="show groups, types, follow-ups, and index freshness"
    )
    inspect.add_argument("target", metavar="TARGET", type=Path)
    return parser


def _issues(items: Sequence[ValidationIssue]) -> None:
    for item in items:
        print(f"{item.path}: {item.message}", file=sys.stderr)


def _warnings(items: Sequence[ValidationIssue]) -> None:
    for item in items:
        print(f"{item.path}: warning: {item.message}", file=sys.stderr)


def _inspection(target: Path) -> None:
    result = inspect_brain(target)
    print("groups:")
    for name, count in result.groups:
        print(f"  {name}: {count}")
    print("inbox (pending triage):")
    for path in result.inbox:
        print(f"  {path}")
    print("types:")
    for name, group in result.types:
        print(f"  {name}: {group}")
    manifest = load_manifest(target)
    if "work" in manifest["groups"]:
        print("work states:")
        for state in manifest["workflow"].get("states", {}):
            print(f"  {state}")
    print("follow-ups:")
    for path in result.follow_ups:
        print(f"  {path}")
    print(f"indexes: {'fresh' if result.indexes_fresh else 'stale'}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
        if arguments.command == "init":
            init_brain(
                arguments.target,
                domains=arguments.domains,
                adapters=arguments.adapters,
                actor=arguments.actor,
                include_work=arguments.work,
            )
        if arguments.command == "archive":
            archived = archive_brain(arguments.target, arguments.item, arguments.yes)
            if archived is not None:
                print(f"archived: {archived.relative_to(arguments.target)}")
        elif arguments.command == "new":
            new_note(
                arguments.target,
                arguments.type_name,
                arguments.slug,
                title=arguments.title,
                actor=arguments.actor,
            )
        elif arguments.command == "validate":
            result = validate_brain(arguments.target, mode=arguments.mode)
            _warnings(result.warnings)
            if not result.valid:
                _issues(result.issues)
                return 1
        elif arguments.command == "index":
            result = build_index(arguments.target, check=arguments.check)
            if arguments.check and result.changed:
                print(
                    "indexes are stale; run portable-brain index TARGET",
                    file=sys.stderr,
                )
                return 1
        elif arguments.command == "inspect":
            _inspection(arguments.target)
        return 0
    except BrainValidationError as error:
        _issues(error.issues)
        return 1
    except (ManifestError, FrontmatterError, OSError, ValueError) as error:
        print(f"portable-brain: error: {error}", file=sys.stderr)
        return 2
    except SystemExit as error:
        return error.code if isinstance(error.code, int) else 1


if __name__ == "__main__":
    raise SystemExit(main())
