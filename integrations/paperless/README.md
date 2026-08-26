# Paperless-ngx → inbox

Copies documents from Paperless-ngx into a brain's `inbox/paperless/` the way a capture script should: one Markdown note per document carrying what Paperless already knows — title, correspondent, document type, tags, document date, original filename, the Paperless URL — and the OCR text. **Text only by default**: Paperless stays the system of record for the PDF, the note cites it by URL, and the brain never fills up with binaries. Pass `--with-files` to also download each archived PDF beside its note (for a self-contained brain, or when triage should spot-check the scan). Triage then does the thinking; the note's text is preserved as the Source's material.

```sh
export PAPERLESS_URL=https://paperless.example.net
export PAPERLESS_TOKEN=…            # never passed as an argument

python3 paperless_to_inbox.py ~/brain --tag insurance --dry-run
python3 paperless_to_inbox.py ~/brain --tag insurance --type "Auto Insurance" --correspondent Progressive
python3 paperless_to_inbox.py ~/brain --since 2026-08-01          # added to Paperless since a date
python3 paperless_to_inbox.py ~/brain --all --limit 50            # feed a big archive in slices
python3 paperless_to_inbox.py ~/brain --ids 411 420
python3 paperless_to_inbox.py ~/brain --tag insurance --with-files      # PDFs too
```

Filters combine as a union across kinds (any listed tag OR type OR correspondent), then `--since` and `--limit` narrow the result. Documents already captured are skipped; the record lives at `<brain>/.portable-brain/paperless-captured.json` so it travels with the brain. Use `--recapture` to pull a document again.

Standard library only. Read-only against Paperless. Feed a large archive in slices (`--limit`, one tag at a time) when you can; triage plans a campaign either way.
