---
name: query
description: Answer a question from this brain with citations — read index.md, then the relevant wiki and work documents, then the sources they cite — and say plainly what the brain does not know. Optionally file a durable answer back into the wiki. Use when the user asks what the brain knows or thinks about something.
---

# Query

AGENTS.md and SPEC.md govern anything you file back; reading is free.

1. Read `index.md`, then the group indexes, then the relevant `wiki/` (and `work/`) documents; follow their citations into `sources/` and `assets/` before asserting anything. The index and standard links are the retrieval — do not build embeddings or side indexes.
2. Answer with standard relative links to the documents and sources you used. Separate what the brain states (cited) from your own inference, and say plainly what the brain has no evidence for.
3. If the answer is durable understanding worth keeping — a comparison, a synthesis, a decision record — offer to file it: a wiki document of a configured type with every declared section, a real `description`, citations to the sources, a link from the owning document, and a journal block. Never file guesses as knowledge.
