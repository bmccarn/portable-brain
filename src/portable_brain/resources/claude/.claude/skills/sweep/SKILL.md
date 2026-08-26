---
name: sweep
description: Health pass over this brain — validation and index freshness, the oldest-verified review queue, open follow-ups, work state drift, orphaned sources and assets, contradictions — with every change journaled. Use when asked to sweep, lint, or review the brain, or when the review queue is more than a couple of weeks old.
---

# Sweep

AGENTS.md and SPEC.md are the rules. A sweep is read-mostly; every change goes through the normal rules and is journaled. Propose deletions; do not delete silently.

1. Measure the time: `date '+%Y-%m-%d %H:%M'`.
2. Mechanics: `portable-brain validate .` and `portable-brain index . --check` (or hand-check links and indexes). Fix what is reported; regenerate.
3. Review queue: wiki and source documents with no `verified` or the oldest `verified.at`. Re-verify the top few against their sources or resources; record `verified` (actor and measured time) or correct the document. Mark finished drafts `stable` with a real `description`; fix stale descriptions.
4. Follow-ups: every checkbox under `## Follow-ups` in wiki and work — still true, done, owned? Promote to work only when it needs independent state.
5. Work: `pb_work_state` matches reality; closed work carries `pb_closed_on`; blocked work names real, resolving blockers.
6. Orphans: sources no document cites, wiki documents nothing links to, assets nothing references, inbox items older than they should be.
6a. Shape: several Concept documents that share a subject and the same headings are a recurring kind without a shape — propose promoting them to a type through the `setup` skill's interview; never promote silently.
6a. Shape: several Concept documents that share a subject and the same headings are a recurring kind without a shape — propose promoting them to a type through the `setup` skill's interview; never promote silently.
7. Contradictions between documents: fix in the owning document and cite the evidence.
8. Append a journal block (`## HH:MM — sweep`) with what was checked, what changed, and what needs the owner's decision.

Report counts (checked / changed / needs owner) and the specific decisions you need from a human.
