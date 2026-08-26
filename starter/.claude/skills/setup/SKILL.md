---
name: setup
description: Set up or reshape this brain through a short interview with its owner — what it is for, which kinds of things recur, whether any need tracked state, what must never be written here — then propose the smallest shape, get a yes, and apply it with portable-brain add-domain / enable-work / add-type (or by editing the manifest per BOOTSTRAP.md). Use on a fresh brain, when the owner says "set up this brain for …", or when a sweep finds a recurring kind of document without a shape.
---

# Setup

AGENTS.md "Setup" is the rule; this is the procedure. It is a conversation: ask, wait for the answer, propose, wait for a yes, then apply. Never apply a shape the owner has not seen.

## 1. Look before asking

- `date '+%Y-%m-%d %H:%M'`.
- Read START-HERE.md, `.portable-brain/profile.yaml`, `index.md`, and list `inbox/`. Whatever the owner already dropped in the inbox is the best evidence of what this brain is for: skim it and draft your guesses before asking anything.
- Note what is already configured: domains, whether work is on, types, adapters.

## 2. Interview the owner, one question at a time

Ask with your tool's question mechanism when it has one (in Claude Code, `AskUserQuestion`); otherwise ask in plain chat and stop until the owner answers. If you cannot ask at all — a headless run — write the questions and your draft answers into a journal block as an open item and stop. Do not guess a shape.

Ask only what you cannot infer, in this order, offering your draft answer each time so the owner can simply say "yes":

1. **Purpose** — "In one sentence, what is this brain for?"
2. **Recurring kinds** — "What kinds of things will keep showing up that you will want to look up by name — policies, clients, engagements, vehicles, recipes …?" Offer your guesses from the inbox and the purpose. Each becomes a candidate type; anything that will appear once stays a Concept.
3. **State** — "Do any of those need a state, an owner, and dates — something you would ask 'where does this stand?' about?" A yes means those are work types and the work module goes on.
4. **Sensitivity** — "Who else might read this folder, and is there anything that must never be written here?" Secrets are always out; owners often add compensation, health, performance, or client-confidential terms. The answers become rules.
5. **Adapters** — only if not already chosen: Obsidian? Claude Code?

Stop as soon as you have enough. Five questions is the ceiling; two is common.

## 3. Propose the smallest shape

Present one proposal, as a table, before touching anything:

- packaged domains to enable — only when most of a domain's types fit;
- work on or off;
- each new type: a singular-noun name, its group (`wiki`, `sources`, or `work`), a kebab-case plural folder, and its ordered sections — every section is a `##` heading every document of that type must carry, so keep them to what you would actually fill in (four to six is typical);
- the owner's rules, one or two sentences each.

Prefer fewer types: drop a candidate that would hold one document; merge two that would share the same sections. Explain each choice in a clause, not a paragraph. End with "Apply this?" and wait.

## 4. Apply

With the CLI, from the brain's root:

```sh
portable-brain add-domain . travel
portable-brain enable-work .
portable-brain add-type . Policy --group wiki --folder policies --sections Summary "Current term" Coverage History Follow-ups References
```

Each command edits the manifest, creates the folder, and writes the template. Without the CLI, edit `.portable-brain/profile.yaml` as BOOTSTRAP.md describes, create the folders, and copy an existing template.

Then:

- write the owner's rules under `## Owner's rules` in AGENTS.md, replacing the placeholder text and keeping the heading — including what must never be written here;
- `portable-brain index .` and `portable-brain validate .`; fix anything reported;
- append a journal block (`## HH:MM — setup`) recording the purpose, the shape, and the reason for each choice;
- tell the owner where to drop the first thing, and that "triage my inbox" is the next step.

## 5. Reshaping later

Run this again when a sweep finds several Concept documents that share a subject and the same headings, or when the owner says a kind of thing keeps recurring. Propose the promotion the same way. On a yes: add the type, then move and retype the existing documents one by one (change `type:`, move into the folder, add any missing sections), re-index, validate, and journal the migration. Never reshape silently.
