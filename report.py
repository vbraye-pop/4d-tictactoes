#!/usr/bin/env python3
"""Generate the deep benchmark report (Typst -> PDF) from analysis data.

Usage: analysis/.venv/bin/python report.py
Requires: semantic.py and analyze.py run first; typst on PATH.
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "report"
OUT.mkdir(exist_ok=True)
FIG = OUT / "fig"
FIG.mkdir(exist_ok=True)

RUN_ORDER = ["claude-code-opus5", "oh-my-humanize-qwen38", "oh-my-humanize-kimi-k3",
             "oh-my-humanize-ox-alpha", "oh-my-humanize-qwen-max", "oh-my-humanize-glm-53",
             "oh-my-humanize-codex", "claude-code-sonnet"]
NICE = {
    "claude-code-opus5": "Claude Code x Opus 5",
    "oh-my-humanize-qwen38": "omh x Qwen 3.8-27B",
    "oh-my-humanize-kimi-k3": "omh x Kimi K3",
    "oh-my-humanize-ox-alpha": "omh x GLM-5.3-flash",
    "oh-my-humanize-qwen-max": "omh x Qwen 3.8 Max",
    "oh-my-humanize-glm-53": "omh x GLM-5.3",
    "oh-my-humanize-codex": "omh x GPT-5.5",
    "claude-code-sonnet": "Claude Code x Sonnet 5",
}
COLORS = {
    "claude-code-opus5": "#2563eb",
    "oh-my-humanize-qwen38": "#dc2626",
    "oh-my-humanize-kimi-k3": "#16a34a",
    "oh-my-humanize-ox-alpha": "#9333ea",
    "oh-my-humanize-qwen-max": "#ea580c",
    "oh-my-humanize-glm-53": "#0d9488",
    "oh-my-humanize-codex": "#64748b",
    "claude-code-sonnet": "#0891b2",
}

sem = json.loads((ROOT / "analysis" / "semantic.json").read_text())
metrics = list(csv.DictReader(open(ROOT / "analysis" / "metrics.csv")))
runs = [r for r in metrics if r["run"] in sem["runs"]]
runs.sort(key=lambda r: RUN_ORDER.index(r["run"]))


def c(run):
    return COLORS.get(run, "#333333")


def nice(run):
    return NICE.get(run, run)


def f(path):
    plt.tight_layout()
    plt.savefig(FIG / path, dpi=140, bbox_inches="tight")
    plt.close()


def bar_multi(rows, fields, title, ylabel, fname, logy=False, hatches=None):
    fig, ax = plt.subplots(figsize=(9, 4.2))
    names = [nice(r["run"]) for r in rows]
    x = np.arange(len(names))
    w = 0.8 / len(fields)
    for i, (field, label) in enumerate(fields):
        vals = []
        for r in rows:
            v = r.get(field, "")
            vals.append(float(v) if v not in ("", "n/a") else 0.0)
        ax.bar(x + i * w, vals, w, label=label, hatch=hatches[i] if hatches else None)
    ax.set_xticks(x + w * (len(fields) - 1) / 2)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    if logy:
        ax.set_yscale("log")
    f(fname)


def scatter(rows, xfield, yfield, title, xl, yl, fname, color_by_harness=True):
    fig, ax = plt.subplots(figsize=(8, 5))
    for r in rows:
        x = float(r.get(xfield, 0) or 0)
        y = float(r.get(yfield, 0) or 0)
        ax.scatter(x, y, s=220, color=c(r["run"]), alpha=0.85)
        ax.annotate(nice(r["run"]), (x, y), textcoords="offset points", xytext=(8, 6), fontsize=9)
    ax.set_title(title)
    ax.set_xlabel(xl)
    ax.set_ylabel(yl)
    f(fname)


def durations():
    for r in runs:
        r["_dur_h"] = float(r["duration_s"]) / 3600
    bar_multi(runs, [("_dur_h", "hours")], "Wall-clock duration per run", "hours", "duration.png")


def tokens():
    rows = [r for r in runs]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    names = [nice(r["run"]) for r in rows]
    tin = np.array([float(r["tokens_in"]) for r in rows])
    tout = np.array([float(r["tokens_out"]) for r in rows])
    tcached = np.array([float(r["tokens_cached"]) for r in rows])
    ax.bar(names, tin, label="input", color="#2563eb")
    ax.bar(names, tout, bottom=tin, label="output", color="#dc2626")
    ax.bar(names, tcached, bottom=tin + tout, label="cached (free-ish)", color="#94a3b8", alpha=0.7)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("tokens (M)")
    ax.set_yticks([0, 20e6, 40e6, 60e6])
    ax.set_yticklabels(["0", "20M", "40M", "60M"])
    ax.set_title("Token composition per run")
    ax.legend()
    f("tokens.png")


def cost():
    rows = [r for r in runs if r.get("cost_usd")]
    fig, ax = plt.subplots(figsize=(8, 4))
    names = [nice(r["run"]) for r in rows]
    costs = [float(r["cost_usd"]) for r in rows]
    ax.bar(names, costs, color=[c(r["run"]) for r in rows])
    ax.set_ylabel("USD (OpenRouter)")
    ax.set_title("Money spent per run")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
    f("cost.png")


def efficiency_scatter():
    rows = [r for r in runs if r.get("tokens_per_line")]
    scatter(rows, "duration_s", "tokens_per_line", "Efficiency frontier (lower-left is better)",
            "duration (s)", "tokens per line changed", "efficiency.png")


def semantic_scatter():
    rows = []
    for r in runs:
        m = sem["runs"][r["run"]]["metrics"]
        rows.append({"run": r["run"], "tokens": float(r["tokens_in"]) + float(r["tokens_out"]),
                     "thinking_words": m["thinking_words"], "error_rate": m["tool_error_rate"]})
    scatter(rows, "thinking_words", "error_rate", "Rumination vs tool errors",
            "thinking words", "tool error rate", "rumination.png")


def interjections():
    labels = ["wait", "hmm", "actually", "oh", "no wait", "i see"]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    x = np.arange(len(labels))
    w = 0.8 / len(runs)
    for i, r in enumerate(runs):
        m = sem["runs"][r["run"]]["metrics"]
        vals = [m["interjections"].get(l, 0) for l in labels]
        ax.bar(x + i * w, vals, w, label=nice(r["run"]), color=c(r["run"]))
    ax.set_xticks(x + w * (len(runs) - 1) / 2)
    ax.set_xticklabels(labels)
    ax.set_title("Self-interruptions in thinking")
    ax.set_yscale("log")
    ax.set_ylabel("count (log)")
    ax.legend(fontsize=8)
    f("interjections.png")


def tool_mix():
    fig, ax = plt.subplots(figsize=(9, 4.6))
    all_tools = sorted({t for r in runs for t in sem["runs"][r["run"]]["metrics"]["tool_mix"]})
    all_tools = [t for t in all_tools if t.lower() not in ("edit", "write", "read")]
    for short in ("edit", "write", "read"):
        match = [t for t in sem["runs"][runs[0]["run"]]["metrics"]["tool_mix"] if t.lower() == short]
        if match:
            all_tools.append(match[0])
    names = [nice(r["run"]) for r in runs]
    bottoms = np.zeros(len(runs))
    cmap = plt.cm.tab10
    for j, tool in enumerate(all_tools):
        vals = []
        for r in runs:
            mix = sem["runs"][r["run"]]["metrics"]["tool_mix"]
            v = sum(cnt for t, cnt in mix.items() if t.lower() == tool.lower())
            vals.append(v)
        ax.bar(names, vals, bottom=bottoms, label=tool, color=cmap(j % 10))
        bottoms += np.array(vals)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("tool calls")
    ax.set_title("Tool usage composition")
    ax.legend(fontsize=8)
    f("tool_mix.png")


def mood():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    names = [nice(r["run"]) for r in runs]
    x = np.arange(len(names))
    w = 0.25
    for i, (key, label, color) in enumerate([("panic_mentions", "panic words", "#dc2626"),
                                             ("praise_mentions", "self-praise", "#16a34a"),
                                             ("hedge_mentions", "hedges", "#94a3b8")]):
        vals = [sem["runs"][r["run"]]["metrics"][key] for r in runs]
        ax.bar(x + i * w, vals, w, label=label, color=color)
    ax.set_xticks(x + w)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_title("Mood vocabulary in thinking")
    ax.legend()
    f("mood.png")


def test_discipline():
    fig, ax = plt.subplots(figsize=(9, 4.2))
    names = [nice(r["run"]) for r in runs]
    x = np.arange(len(names))
    w = 0.35
    runs_n = [sem["runs"][r["run"]]["metrics"]["test_runs"] for r in runs]
    err = [sem["runs"][r["run"]]["metrics"]["tool_error_rate"] * 100 for r in runs]
    ax.bar(x - w / 2, runs_n, w, label="test-suite executions", color="#2563eb")
    ax.bar(x + w / 2, err, w, label="tool error rate %", color="#dc2626")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.set_title("Test discipline vs error rate")
    ax.legend()
    f("test_discipline.png")


def personality_radar():
    dims = ["planning_quality", "error_recovery", "test_discipline", "autonomy", "polish", "efficiency"]
    angles = np.linspace(0, 2 * np.pi, len(dims), endpoint=False).tolist()
    angles += angles[:1]
    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"polar": True})
    for r in runs:
        prof = sem["runs"][r["run"]].get("profile", {})
        vals = [prof.get(d, 0) for d in dims]
        vals += vals[:1]
        ax.plot(angles, vals, color=c(r["run"]), label=nice(r["run"]), linewidth=2)
        ax.fill(angles, vals, color=c(r["run"]), alpha=0.08)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels([d.replace("_", "\n") for d in dims], fontsize=9)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_title("LLM-judged profile (1-5)")
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), fontsize=8)
    f("radar.png")


def main():
    durations()
    tokens()
    cost()
    efficiency_scatter()
    semantic_scatter()
    interjections()
    tool_mix()
    mood()
    test_discipline()
    personality_radar()
    print("figures written to", FIG)

main()
