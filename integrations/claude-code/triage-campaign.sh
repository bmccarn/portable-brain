#!/bin/bash
# Portable Brain triage campaign runner: one careful pass per fresh Claude Code session,
# looping until the inbox is empty, then a closing sweep. See README.md beside this file.
set -u

usage() { echo "usage: $0 BRAIN [--max-passes N] [--model MODEL] [--sweep-model MODEL] [--no-sweep] [--dry-run]" >&2; exit 2; }
[ $# -ge 1 ] || usage
BRAIN=$(cd "$1" 2>/dev/null && pwd) || { echo "not a directory: $1" >&2; exit 2; }; shift
MAX_PASSES=60; MODEL=""; SWEEP_MODEL=""; SWEEP=1; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --max-passes) MAX_PASSES="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --sweep-model) SWEEP_MODEL="$2"; shift 2 ;;
    --no-sweep) SWEEP=0; shift ;;
    --dry-run) DRY=1; shift ;;
    *) usage ;;
  esac
done
[ -f "$BRAIN/.portable-brain/profile.yaml" ] || { echo "not a brain: $BRAIN" >&2; exit 2; }
[ -f "$BRAIN/.claude/skills/triage/SKILL.md" ] || { echo "brain lacks the claude adapter (no .claude/skills/triage)" >&2; exit 2; }
command -v claude >/dev/null || { echo "claude is not on PATH" >&2; exit 2; }
command -v portable-brain >/dev/null || { echo "portable-brain is not on PATH" >&2; exit 2; }

LOCK="$BRAIN/.portable-brain/triage-campaign.lock"
STOP="$BRAIN/.portable-brain/triage-campaign.stop"
rm -f "$STOP"
if [ -e "$LOCK" ] && kill -0 "$(cat "$LOCK" 2>/dev/null)" 2>/dev/null; then echo "another runner holds $LOCK" >&2; exit 1; fi
echo $$ > "$LOCK"; trap 'rm -f "$LOCK"' EXIT

pending() { find "$BRAIN/inbox" -type f ! -name index.md ! -name '.*' 2>/dev/null | wc -l | tr -d ' '; }
ALLOWED="Read,Edit,Write,Glob,Grep,LS,Bash(portable-brain:*),Bash(git:*),Bash(date:*),Bash(mv:*),Bash(rm:*),Bash(mkdir:*),Bash(ls:*),Bash(find:*),Bash(wc:*),Bash(head:*),Bash(tail:*),Bash(cat:*),Bash(file:*),Bash(unzip:*),Bash(textutil:*),Bash(pandoc:*),AskUserQuestion"
DISALLOWED="WebFetch,WebSearch,Task"
PASS_PROMPT='Run the triage skill for this brain. If today'"'"'s or yesterday'"'"'s journal already holds a triage plan, do exactly the next pass in it (one pass only) and stop. Otherwise, if the inbox is large, survey it, write the plan as a journal block, do pass one only, and stop. If the inbox is small, triage all of it. Every pass ends with portable-brain index ., portable-brain validate ., a journal receipt, and a git commit when this brain is a repository. You cannot ask the owner questions in this run: leave anything unclassifiable in the inbox and say so in the journal.'
SWEEP_PROMPT='Run the sweep skill over every page the recent triage campaign touched (see the triage plan and pass blocks in the journal). Check each page'"'"'s claims against related pages for contradictions, fix what the evidence supports, flag what needs the owner, journal the sweep, regenerate indexes, validate, and commit when this brain is a repository.'

run_session() {  # $1 prompt, $2 model, $3 label
  local extra=(); [ -n "$2" ] && extra=(--model "$2")
  local stamp="Measured time at launch: $(date '+%Y-%m-%d %H:%M %Z'). Run date again immediately before writing any journal heading; never estimate a time."
  ( cd "$BRAIN" && env -u CLAUDECODE -u CLAUDE_CODE_ENTRYPOINT PORTABLE_BRAIN_HEADLESS=1 \
      claude -p "$stamp $1" --permission-mode acceptEdits --allowedTools "$ALLOWED" --disallowedTools "$DISALLOWED" \
      --output-format json "${extra[@]}" < /dev/null ) > "$BRAIN/.portable-brain/last-$3.json" 2>&1
  local code=$?
  python3 - "$BRAIN/.portable-brain/last-$3.json" <<'PY'
import json, sys
raw = open(sys.argv[1], encoding="utf-8", errors="replace").read()
try:
    d = json.loads(raw[raw.index("{"):]) if "{" in raw else {}
except Exception:
    d = {}
print(f"    result: {(d.get('result') or raw[:300]).strip()[:400]}")
print(f"    turns={d.get('num_turns')} cost_usd={d.get('total_cost_usd')} session={d.get('session_id')} error={d.get('is_error')}")
PY
  return $code
}

before=$(pending); echo "brain: $BRAIN"; echo "pending: $before"
[ "$before" -eq 0 ] && { echo "inbox is empty; nothing to do"; exit 0; }
[ "$DRY" -eq 1 ] && { echo "dry run: would run up to $MAX_PASSES pass(es), then sweep=$SWEEP"; exit 0; }
pass=0; stopped=""
while [ "$pass" -lt "$MAX_PASSES" ]; do
  if [ -e "$STOP" ]; then stopped="stop file"; rm -f "$STOP"; echo "stop file found; not starting another pass"; break; fi
  left=$(pending); [ "$left" -eq 0 ] && break
  pass=$((pass + 1)); echo "== pass $pass ($(date '+%H:%M'), $left pending)"
  run_session "$PASS_PROMPT" "$MODEL" "pass" || echo "    (claude exited non-zero)"
  after=$(pending); echo "    pending now: $after"
  if [ "$after" -ge "$left" ]; then echo "    no progress this pass; stopping so a human can look" >&2; stopped="no progress"; break; fi
done
left=$(pending); echo "passes run: $pass; pending: $left"
if [ "$SWEEP" -eq 1 ] && [ "$pass" -gt 0 ]; then
  echo "== closing sweep ($(date '+%H:%M'))"; run_session "$SWEEP_PROMPT" "${SWEEP_MODEL:-$MODEL}" "sweep" || echo "    (claude exited non-zero)"
fi
# Exit codes: 0 inbox empty · 3 stopped with items pending (max passes or stop file) · 1 a pass made no progress.
if [ "$left" -eq 0 ]; then exit 0; fi
if [ "$stopped" = "no progress" ]; then exit 1; fi
echo "stopped with $left pending ($([ -n "$stopped" ] && echo "$stopped" || echo "max passes reached")); run again to continue"
exit 3
