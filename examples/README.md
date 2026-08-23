# Examples

- [`nursery/`](nursery/) — a **complete brain** for designing and setting up a baby nursery (`personal` domain + `work`). Read its three `journal/` days first: they are the triage receipts. The inbox was emptied except for one item deliberately left pending (a voice-memo transcript the owner still has to decide on), the PDF and photo live in `assets/` with `Source` documents that preserve them, the wiki holds the layout, palette, and safe-sleep rules, and `work/` tracks the project, a goal, and two closed decisions. It validates and indexes fresh; `tests/test_examples.py` keeps it that way. Copy it and poke at it:

  ```sh
  portable-brain inspect examples/nursery
  portable-brain validate examples/nursery
  ```

- [`manual/`](manual/) — single documents showing each domain's recipe, for copying a shape into your own brain.
