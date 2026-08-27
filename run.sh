#!/usr/bin/env bash
# run.sh: sanity-check an agent directory, launch the harness with the task
# prompt, and record duration/tokens/cost into stats.csv when it exits.
#
# Targets are rows in the TARGETS table below. New harness/model combos go there too.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSV="$ROOT/stats.csv"
PROMPT='Read TASK.md and start planning and executing the task.'

# Target table: DIR:HARNESS:MODEL. Add new combos here.
TARGETS=(
  claude-code-opus5:claude:opus
  claude-code-sonnet:claude:sonnet
  oh-my-humanize-qwen38:omh:openrouter/qwen/qwen3.8-27b
  oh-my-humanize-kimi-k3:omh:openrouter/moonshotai/kimi-k3
  oh-my-humanize-qwen-max:omh:openrouter/qwen/qwen3.8-max
  oh-my-humanize-ox-alpha:omh:openrouter/z-ai/glm-5.3-flash
  oh-my-humanize-glm-53:omh:openrouter/z-ai/glm-5.3
  oh-my-humanize-codex:omh:openrouter/openai/gpt-5.5
  opencode-qwen:opencode:openrouter/qwen/qwen3.8-27b
  opencode-kimi:opencode:openrouter/moonshotai/kimi-k3
  opencode-opus:opencode:openrouter/anthropic/claude-opus-5
  aider-qwen:aider:openrouter/qwen/qwen3.8-27b
  aider-kimi:aider:openrouter/moonshotai/kimi-k3
  opencode-sonnet:opencode:openrouter/anthropic/claude-sonnet-5
  opencode-qwen-max:opencode:openrouter/qwen/qwen3.8-max
  opencode-glm-53:opencode:openrouter/z-ai/glm-5.3
  opencode-codex:opencode:openrouter/openai/gpt-5.5
  aider-opus:aider:openrouter/anthropic/claude-opus-5
  aider-sonnet:aider:openrouter/anthropic/claude-sonnet-5
  aider-qwen-max:aider:openrouter/qwen/qwen3.8-max
  aider-glm-53:aider:openrouter/z-ai/glm-5.3
  aider-codex:aider:openrouter/openai/gpt-5.5
  oh-my-humanize-sonnet:omh:openrouter/anthropic/claude-sonnet-5
)

usage() {
  echo "Usage: run.sh <target> [--reset] [--dry-run] [--new]"
  echo
  echo "Targets:"
  for t in "${TARGETS[@]}"; do
    IFS=':' read -r dir harness model <<< "$t"
    printf "  %-24s %s, %s\n" "$dir" "$harness" "$model"
  done
  echo
  echo "Options:"
  echo "  --new       create the agent dir (git init + baseline + TASK.md) and add a row to stats.csv"
  echo "  --reset     restore the agent dir to its baseline commit before the run"
  echo "  --dry-run   run the sanity checks and print the launch command, start nothing"
  echo "  -h, --help  show this help"
  echo
  echo "On harness exit (normal or Ctrl-C) the script records the run in stats.csv:"
  echo "start_utc, end_utc, duration_s, tokens_in, tokens_out, tokens_cached, and"
  echo "cost_usd for the OpenRouter runs. result and notes stay yours to fill."
}

die() { echo "run.sh: $*" >&2; exit 1; }

TARGET=""
RESET=0
DRY_RUN=0
NEW=0
for arg in "$@"; do
  case "$arg" in
    --reset) RESET=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --new) NEW=1 ;;
    -h|--help) usage; exit 0 ;;
    *) [ -z "$TARGET" ] || die "unexpected argument: $arg"
       TARGET="$arg" ;;
  esac
done
[ -n "$TARGET" ] || { usage; exit 1; }

# ---- resolve target ---------------------------------------------------------

resolve_target() {
  local t
  t="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"
  # exact dir match first
  for e in "${TARGETS[@]}"; do
    IFS=':' read -r dir harness model <<< "$e"
    if [ "$t" = "$dir" ]; then
      echo "$dir" "$harness" "$model"
      return 0
    fi
  done
  # then short name or substring
  for e in "${TARGETS[@]}"; do
    IFS=':' read -r dir harness model <<< "$e"
    local short
    short="${dir#oh-my-humanize-}"
    short="${short#claude-code-}"
    short="${short#opencode-}"
    short="${short#aider-}"
    if [ "$t" = "$short" ] || [[ "$t" == *"$short"* ]] || [[ "$t" == *"$model"* ]]; then
      echo "$dir" "$harness" "$model"
      return 0
    fi
  done
  return 1
}

RESOLVED=""
RESOLVED="$(resolve_target "$TARGET")" || true
if [ -z "$RESOLVED" ]; then
  echo "run.sh: unknown target: $TARGET"
  echo
  usage
  exit 1
fi
read -r DIR HARNESS MODEL <<< "$RESOLVED"

# ---- --new: create the agent dir ---------------------------------------------

if [ "$NEW" -eq 1 ]; then
  if [ -d "$ROOT/$DIR" ] && [ -f "$ROOT/$DIR/.git/HEAD" ]; then
    die "$DIR already exists"
  fi
  mkdir -p "$ROOT/$DIR"
  cd "$ROOT/$DIR"
  git init -b main
  git config user.name "vbraye-pop"
  git config user.email "valerien.braye@proseonpixels.com"
  cp "$ROOT/TASK.md" .
  git add TASK.md
  git commit -m "chore: baseline"
  git config core.autocrlf input
  grep -q "^$DIR," "$CSV" || echo "$DIR,$HARNESS,$MODEL,$( [ "$HARNESS" = "claude" ] && echo "anthropic,flat-monthly" || echo "openrouter,per-token" ),,,,,,,," >> "$CSV"
  echo "created $DIR (baseline $(git rev-parse HEAD))"
  exit 0
fi

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
if [ "$STATUS" != "?? TASK.md" ] && [ -n "$STATUS" ]; then
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
tin = tout = tcached = 0
cost = 0.0
found_data = False

if harness == "claude":
    bases = glob.glob(os.path.expanduser(os.path.join("~", ".claude", "projects", "*" + d + "*")))
    files = []
    for base in bases:
        for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
            st = os.stat(f)
            if getattr(st, "st_birthtime", st.st_mtime) >= cutoff:
                files.append(f)
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
            mid = msg.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            tin += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            tout += u.get("output_tokens", 0)
            tcached += u.get("cache_read_input_tokens", 0)
    found_data = bool(files)

elif harness == "omh":
    base = os.path.expanduser(os.path.join("~", ".omp", "agent", "sessions"))
    slug = "-research-ai-agent-4d-tictactoe-" + d
    files = []
    for f in glob.glob(os.path.join(base, slug, "*.jsonl")):
        st = os.stat(f)
        if getattr(st, "st_birthtime", st.st_mtime) >= cutoff:
            files.append(f)
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
            rid = rec.get("id")
            if rid in seen:
                continue
            seen.add(rid)
            tin += u.get("input", 0) + u.get("cacheWrite", 0)
            tout += u.get("output", 0)
            tcached += u.get("cacheRead", 0)
            cost += (u.get("cost") or {}).get("total", 0)
    found_data = bool(files)

elif harness == "opencode":
    import sqlite3
    db_path = os.path.expanduser(os.path.join("~", ".local", "share", "opencode", "opencode.db"))
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        # find sessions for this project dir created after cutoff
        rows_db = conn.execute(
            "SELECT data FROM message WHERE time_created > ? ORDER BY time_created",
            (int(cutoff * 1000),)).fetchall()
        for (data_str,) in rows_db:
            try:
                data = json.loads(data_str)
            except Exception:
                continue
            path = data.get("path", {})
            cwd = path.get("cwd", "")
            if d not in cwd:
                continue
            tokens = data.get("tokens", {})
            cache = tokens.get("cache", {})
            tin += tokens.get("input", 0) + cache.get("write", 0)
            tout += tokens.get("output", 0)
            tcached += cache.get("read", 0)
            cost += data.get("cost", 0) or 0
            found_data = True
        conn.close()

elif harness == "aider":
    # aider has no structured per-message token store; duration only
    hist = os.path.join(root, d, ".aider.chat.history.md")
    found_data = os.path.exists(hist)

if not found_data:
    print(f"warning: no session data found for {d}, stats.csv left untouched")
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
        if harness in ("omh", "opencode"):
            row[idx["cost_usd"]] = f"{cost:.4f}"
        found = True
        break
if found:
    with open(csv_path, "w", newline="") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)

print(f"duration:   {duration}s ({start_utc} -> {end_utc})")
print(f"tokens:     in={tin} out={tout} cached={tcached}")
if harness in ("omh", "opencode"):
    print(f"cost:       ${cost:.4f}")
elif harness == "aider":
    print(f"cost:       n/a (aider does not expose per-message cost)")
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
elif [ "$HARNESS" = "opencode" ]; then
  opencode run --model "$MODEL" --agent build "$PROMPT Work autonomously until the task is fully complete."
elif [ "$HARNESS" = "aider" ]; then
  aider --model "$MODEL" --yes-always --message "$PROMPT Work autonomously until the task is fully complete."
else
  export PATH="$HOME/.bun/bin:$PATH"
  omh --model "$MODEL" "$PROMPT"
fi
