---
type: System
title: Portable Brain migrations
status: stable
---

# Portable Brain migrations

The active manifest records three independent compatibility signals:

- `schema_version` controls the manifest shape.
- `spec_version` controls Portable Brain behavior.
- `okf_version` identifies the permissive OKF authoring target.

Readers must reject unsupported required schema versions instead of guessing. Before changing any version, copy the brain, validate the copy, apply the documented transformation, rebuild indexes, and validate again.

## 0.1

Version 0.1 is the first public contract. Work tracking is explicit: new manifests include `domains: []` and `modules: []`; enabling `--work` adds `modules: [work]`, the `work/` group, and work types. Older 0.1 manifests that contain a `work` group but omit `modules` are read as work-enabled for compatibility. Regenerating the manifest makes the choice explicit.

Domain overlays no longer write a singular `profile` field. Multiple selections are represented only by the ordered `domains` list.

`inbox/` is an ungated queue. Files of any form are allowed there, untriaged Markdown has no required shape, and probable secrets or non-portable links in inbox Markdown are reported as validation warnings rather than failures. `inbox/index.md` lists every pending item, including non-Markdown files.
