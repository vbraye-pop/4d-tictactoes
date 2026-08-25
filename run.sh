#!/usr/bin/env bash
# run.sh: sanity-check an agent directory, launch the harness with the task
# prompt, and record duration/tokens/cost into stats.csv when it exits.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV="$ROOT/stats.csv"
PROMPT='Read TASK.md and start planning and executing the task.'

MODEL_QWEN="openrouter/qwen/qwen3.8-27b"
MODEL_KIMI="openrouter/moonshotai/kimi-k3"

usage() {
  cat <<EOF
Usage: run.sh <target> [--reset] [--dry-run]

Targets (any string containing the name matches):
  opus    Claude Code, model opus                  in claude-code-opus5/
  qwen    omh, $MODEL_QWEN
                                                              in oh-my-humanize-qwen38/
  kimi    omh, $MODEL_KIMI
                                                              in oh-my-humanize-kimi-k3/

Options:
  --reset     restore the agent dir to its baseline commit before the run
              (tracked files reset, untracked files removed except TASK.md)
  --dry-run   run the sanity checks and print the launch command, start nothing
  -h, --help  show this help

On harness exit (normal or Ctrl-C) the script records the run in stats.csv:
start_utc, end_utc, duration_s, tokens_in, tokens_out, tokens_cached, and
cost_usd for the OpenRouter runs. result and notes stay yours to fill.
EOF
}

die() { echo "run.sh: $*" >&2; exit 1; }

TARGET=""
RESET=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) [ -z "$TARGET" ] || die "unexpected argument: $arg"
       TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || { usage; exit 1; }

T="$(printf '%s' "$TARGET" | tr '[:upper:]' '[:lower:]')"
case "$T" in
  opus|claude*|*opus*)
    DIR="claude-code-opus5"; HARNESS="claude"; MODEL="opus" ;;
  qwen*|*qwen*)
    DIR="oh-my-humanize-qwen38"; HARNESS="omh"; MODEL="$MODEL_QWEN" ;;
  kimi*|*kimi*)
    DIR="oh-my-humanize-kimi-k3"; HARNESS="omh"; MODEL="$MODEL_KIMI" ;;
  *) usage; echo; die "unknown target: $TARGET" ;;
esac

# ---- sanity checks ----------------------------------------------------------

[ -f "$CSV" ] || die "stats.csv not found at $CSV"
[ -d "$ROOT/$DIR/.git" ] || die "$DIR is not a git repo"
[ -f "$ROOT/$DIR/TASK.md" ] || die "TASK.md missing in $DIR"
command -v "$HARNESS" >/dev/null || die "$HARNESS not found on PATH"
command -v python3 >/dev/null || die "python3 not found on PATH"
grep -q "^$DIR," "$CSV" || die "no row for $DIR in stats.csv"

git_ok() { git -C "$ROOT/$DIR" "$@"; }

BASELINE="$(git_ok rev-list --max-parents=0 HEAD)"
if [ "$RESET" -eq 1 ]; then
  echo "resetting $DIR to baseline $BASELINE"
  git_ok reset --hard "$BASELINE"
  git_ok clean -fd -e TASK.md
fi
HEAD="$(git_ok rev-parse HEAD)"
STATUS="$(git_ok status --porcelain)"

if [ "$HEAD" != "$BASELINE" ]; then
  die "$DIR is not at its baseline (HEAD $HEAD, baseline $BASELINE). Pass --reset to restore."
fi
if [ "$STATUS" != "?? TASK.md" ]; then
  die "$DIR working tree is not pristine:
$STATUS
Pass --reset to restore the baseline."
fi

if [ "$DRY_RUN" -eq 1 ]; then
  echo "all checks passed for $DIR"
  echo "would run: cd $ROOT/$DIR"
  echo "  $HARNESS --model $MODEL \"$PROMPT\""
  exit 0
fi

# ---- launch -----------------------------------------------------------------

STATE_FILE="$ROOT/.run-state-$DIR"
START_EPOCH="$(date -u +%s)"
START_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$STATE_FILE" <<EOF
{"root": "$ROOT", "dir": "$DIR", "harness": "$HARNESS", "start_epoch": $START_EPOCH, "start_utc": "$START_UTC"}
EOF

collect_stats() {
  [ -f "$STATE_FILE" ] || return 0
  END_EPOCH="$(date -u +%s)"
  END_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "recording stats for $DIR"
  python3 - "$STATE_FILE" "$CSV" "$END_EPOCH" "$END_UTC" <<'PYEOF'
import csv
import glob
import json
import os
import sys

state = json.loads(open(sys.argv[1]).read())
csv_path = sys.argv[2]
end_epoch = int(sys.argv[3])
end_utc = sys.argv[4]
root, d, harness = state["root"], state["dir"], state["harness"]
start_epoch = state["start_epoch"]
start_utc = state["start_utc"]
duration = end_epoch - start_epoch

cutoff = start_epoch - 15
if harness == "claude":
    bases = glob.glob(os.path.expanduser(os.path.join("~", ".claude", "projects", "*" + d + "*")))
else:
    bases = [os.path.expanduser(os.path.join("~", ".omp", "agent", "sessions"))]

files = []
for base in bases:
    for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
        st = os.stat(f)
        born = getattr(st, "st_birthtime", st.st_mtime)
        if born >= cutoff:
            files.append(f)

tin = tout = tcached = 0
cost = 0.0
for f in files:
    seen = set()
    for line in open(f, errors="ignore"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        msg = rec.get("message")
        if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
            continue
        u = msg["usage"]
        if harness == "claude":
            mid = msg.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            tin += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            tout += u.get("output_tokens", 0)
            tcached += u.get("cache_read_input_tokens", 0)
        else:
            rid = rec.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            tin += u.get("input", 0) + u.get("cacheWrite", 0)
            tout += u.get("output", 0)
            tcached += u.get("cacheRead", 0)
            cost += (u.get("cost") or {}).get("total", 0)

if not files:
    print(f"warning: no session transcripts created in the run window, stats.csv left untouched")
    print(f"duration {duration}s ({start_utc} -> {end_utc})")
    sys.exit(0)

rows = list(csv.reader(open(csv_path)))
idx = {h: i for i, h in enumerate(rows[0])}
found = False
for row in rows[1:]:
    if row and row[0] == d:
        row[idx["start_utc"]] = start_utc
        row[idx["end_utc"]] = end_utc
        row[idx["duration_s"]] = str(duration)
        row[idx["tokens_in"]] = str(tin)
        row[idx["tokens_out"]] = str(tout)
        row[idx["tokens_cached"]] = str(tcached)
        if harness == "omh":
            row[idx["cost_usd"]] = f"{cost:.4f}"
        found = True
        break
if found:
    with open(csv_path, "w", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)

print(f"duration:   {duration}s ({start_utc} -> {end_utc})")
print(f"tokens:     in={tin} out={tout} cached={tcached}")
if harness == "omh":
    print(f"cost:       ${cost:.4f}")
else:
    print(f"cost:       n/a (flat monthly subscription)")
print(f"csv updated: {os.path.relpath(csv_path, root)}")
print(f"inspect:    git -C {os.path.join(root, d)} log --oneline")
PYEOF
  rm -f "$STATE_FILE"
}
trap collect_stats EXIT

echo "starting $HARNESS run for $DIR"
echo "model:    $MODEL"
echo "started:  $START_UTC"
echo "stats are recorded when the harness exits"
cd "$ROOT/$DIR"
if [ "$HARNESS" = "claude" ]; then
  claude --model "$MODEL" "$PROMPT"
else
  omh --model "$MODEL" "$PROMPT"
fi
