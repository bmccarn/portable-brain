#!/bin/bash
# Portable Brain session-end gate — a Claude Code Stop hook.
#
# Fires ONCE per session (per session_id) when the agent tries to stop while working
# inside a brain: it blocks that first stop with a request to follow AGENTS.md
# "Session end", and includes measured brain state so the session need not gather it.
# It never re-blocks a continuation of its own block (stop_hook_active), and it is
# agnostic about where the brain lives: it walks up from $CLAUDE_PROJECT_DIR (or $PWD)
# to the nearest directory containing .portable-brain/profile.yaml. Outside a brain it
# exits silently. Registered by .claude/settings.json, which travels with the brain.
#
# Edit the SENTINEL line to change "once per session" into "every stop".
# Set PORTABLE_BRAIN_HEADLESS=1 to disable the gate for scripted runs.

INPUT=$(cat)

# A headless runner (see integrations/claude-code/triage-campaign.sh) journals each pass itself.
[ -n "${PORTABLE_BRAIN_HEADLESS:-}" ] && exit 0

BRAIN=""
d="${CLAUDE_PROJECT_DIR:-$PWD}"
while [ -n "$d" ] && [ "$d" != "/" ]; do
  if [ -f "$d/.portable-brain/profile.yaml" ]; then BRAIN="$d"; break; fi
  d=$(dirname "$d")
done
[ -n "$BRAIN" ] || exit 0

SESSION=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    d = {}
print("ACTIVE" if d.get("stop_hook_active") else d.get("session_id", ""))' 2>/dev/null)
[ "$SESSION" = "ACTIVE" ] && exit 0
[ -z "$SESSION" ] && exit 0

SENTINEL="${TMPDIR:-/tmp}/portable-brain-session-end-${SESSION}"
[ -f "$SENTINEL" ] && exit 0
: > "$SENTINEL" 2>/dev/null

TODAY=$(date '+%Y-%m-%d'); NOW=$(date '+%H:%M')
PENDING=$(find "$BRAIN/inbox" -type f ! -name index.md ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')
if [ -f "$BRAIN/journal/$TODAY.md" ]; then JOURNAL="exists"; else JOURNAL="missing"; fi
STATE="Brain: $BRAIN. Now (measured): $TODAY $NOW. Inbox pending: $PENDING. Today's journal ($TODAY.md): $JOURNAL."
if command -v portable-brain >/dev/null 2>&1; then
  if portable-brain validate "$BRAIN" >/dev/null 2>&1; then V="passes"; else V="reports issues"; fi
  if portable-brain index "$BRAIN" --check >/dev/null 2>&1; then I="fresh"; else I="stale"; fi
  STATE="$STATE Validation: $V. Indexes: $I."
fi
if [ -d "$BRAIN/.git" ]; then
  DIRTY=$(git -C "$BRAIN" status --porcelain 2>/dev/null | head -8)
  AHEAD=$(git -C "$BRAIN" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "n/a")
  if [ -n "$DIRTY" ]; then
    STATE="$STATE Git: uncommitted yes, unpushed $AHEAD. Dirty: $(printf '%s' "$DIRTY" | tr '\n' ' ' | cut -c1-300)"
  else
    STATE="$STATE Git: uncommitted none, unpushed $AHEAD."
  fi
fi

REASON="Session-end review for this Portable Brain (fires once per session). $STATE Review whether this session did work worth capturing, then follow AGENTS.md 'Session end' (the session-end skill has the checklist): triage pending inbox items; update current state and Follow-ups in the documents you touched; append a journal block to journal/$TODAY.md with the heading time from date '+%H:%M' and the line \`session: claude-code $SESSION\`; regenerate indexes and validate; commit if this brain is a git repository (leave another session's uncommitted work alone and say so). If nothing brain-worthy happened and the state above is clean, say so briefly and stop — this gate will not fire again this session."

python3 -c 'import json, sys; print(json.dumps({"decision": "block", "reason": sys.argv[1]}))' "$REASON"
exit 0
