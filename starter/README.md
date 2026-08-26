---
type: System
title: Brain Guide
status: stable
---

# Brain Guide

This brain is an ordinary-file protocol. Drop anything into `inbox/`, preserve evidence in `sources/`, maintain useful synthesis in `wiki/`, and append continuity in `journal/`. `assets/` is the only home for non-Markdown resources; it is not a Markdown concept layer. `work/` exists only when this profile configures strict work types.

Begin with [START-HERE.md](START-HERE.md). Read [SPEC.md](SPEC.md) for the contract, [SECURITY.md](SECURITY.md) before adding private material, and [AGENTS.md](AGENTS.md) before editing. No runtime, package manager, database, editor, or service is required.

## Daily use

1. Start from `index.md`, today's and yesterday's journal entries when present, and the document that owns the current state.
2. Drop anything new into `inbox/`—no form or metadata is required. Triage moves each item out to its owner: non-Markdown to `assets/` with a `Source` that references it, evidence preserved as a `Source`, understanding into the owning wiki document. Cite evidence from maintained wiki knowledge rather than replacing it with a summary. See [AGENTS.md](AGENTS.md) for the triage procedure.
3. Keep current state and actionable `## Follow-ups` in their owning wiki or strict work document, not in the journal.
4. After meaningful work, append an attributed block to `journal/YYYY-MM-DD.md`; never rewrite an earlier block.
5. Regenerate deterministic indexes after a cataloged document changes materially.

Whenever `inbox/` has something in it, tell your AI: *Triage my inbox following AGENTS.md.* An empty inbox means nothing is pending.

The clean root `index.md` summarizes layers. Group indexes provide catalog detail; `inbox/index.md` lists every pending item; journal entries are excluded from the primary catalog and use `journal/index.md`.

## Optional automation

If available, the companion command automates the same file behavior:

```sh
portable-brain new . TYPE SLUG --title TITLE --actor ACTOR
portable-brain validate .
portable-brain index . --check
```

Its presence is optional. Files remain canonical, and editor views or generated indexes never replace their meaning.

If this brain carries the `claude` adapter (`.claude/`), Claude Code gets a once-per-session end-of-session review hook and the `/setup`, `/triage`, `/sweep`, `/query`, and `/session-end` skills; each is a procedure that points back to [AGENTS.md](AGENTS.md). Other agents follow the same sections in AGENTS.md directly.
