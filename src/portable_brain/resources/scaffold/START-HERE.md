---
type: System
title: Start here
status: stable
---

# Start here

Portable Brain works with ordinary files and any capable LLM. Start with three choices:

1. **What is this for?** Choose any useful domain overlays: `software`, `personal`, `research`, and/or `travel`. Choose none for the universal core.
2. **Do you need tracked projects, decisions, owners, and states?** Enable the optional `work` module only if the answer is yes.
3. **Do you want editor or agent conveniences?** Enable the optional `obsidian` adapter (views, templates, daily notes; it sets Obsidian to insert standard Markdown links — a brain does not use `[[wikilinks]]`, and validation flags any it finds) and/or the optional `claude` adapter (a once-per-session end-of-session review hook plus the `/triage`, `/sweep`, `/query`, and `/session-end` skills for Claude Code; Claude asks you to approve the project's hooks the first time). Neither becomes a dependency.

With the CLI:

```sh
# Smallest useful brain
portable-brain init my-brain --actor human:owner

# Example: software and research, with tracked work and Obsidian conveniences
portable-brain init my-brain --domains software research --work --adapter obsidian claude --actor human:owner
```

Without the CLI, give an LLM this folder and say:

> Set up this folder as my Portable Brain. Read START-HERE.md, SPEC.md, and BOOTSTRAP.md first. Ask me only: (1) which domains fit, (2) whether I need tracked work, and (3) whether I want Obsidian and/or Claude Code conveniences. Then create the smallest conforming brain for my answers, validate internal links and probable secrets, and tell me where to put my first note.

After setup:

- Drop anything new into `inbox/`: Markdown, plain text, documents, images, audio. No form is required; triage moves it to its owner and out of the inbox.
- Preserve evidence in `sources/`.
- Keep current understanding in `wiki/`.
- Append what happened to `journal/YYYY-MM-DD.md`.
- Use `work/` only when it was enabled.

Whenever `inbox/` has something in it, tell your AI: *Triage my inbox following AGENTS.md.* An empty inbox means nothing is pending.

Run `portable-brain validate my-brain` and `portable-brain index my-brain` after structural changes. Read [SECURITY.md](SECURITY.md) before adding private material.
