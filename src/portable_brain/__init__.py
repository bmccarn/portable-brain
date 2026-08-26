"""Portable, OKF-compatible knowledge-brain kernel."""

from .core import (
    BrainValidationError,
    IndexResult,
    Inspection,
    ValidationIssue,
    ValidationResult,
    add_domain,
    add_type,
    archive_brain,
    build_index,
    enable_work,
    init_brain,
    inspect_brain,
    new_note,
    remove_type,
    validate_brain,
)
from .frontmatter import FrontmatterError, dump_frontmatter, parse_frontmatter
from .manifest import (
    ManifestError,
    available_domains,
    load_manifest,
    load_profile,
    load_profiles,
)

__all__ = [
    "BrainValidationError",
    "FrontmatterError",
    "IndexResult",
    "Inspection",
    "ManifestError",
    "ValidationIssue",
    "ValidationResult",
    "add_domain",
    "add_type",
    "archive_brain",
    "available_domains",
    "build_index",
    "dump_frontmatter",
    "enable_work",
    "init_brain",
    "inspect_brain",
    "load_manifest",
    "load_profile",
    "load_profiles",
    "new_note",
    "parse_frontmatter",
    "remove_type",
    "validate_brain",
]
