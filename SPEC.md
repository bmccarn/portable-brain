---
type: System
title: Portable Brain Specification 0.1
status: stable
---

# Portable Brain Specification 0.1

Portable Brain is an ordinary-file protocol for moving material through useful semantic layers: capture in `inbox/`, preserve evidence in `sources/`, synthesize maintained knowledge in `wiki/`, and append continuity in `journal/`. `assets/` is the only home for non-Markdown resources, not a Markdown concept layer. `work/` is optional and strict. Markdown, YAML frontmatter, directories, and standard Markdown links are canonical; a tool or editor is an optional adapter.

Portable Brain is an **OKF authoring profile**. Its `okf_version` declares the permissive Open Knowledge Format core it authors within; `spec_version` declares these additional portable conventions. Portable Brain validation is not a claim that every valid OKF bundle satisfies this profile.

## 1. Canonical model

A brain has `.portable-brain/profile.yaml`, Markdown documents, and optional resources. A Markdown document has parseable YAML frontmatter with non-empty `type` and `title`, except generated indexes, whose specified frontmatter is authoritative, and untriaged `inbox/` content, which has no required shape. Standard links are relative Markdown destinations such as `[Design](wiki/design.md)` or `[Decision](decision.md#follow-ups)`.

The manifest contains these ordered keys:

```yaml
schema_version: 1
spec_version: "0.1"
okf_version: "0.2"
default_actor: human:owner
domains: []
modules: []
groups:
  inbox: {}
  sources: {}
  wiki: {}
  journal: {}
workflow:
  states:
    active: Active
    blocked: Blocked
    parked: Parked
    done: Done
    dropped: Dropped
  initial_state: active
  closed_states: [done, dropped]
  requires_blocked_on: [blocked]
types: {}
adapters: []
```

`domains` is the ordered list of composable domain overlays. `modules` names explicit optional behavior; version 0.1 supports `work`. The manifest never uses a singular `profile` selector. `groups` are semantic layers, not a type-to-folder map. Their workflow order is `inbox`, `sources`, `wiki`, `journal`, then optional `work`; `assets` is outside that sequence. A type declares its `group`, group-relative non-empty `folder`, ordered `sections`, and, only where applicable, `workflow` behavior. `folder: "."` is the reserved marker for that group's root, so `Journal` uses `group: journal` and `folder: "."`. The implementation reads the manifest rather than assuming type names, folders, or sections.

Root system documents (`README.md`, `START-HERE.md`, `SPEC.md`, `SECURITY.md`, `MIGRATIONS.md`, `AGENTS.md`, `CLAUDE.md`, `BOOTSTRAP.md`, and adapter home material) are reserved operational documents: they require parseable frontmatter and non-empty `type` and `title`, but are not routed into a group or cataloged as knowledge. Hidden directories such as `.obsidian/`, `.claude/`, and `.git/` hold editor, agent, or tool material and are never routed, cataloged, or validated as knowledge.

### Group rules

- `inbox/` is the ungated front door. Anything may land there in any form: Markdown with or without frontmatter, plain text, documents, images, audio, or folders of them. Inbox content is outside every shape rule in this specification until it is triaged; portable validation reports probable secrets and non-portable or broken links in inbox Markdown as warnings, never as failures. Inbox is a queue, not a home: triage moves each item out to its owner, so an empty inbox means nothing is pending.
- `sources/` contains only configured `Source` types. Preserve source text, identity, citation details, and original resource references; do not silently rewrite source material into a summary.
- `wiki/` contains maintained knowledge. It accepts every non-reserved type and is where synthesis, explanation, and current durable understanding live.
- `journal/` contains only `Journal` documents. It is mandatory in every profile.
- `work/` is optional. It contains only configured work types and is the sole layer allowed to carry `pb_*` workflow fields. `work/archive/` mirrors `work/`: an archived document keeps its configured type folder beneath `archive/` and remains valid there; configured type folders themselves are never archived.
- `assets/` is the only home for non-Markdown resources: documents, images, audio, data files, and similar material. It is not a Markdown group and has no concept types. A resource is referenced from the document that preserves or explains it through an ordinary relative path that resolves inside the brain, such as `resource: ../assets/contractor-quote.pdf` in `sources` metadata or a standard Markdown link.

## 2. Frontmatter, descriptions, and citations

Use ordinary OKF-shaped metadata where useful:

```yaml
type: Concept
title: Example title
description: A concise orientation to this maintained document.
status: stable
tags: [example]
generated:
  by: human:owner
  at: 2026-08-22T00:00:00+00:00
sources:
  - resource: https://example.invalid/source
    title: Primary source
```

`description` is a concise navigation summary; it is not evidence, a citation, or a substitute for a claim's source. Stable wiki and work documents require a non-empty, single-line description; drafts may leave it empty while being written. `sources` identifies derivation material. A source with an `id` joins one-for-one to a Markdown footnote of the same id in source, wiki, or journal content. Resource paths must resolve within the brain unless they are external URLs. Preserve supplied source text and resource/citation details faithfully enough to trace each claim. `generated` identifies the actor and meaningful-change time. `verified` records a real check against a named source or resource. Timestamps emitted by this profile are local time with an explicit offset, measured when written rather than estimated.

For configured types, every declared `sections` heading must appear as an exact `##` heading in the declared order. Extra headings are allowed. Unconfigured conceptual types remain allowed in `wiki/` and do not inherit a configured section recipe.

Actors are `human:<id>`, `process:<id>`, or `<producer>/<version>`. `default_actor` fills only a genuinely unknown creator. Unknown, non-conflicting frontmatter is preserved.

## 3. Strict work and append-only journal

Only a configured work type may use these flat Portable Brain fields:

```yaml
pb_work_state: active
pb_owner: human:owner
pb_blocked_on:
  - "[Dependency](../wiki/dependency.md)"
pb_closed_on: 2026-08-22T00:00:00+00:00
```

`pb_work_state` names a `workflow.states` key. Its initial state is `workflow.initial_state`; every state in `workflow.closed_states` requires `pb_closed_on`; every state in `workflow.requires_blocked_on` requires `pb_blocked_on`. Each blocker is one standard Markdown link that resolves inside the brain. No other group may carry any `pb_*` field.

Journal is core, not optional: meaningful work appends an attributed `## HH:MM — topic` block to `journal/YYYY-MM-DD.md`, where the day and time are local and measured at write time. Earlier blocks never change; corrections are new blocks that identify what they correct. A published immutable bundle may leave `journal/` empty, but it still retains the directory and its semantics.

The journal records what happened, evidence, and links. It does **not** own current state or actionable follow-ups. Current state and `## Follow-ups` belong in the relevant maintained wiki document or strict work document. A follow-up becomes a work item only when it needs independent workflow state, ownership, provenance, or history. Journals have no actionable checkboxes.

## 4. Four file-native behaviors

1. **Initialize** — start only in an empty target, select zero or more domain overlays, explicitly choose whether to enable work, write the manifest and root system documents, and create the mandatory layers. The optional CLI is `portable-brain init TARGET [--domains software|personal|research|travel ...] [--work] [--adapter obsidian|claude ...] [--actor ACTOR]`.
2. **Ingest** — drop anything into `inbox/`; no form or metadata is required. Triage then moves each item out to its owner: a non-Markdown item moves to `assets/` and gains a `Source` that references it; text that is evidence is preserved as a `Source`; text that is understanding is written into the owning wiki document; something that needs its own state becomes work only when `work/` is configured. Each triaged item is linked from the document that owns its subject, recorded in the journal, and removed from `inbox/`. Material that cannot be classified stays in `inbox/` and the journal says so. Do not turn preservation into silent synthesis.
3. **Query** — read the clean root `index.md` as a layer summary, then group indexes and linked documents. `journal/` is excluded from the primary catalog and has `journal/index.md` instead. Query remains ordinary file navigation; no runtime is required.
4. **Maintain** — update wiki synthesis with citations, triage inbox material out to its owner, maintain strict work state when configured, and append journal continuity. Regenerate deterministic indexes after material catalog changes.

`portable-brain new TARGET TYPE SLUG --title TITLE [--actor ACTOR]`, `archive TARGET ITEM [yes]`, `validate TARGET [--portable|--okf]`, `index TARGET [--check]`, and `inspect TARGET` are optional adapters for these behaviors. `new` refuses overwrite; `index` fails closed when the brain is invalid.

## 5. Indexes and adapters

The root `index.md` is deterministic, generated, and a clean layer summary. Group indexes are deterministic and mirror nested folders with nested headings, so domain overlays remain legible without flattening their structure. Maintained wiki, source, and work content may appear in their applicable catalogs; the inbox index lists every pending item, including non-Markdown files, so the queue is visible without a runtime; journal entries do not appear in the primary catalog. Generated indexes, views, templates, and editor settings are derived material and never override canonical files. Because they are derived, a generated index whose links no longer resolve is stale rather than invalid: portable validation reports it as a warning that says to regenerate, and regeneration is never blocked by the stale index itself.

Adapters may add convenience material but preserve the canonical tree. Obsidian Bases or embeds are presentation syntax only; canonical relationships remain standard Markdown links. Removing an adapter must not remove canonical meaning. The `claude` adapter adds a project-scoped session-end hook and agent skills under `.claude/`; they are procedure and presentation that point back to `AGENTS.md`, never canonical meaning.

## 6. Validation and safety

`validate TARGET` defaults to **portable** validation. Portable validation checks this profile's manifest shape, group routing, frontmatter, standard links, strict source/work/journal rules, and generated-index eligibility. It rejects secure-material patterns in canonical Markdown and frontmatter, including structured secrets, private keys, bearer credentials, password values, and well-known provider token formats; source text is preserved rather than sanitized or executed. Untriaged `inbox/` content is exempt from shape rules; probable secrets and non-portable or broken links in inbox Markdown are reported as warnings so triage does not carry them forward, and they never fail validation or block index generation.

`validate TARGET --okf` is manifest-independent: it checks Markdown in any directory for the permissive OKF core shape and intentionally does not impose Portable Brain's manifest, secret, path, link, group, or workflow policy. Validation reads files and never executes their content. Keep credentials and machine-local secrets out of portable content.

A conforming brain needs no package manager, daemon, database, embedding service, editor, or runtime. A person or agent can create, inspect, query, and maintain it using ordinary files alone.

## 7. Compatibility

`schema_version` governs manifest shape; `spec_version` governs this profile; `okf_version` names its OKF authoring target. Readers reject unsupported required schema versions rather than guessing. Additive metadata remains compatible when preserved; breaking changes require a new major version and migration guidance in [MIGRATIONS.md](MIGRATIONS.md).
