# Integrations

Capture and automation scripts that feed or drive a brain. They are not part of the `portable-brain` package and a brain never depends on them; they are the "many writers to `inbox/`, one maintainer for everything else" pattern made concrete.

- [`paperless/`](paperless/) — copy documents from a Paperless-ngx instance into a brain's inbox (archived PDF plus a sidecar with the metadata and OCR text Paperless already has), filtered by tag, type, correspondent, date, or id, incrementally.
- [`claude-code/`](claude-code/) — run a triage campaign headlessly: one careful pass per fresh Claude Code session, looping until the inbox is empty, then a sweep.
