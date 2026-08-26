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

BASELINE = "1e40f677"
PROMPT = timezone.utc

def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=PROMPT).timestamp()

def fmt_duration(s):
    s = int(s)
    return f"{s//3600}h{(s % 3600)//60:02d}m{s % 60:02d}s"

def git(base, *args):
    return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True).stdout

def load_run(row):
    harness = row["harness"]
    start = ts(row["start_utc"])
    cutoff = start - 15
    if harness == "claude-code":
        bases = glob.glob(str(os.path.join(str(Path.home()), ".claude", "projects", "*" + row["run"] + "*")))
    else:
        bases = [os.path.join(str(Path.home()), ".omp", "agent", "sessions")]
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
    r = {"commits": 0, "files": 0, "added": 0}
    if not (base / ".git").exists():
        return r
    log = git(base, "log", "--oneline", BASELINE + "..HEAD").splitlines()
    r["commits"] = len(log)
    diff = git(base, "diff", "--stat", BASELINE)
    if ", " in diff:
        parts = [p.split() for p in diff.strip().splitlines()[-1].split(", ")]
        r["files"] = int(parts[0][0])
        r["added"] = int(parts[1][0])
    return r

def main():
    rows = list(csv.DictReader(open(ROOT / "stats.csv")))
    filled = [r for r in rows if r.get("start_utc")]
    if not filled:
        sys.exit("no filled rows in stats.csv")
    reports = []
    for row in filled:
        d = row["run"]
        data = load_run(row)
        repo = repo_metrics(d)
        events = data["events"]
        start, end = ts(row["start_utc"]), ts(row["end_utc"])
        dur = end - start
        calls = len(events)
        tin = sum(e[1] for e in events)
        tout = sum(e[2] for e in events)
        tcached = sum(e[3] for e in events)
        cost = sum(e[4] for e in events)
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
        cost = f"${r['cost']:.4f}" if r["harness"] == "oh-my-humanize" else "n/a"
        tpc = f"{(r['tin']+r['tout'])/r['repo']['commits']:,.0f}" if r["repo"]["commits"] else "-"
        tpl = f"{(r['tin']+r['tout'])/r['repo']['added']:,.0f}" if r["repo"]["added"] else "-"
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
        md.append(f"- **{r['run']}**: {fmt_duration(r['dur'])}, {r['calls']} calls, {tokens:,} tokens ({r['cache_ratio']:.1%} cached), "
                  f"{r['repo']['commits']} commits, {r['repo']['added']} lines, {tokens/r['repo']['commits']:,.0f} tok/commit, "
                  f"{tokens/r['repo']['added']:,.0f} tok/line" + (f", ${r['cost']:.4f}" if r["harness"] == "oh-my-humanize" else ""))
    (OUT / "summary.md").write_text("\n".join(md) + "\n")

def build_metrics_csv(reports):
    cols = ["run", "harness", "model", "duration_s", "api_calls", "tokens_in", "tokens_out", "tokens_cached",
            "cache_ratio", "tool_calls", "tool_err_pct", "tool_avg_ms", "cost_usd", "commits", "files_changed",
            "loc_added", "tokens_per_commit", "tokens_per_line"]
    rows = [cols]
    for r in reports:
        tokens = r["tin"] + r["tout"] + r["tcached"]
        rows.append([r["run"], r["harness"], r["model"], int(r["dur"]), r["calls"], r["tin"], r["tout"], r["tcached"],
                     f"{r['cache_ratio']:.4f}", r["tool_n"], f"{r['tool_err_pct']:.2f}", r["tool_avg_ms"],
                     f"{r['cost']:.4f}" if r["harness"] == "oh-my-humanize" else "",
                     r["repo"]["commits"], r["repo"]["files"], r["repo"]["added"],
                     f"{tokens/r['repo']['commits']:.1f}" if r["repo"]["commits"] else "",
                     f"{tokens/r['repo']['added']:.1f}" if r["repo"]["added"] else ""])
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
        is_cost = r["harness"] == "oh-my-humanize"
        series = [e[4] for e in r["events"]] if is_cost else [e[1] + e[2] + e[3] for e in r["events"]]
        ax[i][0].plot([(e[0] - r["start"]) / 60 for e in r["events"]],
                      np.cumsum(series) if is_cost else np.cumsum(series) / 1e6)
        ax[i][0].set_ylabel("$" if is_cost else "total Mt")
        names, counts = np.unique(r["tool_names"], return_counts=True) if r["tool_names"] else ([], [])
        if len(names):
            ax[i][1].barh(list(names), list(counts), color=colors[i % 4])
        ax[i][1].set_title("tool calls")
    fig.tight_layout()
    fig.savefig(OUT / ("cost_over_time.png" if any(r["harness"] == "oh-my-humanize" for r in reports) else "tokens_vs_cost.png"), dpi=110)
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
