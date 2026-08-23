---
type: System
title: Portable Brain Claude Development Entry Point
status: stable
---

# Claude development entry point

Read [AGENTS.md](AGENTS.md) for repository rules and [SPEC.md](SPEC.md) for the shipped file protocol. Preserve the source-to-synthesis model: `inbox/` is the ungated front door that empties on triage, `sources/` preserves evidence, `wiki/` maintains knowledge, `journal/` appends continuity, and optional `work/` alone owns strict workflow metadata.

For any semantic change, update the contract, matching scaffold resources, implementation, and behavior together. Keep `SPEC.md` byte-identical to its scaffold copy and regenerate—not hand-edit—`starter/` after packaged-resource changes. Python and Obsidian remain optional adapters; the finished brain must work as ordinary files without either.
