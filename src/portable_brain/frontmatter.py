"""Strict YAML-frontmatter parsing and deterministic emission."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import yaml


class FrontmatterError(ValueError):
    """Raised when a Markdown document has invalid YAML frontmatter."""


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return a document's YAML frontmatter mapping and Markdown body.

    Frontmatter may include a UTF-8 BOM or leading blank lines, but must otherwise
    begin before substantive Markdown content so a later YAML fence is not
    accidentally treated as metadata.
    """
    stripped = text.removeprefix("\ufeff").lstrip("\r\n")
    if not stripped.startswith("---\n"):
        raise FrontmatterError("frontmatter must begin with an opening --- fence")

    closing = stripped.find("\n---\n", 4)
    closing_length = 5
    if closing < 0 and stripped.endswith("\n---"):
        closing = len(stripped) - 4
        closing_length = 4
    if closing < 0:
        raise FrontmatterError("frontmatter is missing its closing --- fence")

    raw = stripped[4:closing]
    try:
        parsed = yaml.safe_load(raw)
    except yaml.YAMLError as error:
        raise FrontmatterError(f"invalid YAML frontmatter: {error}") from error
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, Mapping):
        raise FrontmatterError("frontmatter must be a YAML mapping")
    if any(not isinstance(key, str) for key in parsed):
        raise FrontmatterError("frontmatter keys must be strings")

    body_start = closing + closing_length
    return dict(parsed), stripped[body_start:]


def dump_frontmatter(metadata: Mapping[str, Any], body: str = "") -> str:
    """Emit a Markdown document with stable, safe YAML frontmatter."""
    if not isinstance(metadata, Mapping):
        raise FrontmatterError("frontmatter must be a mapping")
    rendered = yaml.safe_dump(
        dict(metadata),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).rstrip("\n")
    return f"---\n{rendered}\n---\n{body}"
