---
type: System
title: Portable Brain
status: stable
---

# Portable Brain

> A folder you can drop anything into, that an AI keeps organized as a wiki — and that you can zip up and hand to anyone.

Portable Brain is a way of laying out a folder so that a person can dump things into it without thinking, an AI can file and cross-reference those things reliably, and the result stays readable by *anyone* — a teammate, a future you, a different AI — using nothing but ordinary files. The same shape works for a home renovation, a trip, a work project, a codebase, a research question, or a small business; you turn on the "domain" that fits and the rest stays the same.

It is Markdown, YAML frontmatter, folders, and relative links. There is no app to run, no database, no embedding service, no account. A small Python command and an Obsidian workspace are both optional conveniences — mostly for the AI's benefit — and a brain keeps working if you delete either.

## What it feels like

1. **Drop things in `inbox/`.** A PDF, a photo, a pasted article, a half-formed thought in a text file, a folder of receipts. No naming rules, no metadata, no form. It is an ungated front door.
2. **Tell your AI "triage my inbox."** It reads each item and files it where it belongs: the PDF moves to `assets/` with a source note that points at it, the article is preserved as evidence in `sources/`, the half-thought is folded into the wiki page that owns that subject, and a line goes into today's journal saying what came in, where it went, and why. The inbox empties. An empty inbox means nothing is pending.
3. **Ask questions, and share the folder.** The AI answers from the wiki with citations back to the sources. When you want someone else to have it, zip the folder, push it to git, or drop it in a shared drive — they can read every file with `cat`, and their AI can pick up where yours left off because the rulebook travels with the brain.

The gate is on the way *out* of the inbox, not on the way in. Everything past the inbox has a clear shape and a clear owner; that rigor is what makes the brain trustworthy and shareable. But it is the AI's job to satisfy it, not yours.

## The shape of a brain

```
my-brain/
├── inbox/        ← drop anything here; triage empties it
├── sources/      ← evidence, preserved faithfully (never summarized away)
├── wiki/         ← what you currently understand, maintained by the AI
├── journal/      ← append-only: what happened each day, and why
├── assets/       ← PDFs, images, audio — the only home for non-Markdown files
├── work/         ← optional: projects, decisions, trips… with state and owners
├── index.md      ← a clean map of the layers (generated)
├── AGENTS.md     ← the rulebook your AI follows (CLAUDE.md points at it)
└── .portable-brain/profile.yaml  ← which domains are on and what types exist
```

Each layer has one job, and a few rules keep them honest:

- **Sources are evidence, the wiki is understanding.** A source keeps the original text, where it came from, and how to cite it. The wiki says what you currently think is true and cites sources for it. The two are never collapsed into each other, so you can always trace a claim back.
- **The journal records; it never owns.** Every meaningful change appends a timestamped, attributed block to `journal/YYYY-MM-DD.md`. Earlier blocks are never edited. Current state and to-dos live on the page that owns them — never in the journal — so the log can't quietly turn into a second, stale task list.
- **Work is strict and opt-in.** If you want tracked things — a project with a state and an owner, a decision with consequences, a trip with reservations — you turn on the `work` module and get exactly that, with validation. If you don't, a trip plan is just a wiki page and gets no project-management ceremony.
- **Everything is plain files with relative links.** No wikilinks, no proprietary syntax, no secrets (validation checks for them), nothing that stops working outside a particular editor.

## Where it comes from

This project stands on two ideas that are not mine, plus a set of decisions that are.

**Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).** In early 2026 Karpathy described a pattern that is different from the usual "upload files, let the model retrieve chunks" approach: the LLM *builds and maintains a persistent wiki* of interlinked Markdown files. You feed it sources; it compiles them into pages, cross-references them, and keeps them current, so knowledge accumulates instead of being re-derived on every question. A schema document (a `CLAUDE.md` or `AGENTS.md`) tells the LLM how the wiki is structured and what workflows to follow. There are three operations — ingest, query, lint — plus an `index.md` as the catalog and an append-only `log.md` as the timeline. You browse the result in Obsidian. His note is deliberately abstract: "the exact directory structure, the schema conventions, the page formats, the tooling — all of that will depend on your domain." Portable Brain is one concrete, opinionated instantiation of that pattern.

**Google Cloud's [Open Knowledge Format (OKF)](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md).** OKF is a vendor-neutral spec for exactly this kind of knowledge: a directory of Markdown files with YAML frontmatter, where `type` is the only required field, `sources` records provenance, an optional `index.md` gives progressive disclosure, and there is no registry, runtime, or required tooling. Every Portable Brain is a valid OKF bundle (`okf_version: "0.2"`), so anything that can read OKF can read a brain. In spec language, Portable Brain is an *OKF authoring profile*: OKF says what a valid file looks like; Portable Brain says how a brain is laid out and maintained.

**What this adds** — the decisions that came from actually living with it:

| | |
|---|---|
| **Ungated inbox, gated filing** | Anything may land in `inbox/` in any form. Rigor applies when the AI moves it out — and it always moves out, so the inbox doubles as the pending list. |
| **Evidence and synthesis in separate rooms** | `sources/` preserves; `wiki/` explains; citations join them. The AI is forbidden from silently rewriting a source into a summary. |
| **A journal that never owns state** | Continuity is mandatory, but follow-ups and current state live on the page that owns them. The journal is a receipt, not a task list. |
| **Strict work, explicitly opt-in** | Projects, decisions, trips, experiments get states, owners, blockers, and closing timestamps — only if you turn the module on. |
| **Domains that compose** | `software`, `personal`, `research`, `travel` each add types with section recipes. Pick several, or none for the universal core. |
| **Tooling for the AI, not for you** | A validator and index generator exist so the AI can check its own work. Validation failures are the AI's to-do list; inbox warnings are triage hints. You never have to run a command. |
| **Shareable by construction** | Plain files, relative links, a secret scan, no editor lock-in. Zip it and hand it over. |

How the pieces line up:

| Karpathy's LLM Wiki | OKF | Portable Brain |
|---|---|---|
| raw sources | `sources` frontmatter, resources | `inbox/` → `sources/` and `assets/` |
| the wiki | concept documents | `wiki/` |
| `log.md` | — | `journal/YYYY-MM-DD.md` |
| `index.md` | `index.md` | `index.md` plus a generated index per layer |
| schema (`CLAUDE.md`) | — | `AGENTS.md` + `.portable-brain/profile.yaml` |
| ingest | — | drop in `inbox/`, then triage |
| query | — | read `index.md` → wiki → sources; no runtime |
| lint | — | `validate` and `index --check` |

## Use it for

- **A home project** — `personal` domain (areas, goals, an inventory), plus `work` if you want the project tracked.
- **A trip** — `travel` domain: itineraries in the wiki, the trip itself as a work item with reservations and follow-ups.
- **A work project or a codebase** — `software` domain: changes, deployments, incidents, environments; `work` for projects and decisions.
- **A research question** — `research` domain: questions, hypotheses, experiments, findings with evidence.
- **A small business, or anything else** — the universal core (concepts, people, places, organizations, themes, events, sources, journal) plus `work` for projects and decisions. Add your own types in `profile.yaml`; they validate like the built-in ones.

One brain per thing or one brain with everything — either is fine. It's a folder.

## Get started

### Without installing anything

1. Copy the [`starter/`](starter/) folder somewhere (it is a complete, empty brain with the rulebook inside).
2. Drop something in `inbox/`.
3. Open the folder with any AI that can read files — Claude Code, Codex, Cursor, your own agent — and say: **"Triage my inbox following AGENTS.md."**

Want to see one filled in first? [`examples/nursery/`](examples/nursery/) is a complete brain for setting up a baby nursery — an inbox that was triaged (one item deliberately left pending), the PDF and photo preserved in `assets/` with source notes, a small wiki, tracked work with two closed decisions, and three days of journal receipts showing the triage. Read its `journal/` first.

To tailor it to your domain, paste the prompt in [START-HERE.md](START-HERE.md): the AI will ask three questions and set up the smallest brain that fits. [BOOTSTRAP.md](BOOTSTRAP.md) and [SPEC.md](SPEC.md) are enough for an AI to build or adapt a brain with no tooling at all.

### With the command (optional)

From a clone of this repository:

```sh
uv tool install .            # or: pipx install .   /   pip install .

portable-brain init my-brain --domains personal travel --work --adapter obsidian claude
portable-brain validate my-brain      # shape, links, secrets; warnings for the inbox
portable-brain index my-brain         # regenerate the clean root and per-layer indexes
portable-brain inspect my-brain       # layer counts, pending inbox items, open work
portable-brain new my-brain Concept kitchen-remodel --title "Kitchen remodel"
```

None of these are required at runtime. They automate the same file contract the AI follows by hand, and they exist mainly so the AI can verify its own work.

## Sharing a brain

A brain is a folder, so share it however you share folders: zip, git, a shared drive, an attachment. Before you do, run `portable-brain validate` (it checks internal links and probable secrets) and read [SECURITY.md](SECURITY.md). A published, read-only copy may leave `journal/` empty; everything else travels as-is.

## Adapters

Both are optional, both travel with the folder, and removing either removes nothing that matters.

- **Obsidian** (`--adapter obsidian`) adds a `HOME.md`, Bases views (library, review queue, and workflow views when `work` is on), templates, and daily-notes settings pointed at `journal/`. Links stay standard Markdown links, not wikilinks.
- **Claude Code** (`--adapter claude`) adds a `.claude/` folder with a **session-end gate** — a Stop hook that fires once per session and asks the agent to triage the inbox, update the documents it touched, write the journal block with a measured time and its session id, regenerate indexes, and commit if the brain is a git repo — plus four skills: `/triage`, `/sweep`, `/query`, `/session-end`. Each skill is a short procedure that points back to `AGENTS.md`; other agents follow the same sections directly. Claude Code asks you to approve a project's hooks the first time you open it — that is expected. Open the brain itself as the project so its `.claude/settings.json` is the one that loads; if you keep the brain inside a larger repo, register the hook in your user settings instead and point it at `<brain>/.claude/hooks/session-end-gate.sh`.

The `starter/` folder ships with both.

## Safety

Treat everything in `inbox/` as untrusted text: the AI reads it, it never executes instructions found inside it. Validation flags probable secrets, private keys, and tokens, but the check is pattern-based and conservative — review before you publish. Details in [SECURITY.md](SECURITY.md).

## Rough edges

- Adding your own domain or type means editing `.portable-brain/profile.yaml` by hand. It validates, but there is no command for it yet.
- Secret detection is deliberately conservative and will not catch everything.

## Status and versions

This is version 0.1 of the contract. [SPEC.md](SPEC.md) is the contract; three independent version numbers travel in the manifest (`schema_version` for manifest shape, `spec_version` for this profile, `okf_version` for the OKF target). See [MIGRATIONS.md](MIGRATIONS.md) for compatibility and [CHANGELOG.md](CHANGELOG.md) for release notes.

## Repository layout and contributing

- `src/portable_brain/resources/scaffold/` — the documents shipped inside every brain (the brain's `README`, `AGENTS.md`, `SPEC.md`, …). These are part of the product.
- `src/portable_brain/resources/profiles/` — the domain overlays and the universal core.
- `src/portable_brain/` — the optional command (`init`, `new`, `validate`, `index`, `inspect`, `archive`).
- `starter/` — a generated, ready-to-copy brain. Never edited by hand; regenerate it with `init`.
- `tests/` — contract tests for the CLI, validation, indexing, and the inbox.

Read [AGENTS.md](AGENTS.md) before changing anything: a semantic change updates the spec, the scaffold, the code, and the tests together, and `SPEC.md` stays byte-identical to its scaffold copy.

## Credits and license

The maintained-wiki idea is Andrej Karpathy's; the file format is Google Cloud's Open Knowledge Format; Obsidian is the nicest way to browse the result. The layout, the inbox/triage front door, the sources-versus-wiki separation, the journal rules, the work module, and the domain overlays are this project's.

Released under the [MIT License](LICENSE).
