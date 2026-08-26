---
type: System
title: Start here
status: stable
---

# Start here

Portable Brain works with ordinary files and any capable LLM. Setting one up is a short conversation with your AI, not a form:

1. **Copy the starter folder** (or run `portable-brain init`).
2. **Drop anything into `inbox/`.** The first few things you want the brain to hold are the best hint of what it is for.
3. **Tell your AI:** *Set up this brain for <what it's for>.* It asks a few questions — what kinds of things recur, whether any need a state and an owner, who else may read the folder and what must stay out — proposes the smallest shape, and applies it only after you say yes. Then: *Triage my inbox.*

The choices behind that conversation:

- **Domains.** Ready-made shapes: `software`, `personal`, `research`, `travel`. Pick any, or none for the universal core (concepts, people, places, organizations, themes, events, sources, journal), which files anything.
- **Work.** Enable the optional `work` module only if some things need tracked state, owners, and dates.
- **Your own types.** When a kind of thing keeps recurring — a policy, a client, a recipe — your AI gives it a shape in one step (`portable-brain add-type`: a folder and the headings every such page must carry). Nothing about the brain's engine changes.
- **Adapters.** `obsidian` (views, templates, daily notes; it inserts standard Markdown links — a brain does not use `[[wikilinks]]`, and validation flags any it finds) and/or `claude` (a once-per-session end-of-session review hook plus the `/setup`, `/triage`, `/sweep`, `/query`, and `/session-end` skills for Claude Code; Claude asks you to approve the project's hooks the first time). Neither becomes a dependency.

With the CLI:

```sh
# Smallest useful brain
portable-brain init my-brain --actor human:owner

# Example: software and research, with tracked work and both adapters
portable-brain init my-brain --domains software research --work --adapter obsidian claude --actor human:owner

# Give a recurring kind of thing a shape, any time
portable-brain add-type my-brain Policy --group wiki --folder policies --sections Summary "Current term" Coverage History Follow-ups References
```

Without the CLI, give an LLM this folder and say:

> Set up this folder as my Portable Brain for <what it's for>. Read START-HERE.md, SPEC.md, BOOTSTRAP.md, and the Setup section of AGENTS.md first. Interview me one question at a time about what recurs, what needs tracked state, and what must never be written here; propose the smallest shape; apply it only after I say yes; then tell me where to put my first note.

After setup:

- Drop anything new into `inbox/`: Markdown, plain text, documents, images, audio. No form is required; triage moves it to its owner and out of the inbox.
- Preserve evidence in `sources/`.
- Keep current understanding in `wiki/`.
- Append what happened to `journal/YYYY-MM-DD.md`.
- Use `work/` only when it was enabled.

Whenever `inbox/` has something in it, tell your AI: *Triage my inbox following AGENTS.md.* An empty inbox means nothing is pending.

Run `portable-brain validate my-brain` and `portable-brain index my-brain` after structural changes. Read [SECURITY.md](SECURITY.md) before adding private material.
