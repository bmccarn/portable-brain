## What changed

<!-- One or two sentences. Link the issue if there is one. -->

## Checklist

- [ ] If this changes how a brain looks or behaves: `SPEC.md`, the scaffold documents, the code, and the tests changed together (see `AGENTS.md`).
- [ ] `SPEC.md` is still byte-identical to `src/portable_brain/resources/scaffold/SPEC.md`.
- [ ] `starter/` was regenerated with `portable-brain init starter --adapter obsidian claude --actor human:owner`, not hand-edited.
- [ ] `ruff format --check`, `ruff check`, `pyright`, and `pytest` pass locally.
- [ ] No secrets, personal data, or machine-local paths in any shipped document.
