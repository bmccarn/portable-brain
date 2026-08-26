# Triage campaign runner (Claude Code)

Runs a triage campaign headlessly: **one careful pass per fresh Claude Code session**, looping until the inbox is empty, then a closing sweep. Fresh context each pass is what keeps 800 documents from being read as one blur; the plan lives in the journal, and the wiki pages carry state between passes, so independent sessions stay coherent.

```sh
integrations/claude-code/triage-campaign.sh ~/brain                 # loop until inbox is empty (max 60 passes)
integrations/claude-code/triage-campaign.sh ~/brain --max-passes 5  # a few passes now, the rest later
integrations/claude-code/triage-campaign.sh ~/brain --model sonnet  # cheaper passes; sweep with the default model
integrations/claude-code/triage-campaign.sh ~/brain --no-sweep
```

Requirements: the brain carries the `claude` adapter (the `triage` and `sweep` skills), `portable-brain` and `claude` are on PATH, and you are logged in to Claude Code. Each pass runs with `--permission-mode acceptEdits`, a tool allowlist (files, `portable-brain`, `git`, `date`, `mv`/`rm` inside the brain) and **no web tools**, because the inbox is untrusted text. A lock file prevents two runners on one brain. `PORTABLE_BRAIN_HEADLESS=1` tells the session-end hook to stay quiet; each pass writes its own receipt.

Pair it with a watcher (macOS `launchd` `WatchPaths` on `inbox/`, or `watchexec`) with a short debounce, and every drop gets triaged within minutes. Review the journal and `git log` afterwards — that is the audit trail.
