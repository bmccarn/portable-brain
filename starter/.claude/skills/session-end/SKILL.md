---
name: session-end
description: Close out a work session on this brain — triage pending inbox items, update the touched documents' current state and follow-ups, append today's journal block with a measured time and session id, regenerate indexes, validate, and commit if the brain is a git repository. Use at the end of a session, or when the session-end hook asks.
---

# Session end

Follow AGENTS.md "Session end" exactly. Checklist:

1. `date '+%Y-%m-%d %H:%M'` — this is "now" and "today".
2. Anything pending in `inbox/`? Triage it (the `triage` skill) or say in the journal why it stays.
3. For every wiki or work document this session touched: current state and `## Follow-ups` are right; `verified` is set only where you actually checked something.
4. Append today's journal block: measured `## HH:MM — topic` heading, the actor line, a backticked `session: <tool> <id>` line when your tool exposes one (never invent an id), then what changed, why, evidence, and links to the documents that own current state.
5. `portable-brain index .` and `portable-brain validate .` when available; fix what is reported.
6. If the brain is a git repository: commit with a short journal-style message and push when a remote is configured. Leave another session's uncommitted work alone and say so.

If nothing brain-worthy happened and the brain is clean, say so in one line and stop.
