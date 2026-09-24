#!/usr/bin/env python3
"""Analyze benchmark run transcripts into analysis/summary.md, metrics.csv and PNG plots.

Usage: analysis/.venv/bin/python analyze.py
Inputs: stats.csv windows, harness transcripts (claude ~/.claude/projects, omh ~/.omp/agent/sessions),
plus each run repo's git history.
"""
import csv
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis"
import importlib
for mod in ("matplotlib", "numpy", "csv"):
    importlib.import_module(mod)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PROMPT = timezone.utc

def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=PROMPT).timestamp()

def fmt_duration(s):
    s = int(s)
    return f"{s//3600}h{(s % 3600)//60:02d}m{s % 60:02d}s"

def git(base, *args):
    return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True).stdout

def normalize_harness(h):
    """stats.csv has grown inconsistent labels over time (claude vs claude-code,
    omh vs oh-my-humanize) -- collapse them to one canonical value per harness."""
    h = (h or "").strip().lower()
    if h in ("claude-code", "claude"):
        return "claude-code"
    if h in ("omh", "oh-my-humanize"):
        return "omh"
    return h  # opencode, aider

def load_run(row):
    harness = normalize_harness(row["harness"])
    start = ts(row["start_utc"])
    cutoff = start - 15
    if harness == "claude-code":
        bases = glob.glob(str(os.path.join(str(Path.home()), ".claude", "projects", "*" + row["run"] + "*")))
    elif harness == "omh":
        # Per-run slug, matching run.sh's own collector -- a bare glob over the
        # whole sessions/ dir (the old behavior) pulls in every other omh run
        # active around the same time, silently inflating tokens/cost/calls.
        slug = "-research-ai-agent-4d-tictactoe-" + row["run"]
        bases = [os.path.join(str(Path.home()), ".omp", "agent", "sessions", slug)]
    else:
        # opencode/aider have no generic transcript source wired up here;
        # main() falls back to stats.csv's own (harness-specific-collector)
        # totals for these instead of silently reporting zero.
        bases = []
    events, tools, tool_lat, per_call_in, per_call_out = [], [], [], [], []
    for base in bases:
        for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
            if getattr(os.stat(f), "st_birthtime", os.stat(f).st_mtime) < cutoff:
                continue
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
                if isinstance(msg, dict):
                    u = msg.get("usage")
                    if isinstance(u, dict):
                        key = msg.get("id") if harness == "claude-code" else rec.get("id")
                        if key in seen:
                            continue
                        seen.add(key)
                        t = ts(rec.get("timestamp", "2026-01-01T00:00:00Z")[:19] + "Z") if rec.get("timestamp") else start
                        if harness == "claude-code":
                            tin = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
                            tout = u.get("output_tokens", 0)
                            tcached = u.get("cache_read_input_tokens", 0)
                            cost = 0.0
                        else:
                            tin = u.get("input", 0) + u.get("cacheWrite", 0)
                            tout = u.get("output", 0)
                            tcached = u.get("cacheRead", 0)
                            cost = (u.get("cost") or {}).get("total", 0.0)
                        events.append((t, tin, tout, tcached, cost))
                        per_call_in.append(tin)
                        per_call_out.append(tout)
                    role = msg.get("role", "")
                    if role == "assistant":
                        for blk in msg.get("content", []):
                            if isinstance(blk, dict) and blk.get("type") in ("tool_use", "toolCall"):
                                tools.append(blk.get("name"))
                    if role == "toolResult":
                        err = 1 if msg.get("isError") else 0
                        lat = (msg.get("details") or {}).get("wallTimeMs", 0)
                        tool_lat.append((msg.get("toolName"), lat, err))
    events.sort()
    return {"events": events, "tools": tools, "tool_lat": tool_lat,
            "per_call_in": per_call_in, "per_call_out": per_call_out}

def repo_metrics(dir_name):
    base = ROOT / dir_name
    r = {"commits": 0, "files": 0, "added": 0, "total_files": 0, "total_loc": 0}
    if not (base / ".git").exists():
        return r
    # Each run repo has its own distinct baseline commit -- a hardcoded hash
    # here matched none of them and silently produced 0/0/0 for every run.
    baseline_lines = git(base, "rev-list", "--max-parents=0", "HEAD").strip().splitlines()
    if not baseline_lines:
        return r
    baseline = baseline_lines[0]
    log = git(base, "log", "--oneline", baseline + "..HEAD").splitlines()
    r["commits"] = len(log)
    diff = git(base, "diff", "--stat", baseline)
    if ", " in diff:
        parts = [p.split() for p in diff.strip().splitlines()[-1].split(", ")]
        r["files"] = int(parts[0][0])
        r["added"] = int(parts[1][0])
    # Some early runs were squash-committed after the fact into a single
    # commit ("restored from parent repo"), so baseline == HEAD and the diff
    # above is empty even though the deliverable is real -- total tracked
    # size is the only meaningful metric for those, so always compute it too.
    files = [f for f in git(base, "ls-files").splitlines() if f and "__pycache__" not in f and not f.endswith(".pyc")]
    r["total_files"] = len(files)
    total_loc = 0
    for f in files:
        try:
            total_loc += sum(1 for _ in open(base / f, "rb"))
        except OSError:
            pass
    r["total_loc"] = total_loc
    return r

def to_num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0

def main():
    rows = list(csv.DictReader(open(ROOT / "stats.csv")))
    filled = [r for r in rows if r.get("start_utc")]
    if not filled:
        sys.exit("no filled rows in stats.csv")
    reports = []
    for row in filled:
        row = {**row, "harness": normalize_harness(row["harness"])}
        d = row["run"]
        data = load_run(row)
        repo = repo_metrics(d)
        events = data["events"]
        start = ts(row["start_utc"])
        end = ts(row["end_utc"]) if row.get("end_utc") else start + to_num(row.get("duration_s"))
        dur = end - start
        calls = len(events)
        # stats.csv is authoritative for tokens/cost -- it's collected right at
        # harness-exit time by each harness's own dedicated collector (run.sh)
        # and is what gets hand-corrected for edge cases (interrupted runs,
        # multi-segment resumes). Recomputing from raw transcripts here is
        # strictly a fallback for whatever stats.csv doesn't have, since an
        # omh session slug directory can accumulate files from more than one
        # invocation over time and a birthtime cutoff alone can't always tell
        # them apart -- that silently inflated some historical rows here.
        csv_tin, csv_tout, csv_tcached = (to_num(row.get("tokens_in")), to_num(row.get("tokens_out")),
                                           to_num(row.get("tokens_cached")))
        if csv_tin or csv_tout or csv_tcached:
            tin, tout, tcached = csv_tin, csv_tout, csv_tcached
        else:
            tin = sum(e[1] for e in events)
            tout = sum(e[2] for e in events)
            tcached = sum(e[3] for e in events)
        csv_cost = to_num(row.get("cost_usd"))
        cost = csv_cost if csv_cost else sum(e[4] for e in events)
        tool_lat = data["tool_lat"]
        tool_n = len(tool_lat) or len(data["tools"])
        tool_err_pct = 100 * (sum(t[2] for t in tool_lat) / tool_n) if tool_n else 0
        tool_avg_ms = int(np.mean([t[1] for t in tool_lat])) if tool_lat else 0
        cache_ratio = tcached / (tin + tcached) if (tin + tcached) else 0
        reports.append({**row, "repo": repo, "start": start, "end": end, "dur": dur,
                        "events": events, "calls": calls, "tin": tin, "tout": tout, "tcached": tcached,
                        "cost": cost, "tool_names": data["tools"], "tool_err_pct": tool_err_pct,
                        "tool_n": tool_n, "tool_avg_ms": tool_avg_ms, "cache_ratio": cache_ratio,
                        "per_call_in": data["per_call_in"]})
    OUT.mkdir(exist_ok=True)
    build_markdown(reports)
    build_metrics_csv(reports)
    build_plots(reports)
    print("analysis written to", OUT)

def build_markdown(reports):
    md = ["# Benchmark analysis", ""]
    md.append("| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |")
    md.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for r in reports:
        tokens_s = f"{(r['tin']+r['tout']+r['tcached'])/r['dur']:.1f}" if r["dur"] else "-"
        cost = f"${r['cost']:.4f}" if r["cost"] else "n/a"
        tpc = f"{(r['tin']+r['tout'])/r['repo']['commits']:,.0f}" if r["repo"]["commits"] else "-"
        # LOC-added-since-baseline is 0 for the handful of squash-committed
        # runs (baseline == HEAD); fall back to total tracked LOC so those
        # still get a meaningful (if less precise) tokens/line figure.
        loc_for_ratio = r["repo"]["added"] or r["repo"]["total_loc"]
        tpl = f"{(r['tin']+r['tout'])/loc_for_ratio:,.0f}" if loc_for_ratio else "-"
        md.append(f"| {r['run']} | {fmt_duration(r['dur'])} | {r['calls']} | {r['tin']:,} | {r['tout']:,} | {r['tcached']:,} "
                  f"| {r['cache_ratio']:.1%} | {tokens_s} | {cost} | {tpc} | {tpl} | {r['tool_n']} | {r['tool_err_pct']:.1f}% | {r['tool_avg_ms']} |")
    md.append("")
    md.append("## Plots")
    for f in ["tokens_over_time", "tokens_vs_cost", "cost_over_time", "tool_usage", "tokens_per_commit"]:
        if (OUT / (f + ".png")).exists():
            md.append(f"### {f.replace('_', ' ')}\n![]({f}.png)")
    md.append("")
    md.append("## Per-run insights")
    for r in reports:
        tokens = r["tin"] + r["tout"] + r["tcached"]
        loc_for_ratio = r["repo"]["added"] or r["repo"]["total_loc"]
        md.append(f"- **{r['run']}**: {fmt_duration(r['dur'])}, {r['calls']} calls, {tokens:,} tokens ({r['cache_ratio']:.1%} cached), "
                  f"{r['repo']['commits']} commits, {r['repo']['added']} lines added ({r['repo']['total_loc']} total), "
                  f"{tokens/(r['repo']['commits'] or 1):,.0f} tok/commit, "
                  f"{tokens/(loc_for_ratio or 1):,.0f} tok/line" + (f", ${r['cost']:.4f}" if r["cost"] else ""))
    (OUT / "summary.md").write_text("\n".join(md) + "\n")

def build_metrics_csv(reports):
    cols = ["run", "harness", "model", "duration_s", "api_calls", "tokens_in", "tokens_out", "tokens_cached",
            "cache_ratio", "tool_calls", "tool_err_pct", "tool_avg_ms", "cost_usd", "commits", "files_changed",
            "loc_added", "total_files", "total_loc", "tokens_per_commit", "tokens_per_line"]
    rows = [cols]
    for r in reports:
        tokens = r["tin"] + r["tout"] + r["tcached"]
        loc_for_ratio = r["repo"]["added"] or r["repo"]["total_loc"]
        rows.append([r["run"], r["harness"], r["model"], int(r["dur"]), r["calls"], r["tin"], r["tout"], r["tcached"],
                     f"{r['cache_ratio']:.4f}", r["tool_n"], f"{r['tool_err_pct']:.2f}", r["tool_avg_ms"],
                     f"{r['cost']:.4f}" if r["cost"] else "",
                     r["repo"]["commits"], r["repo"]["files"], r["repo"]["added"],
                     r["repo"]["total_files"], r["repo"]["total_loc"],
                     f"{tokens/r['repo']['commits']:.1f}" if r["repo"]["commits"] else "",
                     f"{tokens/loc_for_ratio:.1f}" if loc_for_ratio else ""])
    (OUT / "metrics.csv").write_text("\n".join(",".join(map(str, r)) for r in rows) + "\n")

def build_plots(reports):
    colors = ["#2563eb", "#16a34a", "#dc2626", "#7c3aed"]
    n = len(reports)
    fig, ax = plt.subplots(n, 2, figsize=(13, 4 * n))
    if n == 1:
        ax = [ax]
    for i, r in enumerate(reports):
        ax[i][0].set_title(r["run"])
        ev = r["events"]
        xs = [(e[0] - r["start"]) / 60 for e in ev]
        for name, idx in [("in", 1), ("out", 2), ("cached", 3)]:
            ax[i][0].plot(xs, np.cumsum([e[idx] for e in ev]) / 1e6, label=name)
        ax[i][0].set_xlabel("minutes")
        ax[i][0].set_ylabel("Mt")
        ax[i][0].legend()
        ax[i][1].bar(["in", "out", "cached"], [r["tin"] / 1e6, r["tout"] / 1e6, r["tcached"] / 1e6], color=colors[i % 4])
        ax[i][1].set_ylabel("Mt")
    fig.tight_layout()
    fig.savefig(OUT / "tokens_over_time.png", dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(n, 2, figsize=(13, 4 * n))
    if n == 1:
        ax = [ax]
    for i, r in enumerate(reports):
        ax[i][0].set_title(r["run"])
        is_cost = r["harness"] == "omh"
        series = [e[4] for e in r["events"]] if is_cost else [e[1] + e[2] + e[3] for e in r["events"]]
        ax[i][0].plot([(e[0] - r["start"]) / 60 for e in r["events"]],
                      np.cumsum(series) if is_cost else np.cumsum(series) / 1e6)
        ax[i][0].set_ylabel("$" if is_cost else "total Mt")
        names, counts = np.unique(r["tool_names"], return_counts=True) if r["tool_names"] else ([], [])
        if len(names):
            ax[i][1].barh(list(names), list(counts), color=colors[i % 4])
        ax[i][1].set_title("tool calls")
    fig.tight_layout()
    fig.savefig(OUT / ("cost_over_time.png" if any(r["harness"] == "omh" for r in reports) else "tokens_vs_cost.png"), dpi=110)
    plt.close(fig)

    fig, ax = plt.subplots(n, 2, figsize=(13, 4 * n))
    if n == 1:
        ax = [ax]
    for i, r in enumerate(reports):
        names = np.unique(r["tool_names"]) if r["tool_names"] else []
        counts = [r["tool_names"].count(name) for name in names]
        ax[i][0].set_title(r["run"])
        if len(names):
            ax[i][0].barh(names, counts, color=colors[i % 4])
        ax[i][1].hist(r["per_call_in"], bins=40, color=colors[i % 4])
        ax[i][1].set_title("tokens per api call (in)")
        ax[i][1].set_ylabel("calls")
    fig.tight_layout()
    fig.savefig(OUT / "tool_usage.png", dpi=110)
    plt.close(fig)

    if len(reports) >= 2:
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar([r["run"] for r in reports],
               [(r["tin"] + r["tout"]) / max(r["repo"]["commits"], 1) for r in reports], color=colors)
        ax.set_ylabel("tokens per commit")
        fig.tight_layout()
        fig.savefig(OUT / "tokens_per_commit.png", dpi=110)
        plt.close(fig)

main()
