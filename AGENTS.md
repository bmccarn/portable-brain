---
type: System
title: Portable Brain Development Protocol
status: stable
---

# Development Protocol

## Contract and boundaries

[SPEC.md](SPEC.md) is the public contract. It is byte-identical to `src/portable_brain/resources/scaffold/SPEC.md`. The repository documents explain development; scaffold documents guide an initialized brain. Both are reserved system documents: keep their frontmatter parseable with a non-empty type, but do not model them as routed knowledge entries.

The file protocol is primary. `src/portable_brain/` is optional automation; `resources/scaffold/` is the canonical initialized-brain document set; `resources/profiles/` defines manifest vocabulary; `resources/obsidian/` is optional presentation material; and `starter/` is generated output. Do not hand-edit `starter/` or let adapter syntax become canonical meaning.

## Semantic changes

Read the manifest and specification before changing brain semantics. Keep the four mandatory manifest groups in their declared order: `inbox`, `sources`, `wiki`, `journal`; append `work` only when the explicit module is enabled. Treat `assets` as a resource area, not a Markdown group. Keep inbox ungated so anything may land there and leaves on triage; preserve sources rather than silently rewriting them as synthesis; maintain knowledge in wiki; keep journal append-only; allow `pb_*` only on configured work types.

A semantic change updates its contract, shipped scaffold, implementation, and behavioral coverage together. Format and lint with `ruff format src tests` and `ruff check --fix src tests` before considering code done; `pytest` and `pyright` must both pass. Use the manifest-loading boundary rather than hard-coding group names, types, folders, sections, or workflow states in unrelated code. Preserve standard Markdown links and the no-runtime guarantee.

## Resource synchronization

After changing scaffold, profile, adapter, or template resources, regenerate `starter/` only through the initializer into an empty target, then replace the generated starter as one coherent output. Never patch generated starter files by hand. Keep root/scaffold `SPEC.md` byte-identical; keep root documents appropriate for contributors and scaffold `README.md`, `AGENTS.md`, `CLAUDE.md`, and `BOOTSTRAP.md` appropriate for people and agents operating a brain.

## Agent discipline

An agent starts by reading `SPEC.md`, the manifest, the root index, current journal context, and the document that owns the requested state. It edits source preservation, maintained synthesis, strict work state, follow-ups, and journal entries in their distinct homes; then it updates derived indexes only from valid canonical files. Completion requires one owner for current state and follow-ups, append-only journal continuity for meaningful work, preserved evidence, and current deterministic indexes.
