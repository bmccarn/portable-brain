# Contributing

Thanks for looking. Portable Brain is small on purpose; the best contributions keep it that way.

**Read [AGENTS.md](AGENTS.md) first** — it is the development protocol, and it is short. The gist:

- The file protocol is the product. `SPEC.md` is the contract; the documents under `src/portable_brain/resources/scaffold/` ship inside every brain; the Python command is an optional adapter.
- A semantic change updates the spec, the scaffold, the code, and the tests **together**. `SPEC.md` stays byte-identical to its scaffold copy. `starter/` is generated — regenerate it with `init`, never edit it by hand.
- Keep the human surface plain. Precision belongs in `SPEC.md` and `AGENTS.md`; `README.md` and `START-HERE.md` are for people.
- The command exists for the AI, not for people. Prefer improvements an agent can act on over new human-facing commands.

## Setup

```sh
uv sync --extra dev
uv run ruff format --check src tests && uv run ruff check src tests
uv run pyright src tests
uv run pytest -q
```

CI runs exactly those on Ubuntu and macOS for Python 3.11–3.13, plus a wheel build and smoke test.

## Changes to the spec

Open an issue before a pull request if you want to change what a brain *means* — a new group, type rule, workflow field, or validation rule. Additive, compatible changes are welcome; breaking ones need a new major version and a note in `MIGRATIONS.md`.

## Security

See [SECURITY.md](SECURITY.md). Report a suspected vulnerability privately to the maintainer before public disclosure.
