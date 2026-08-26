---
type: System
title: Portable Brain Bootstrap
status: stable
---

# Portable Brain bootstrap

This document and [SPEC.md](SPEC.md) are sufficient to create, adapt, and maintain a brain. The result must work with ordinary files alone: do not require Python, an editor, a database, an embedding service, a daemon, or any other runtime.

## Adapt a brain

1. Interview the owner first, as the Setup section of AGENTS.md describes — purpose, recurring kinds, tracked state, what must stay out — and propose the smallest shape before writing anything. Then begin with an empty target and create `.portable-brain/profile.yaml` with the ordered `domains`, `modules`, `groups`, `workflow`, and `types` mappings described in [SPEC.md](SPEC.md). Select only needed domain overlays.
2. Create the mandatory semantic layers: `inbox/`, `sources/`, `wiki/`, and `journal/`. Create `work/` only if the manifest declares work types. Treat `assets/` as the only home for non-Markdown resources, referenced by relative path from the document that preserves or explains them; it is not a Markdown concept layer.
3. Keep root system documents as simple, parseable type-bearing operational files. They are not routed concepts.
4. Let anything land in `inbox/` with no required shape; it is the ungated front door. Triage moves each item out to its owner: a non-Markdown item moves to `assets/` and gains a `Source` that references it; text that is evidence is preserved as `Source` material under sources, including supplied text, identity, resource, and citation details; text that is understanding is written into the owning wiki document; journal each move. Do not replace preservation with a prose summary.
5. Maintain durable explanation in wiki. Use `description` only as a navigation summary; cite evidence through `sources` metadata and standard Markdown links.
6. Keep current state and actionable `## Follow-ups` in their owning wiki or strict work document. Journal entries say what happened and link to that owner; they never own current state or actionable checkboxes.
7. For meaningful work, append an attributed `## HH:MM — topic` block to `journal/YYYY-MM-DD.md`. Never edit an earlier block. An immutable published bundle may leave the journal empty.
8. Configure work only when needed. Only configured work types may carry `pb_*`; use the manifest's state keys, initial state, closed states, and blocker rule.
9. To add a type later without the CLI, append it under `types` in the manifest — `group`, group-relative `folder`, `workflow: true` only for work types, ordered `sections` — create its folder, copy an existing template, and validate. Remove a type only when no document uses it.
10. Generate a clean root layer summary and deterministic group indexes. List every pending inbox item, including non-Markdown files, in `inbox/index.md`. Exclude journal entries from the primary catalog; provide `journal/index.md`.

## Prompt for an agent

> Build or adapt this target as a Portable Brain 0.1 authoring profile. Read `SPEC.md`, `AGENTS.md`, and `.portable-brain/profile.yaml` first. Interview me as AGENTS.md's Setup section describes and apply a shape only after I agree. Interview me as AGENTS.md's Setup section describes and apply a shape only after I agree. Use ordinary Markdown, YAML, directories, and standard relative links as the complete runtime. Create the inbox → sources → wiki → journal flow with inbox as an ungated queue that empties on triage; preserve source material distinctly from maintained synthesis; keep journal append-only; keep current state and follow-ups in their owning wiki or strict work document; and use work only when configured. Treat `assets` as the only home for non-Markdown resources, not a Markdown layer. Keep the root index a clean layer summary and journal out of its primary catalog. Do not add services, databases, embeddings, daemons, or an editor dependency.

## Optional adapter

When installed, the CLI automates the same protocol:

```sh
portable-brain init TARGET --domains software personal research --work --adapter obsidian claude --actor human:owner
portable-brain add-type TARGET Client --group wiki --folder clients --sections Summary "Current state" Contacts History Follow-ups References
portable-brain add-type TARGET Client --group wiki --folder clients --sections Summary "Current state" Contacts History Follow-ups References
portable-brain validate TARGET
portable-brain index TARGET --check
```

Use `validate TARGET` for strict portable validation. Use `validate TARGET --okf` only to check the permissive OKF core shape; it does not assert Portable Brain group or workflow conformance.
