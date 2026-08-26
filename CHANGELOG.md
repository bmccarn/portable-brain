# Changelog

All notable public changes to Portable Brain are recorded here.

## Unreleased

- Shaping a brain is now a conversation, not a hand edit: `add-type`, `remove-type`, `add-domain`, and `enable-work` adapt the manifest, folders, and templates of an existing brain; the `claude` adapter gains a `/setup` skill that interviews the owner (purpose, recurring kinds, tracked state, what must stay out), proposes the smallest shape, and applies it only after a yes; scaffold `AGENTS.md` gains a "Setup" section and an "Owner's rules" section; START-HERE and BOOTSTRAP are rewritten around the setup interview; `/sweep` proposes promoting recurring Concept documents to a type through the same interview.
- Scaffold `.gitignore` re-includes `AGENTS.md` and `CLAUDE.md`.
- Triage skill: judge dated state against today, group items by subject, drop pipeline tags.

## 0.1.0 - 2026-08-23

First public release.

- Published the ordinary-file Portable Brain 0.1 contract: `inbox/` → `sources/` → `wiki/` → `journal/`, with `assets/` as the only home for non-Markdown resources and an optional strict `work/` module. Every brain is a valid OKF 0.2 bundle.
- `inbox/` is an ungated front door: any file type and shape is allowed, untriaged Markdown has no required shape, and probable secrets or non-portable links there are validation warnings instead of failures. `inbox/index.md` and the root summary list every pending item, including non-Markdown files; triage moves each item out to its owner.
- Sources preserve evidence; the wiki maintains synthesis with citations; the journal is append-only continuity, with local measured timestamps, that never owns current state or follow-ups.
- Composable domain overlays: `software`, `personal`, `research`, `travel`.
- Optional CLI — `init`, `new`, `validate`, `index`, `inspect`, `archive` — automating the same file contract. `validate` prints warnings and exits 0 when only warnings are present; stale generated indexes are warnings and never block regeneration; `archive` mirrors a work item's path beneath `work/archive/` and refuses configured type folders.
- Validation rejects probable secrets, including well-known provider token formats, and treats inbox content as untrusted text.
- Deterministic hierarchical indexes, starter brain generation, and onboarding, security, migration, and packaging material.
- Optional adapters: `obsidian` (views, templates, daily notes) and `claude` (a once-per-session end-of-session review hook that travels with the brain, plus `/triage`, `/sweep`, `/query`, and `/session-end` skills). Hidden tool directories are never validated as knowledge.
