#!/usr/bin/env python3
"""Semantic analysis of benchmark transcripts.

Reads the same session windows as analyze.py, parses both harness transcript
formats into a unified turn model, computes deterministic behavioral metrics
and fun stats, samples excerpts, and asks a small model (OpenRouter) for a
per-run profile JSON plus a cross-run synthesis. Writes analysis/semantic.json.

Usage: analysis/.venv/bin/python semantic.py
"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "analysis"
READER_MODEL = "qwen/qwen3.8-27b"

UTC = timezone.utc

def ts(s):
    if isinstance(s, (int, float)):
        return float(s) / 1000 if s > 1e12 else float(s)
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC).timestamp()


# ---------------------------------------------------------------- transcripts

def openrouter_key():
    r = subprocess.run(["omh", "token", "openrouter"], capture_output=True, text=True)
    key = r.stdout.strip()
    if not key.startswith("sk-"):
        raise RuntimeError("could not get openrouter key from `omh token openrouter`")
    return key


def parse_turns(dir_name, harness, start_epoch):
    """Unify both transcript formats into a flat list of event dicts."""
    cutoff = start_epoch - 15
    if harness == "claude-code":
        bases = glob.glob(str(Path.home() / ".claude" / "projects" / f"*{dir_name}*"))
    else:
        bases = [str(Path.home() / ".omp" / "agent" / "sessions")]
    files = []
    for base in bases:
        for f in glob.glob(os.path.join(base, "**", "*.jsonl"), recursive=True):
            st = os.stat(f)
            if getattr(st, "st_birthtime", st.st_mtime) >= cutoff:
                files.append(f)
    events = []
    for f in files:
        for line in open(f, errors="ignore"):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msg = rec.get("message")
            stamp = rec.get("timestamp", "")
            try:
                if isinstance(stamp, (int, float)):
                    t = ts(stamp)
                elif isinstance(stamp, str) and len(stamp) >= 19 and "T" in stamp and "-" in stamp:
                    t = ts(stamp[:19] + "Z")
                else:
                    t = float(start_epoch)
            except Exception:
                t = float(start_epoch)
            if harness == "claude-code":
                events += claude_events(rec, t)
            else:
                events += omh_events(rec, t)
    bad = [e for e in events if not isinstance(e.get("ts"), (int, float))]
    if bad:
        print(f"DEBUG bad events: {[(e['kind'], repr(e.get('ts'))[:80]) for e in bad[:5]]}")
        for e in bad:
            e["ts"] = float(start_epoch)
    events.sort(key=lambda e: float(e["ts"]))
    return events


def claude_events(rec, t):
    """Claude Code transcript entry -> events."""
    out = []
    m = rec.get("message")
    if not isinstance(m, dict):
        return out
    role = m.get("role")
    if role == "assistant":
        thinking = ""
        text = ""
        calls = []
        for blk in m.get("content", []):
            if not isinstance(blk, dict):
                continue
            if blk.get("type") == "thinking":
                t = blk.get("thinking", "")
                if t:
                    thinking += t
                else:
                    # redacted thinking block (Claude streams signatures, not text)
                    m["thinking_redacted"] = True
            elif blk.get("type") == "text":
                text += blk.get("text", "")
            elif blk.get("type") == "tool_use":
                calls.append({"name": blk.get("name", ""),
                              "arg": str(blk.get("input", ""))[:200]})
        redacted = any(isinstance(blk, dict) and blk.get("type") == "thinking" and not blk.get("thinking") for blk in m.get("content", []))
        u = m.get("usage") or {}
        stop = m.get("stop_reason")
        ev = {"kind": "assistant", "ts": t, "thinking": thinking, "text": text,
              "tool_calls": calls, "usage": u, "stop": stop}
        if redacted:
            ev["thinking_redacted"] = True
        out.append(ev)
    elif role == "user":
        for blk in m.get("content", []):
            if isinstance(blk, dict) and blk.get("type") == "tool_result":
                out.append({"kind": "tool_result", "ts": t,
                            "tool_name": "", "error": bool(blk.get("is_error")),
                            "wall_ms": None, "text": str(blk.get("content", ""))[:400]})
        if isinstance(m.get("content"), str) or (isinstance(m.get("content"), list) and not any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in m["content"])):
            txt = m.get("content", "")
            if isinstance(txt, list):
                txt = " ".join(str(b.get("text", "")) for b in txt if isinstance(b, dict))
            out.append({"kind": "user", "ts": t, "text": txt[:500]})
    return out


def omh_events(rec, t):
    """omh transcript entry -> events."""
    out = []
    if rec.get("type") == "custom_message" and rec.get("customType") == "interrupted-thinking":
        out.append({"kind": "abort", "ts": t})
        return out
    m = rec.get("message")
    if not isinstance(m, dict):
        return out
    role = m.get("role")
    if role == "assistant":
        thinking = ""
        text = ""
        calls = []
        for blk in m.get("content", []):
            if not isinstance(blk, dict):
                continue
            if blk.get("type") == "thinking":
                t = blk.get("thinking", "")
                if t:
                    thinking += t
                else:
                    # redacted thinking block (Claude streams signatures, not text)
                    m["thinking_redacted"] = True
            elif blk.get("type") == "text":
                text += blk.get("text", "")
            elif blk.get("type") == "toolCall":
                calls.append({"name": blk.get("name", ""),
                              "arg": str(blk.get("arguments", blk.get("args", "")))[:200]})
        out.append({"kind": "assistant", "ts": t, "thinking": thinking, "text": text,
                    "tool_calls": calls, "usage": m.get("usage") or {},
                    "stop": m.get("stopReason"), "error_msg": m.get("errorMessage")})
    elif role == "user":
        content = m.get("content", "")
        if isinstance(content, list):
            content = " ".join(str(b.get("text", "")) for b in content if isinstance(b, dict))
        out.append({"kind": "user", "ts": t, "text": content[:500]})
    elif role == "toolResult":
        out.append({"kind": "tool_result", "ts": t, "tool_name": m.get("toolName", ""),
                    "error": bool(m.get("isError")),
                    "wall_ms": (m.get("details") or {}).get("wallTimeMs"),
                    "text": " ".join(str(b.get("text", "")) for b in m.get("content", []) if isinstance(b, dict))[:400]})
    return out


# ------------------------------------------------------------- deterministic

INTERJECTIONS = {
    "wait": r"\bwait\b", "hmm": r"\bhmm+\b", "oh": r"\boh\b", "actually": r"\bactually\b",
    "ah": r"\bah\b", "got it": r"\bgot it\b", "no wait": r"\bno,? wait\b",
    "oops": r"\boops\b", "damn": r"\bdamn\b", "ugh": r"\bugh\b",
    "nice": r"\bnice\b", "interesting": r"\binteresting\b", "clearly": r"\bclearly\b",
    "obviously": r"\bobviously\b", "the bug": r"\bthe bug\b", "i see": r"\bi see\b",
}
PANIC = r"\b(oh no|broken|wrong|bug|fail|fails|failed|error|crash|ugh|damn)\b"
PRAISE = r"\b(nice|great|clean|works|perfect|beautiful|elegant)\b"
HEDGE = r"\b(maybe|probably|might|perhaps|i think|i guess|not sure)\b"

EDIT_TOOLS = {"edit", "write", "Edit", "Write"}
READ_TOOLS = {"read", "grep", "glob", "Read", "Grep", "Glob"}


def metrics(events):
    m = {"thinking_redacted": False}
    m["user_turns"] = sum(1 for e in events if e["kind"] == "user")
    m["assistant_turns"] = sum(1 for e in events if e["kind"] == "assistant")
    m["tool_results"] = sum(1 for e in events if e["kind"] == "tool_result")
    m["aborts"] = sum(1 for e in events if e["kind"] == "abort"
                      or (e["kind"] == "assistant" and e.get("stop") == "aborted"))

    thinking_all = ""
    text_all = ""
    think_lens = []
    tool_calls = []
    for e in events:
        if e["kind"] == "assistant":
            thinking_all += e["thinking"]
            text_all += e["text"]
            if e["thinking"]:
                think_lens.append(len(e["thinking"]))
            tool_calls += e["tool_calls"]
    m["thinking_redacted"] = any(e.get("thinking_redacted") for e in events)
    m["thinking_chars"] = len(thinking_all)
    m["text_chars"] = len(text_all)
    m["thinking_share"] = (m["thinking_chars"] / (m["thinking_chars"] + m["text_chars"])) if thinking_all or text_all else 0
    m["longest_thinking_chars"] = max(think_lens) if think_lens else 0
    m["median_thinking_chars"] = sorted(think_lens)[len(think_lens) // 2] if think_lens else 0
    m["n_thinking_blocks"] = len(think_lens)

    from collections import Counter
    mix = Counter(c["name"] for c in tool_calls)
    m["tool_mix"] = dict(mix)
    m["tool_calls"] = len(tool_calls)

    results = [e for e in events if e["kind"] == "tool_result"]
    m["tool_errors"] = sum(1 for e in results if e["error"])
    m["tool_error_rate"] = m["tool_errors"] / len(results) if results else 0

    # edit streaks on same file with no bash/test between (dead-end proxy)
    streaks = []
    cur_file = None
    cur = 0
    for c in tool_calls:
        name, arg = c["name"], c["arg"]
        if name in EDIT_TOOLS:
            fm = re.search(r"'path':\s*'([^']+)'|\"path\":\s*\"([^\"]+)\"|file_path.*?'([^']+)'", arg)
            f = (fm.group(1) or fm.group(2) or fm.group(3)) if fm else ""
            if f == cur_file:
                cur += 1
            else:
                if cur:
                    streaks.append((cur_file, cur))
                cur_file, cur = f, 1
        else:
            if cur:
                streaks.append((cur_file, cur))
            cur_file, cur = None, 0
    if cur:
        streaks.append((cur_file, cur))
    m["max_edit_streak"] = max((s for _, s in streaks), default=0)
    m["long_edit_streaks"] = sum(1 for _, s in streaks if s >= 4)

    # test discipline
    bash_cmds = [c["arg"] for c in tool_calls if c["name"].lower() == "bash"]
    m["test_runs"] = sum(1 for c in bash_cmds if re.search(r"pytest|unittest", c))
    m["server_starts"] = sum(1 for c in bash_cmds if re.search(r"run\.py|serve|uvicorn|flask run|http\.server", c))
    m["browser_calls"] = sum(1 for c in tool_calls if c["name"].lower() == "browser")
    m["todo_calls"] = sum(1 for c in tool_calls if c["name"].lower() == "todo")
    m["subagent_calls"] = sum(1 for c in tool_calls if c["name"].lower() in ("task", "agent"))

    first_test_write = first_src_write = None
    for c in tool_calls:
        if c["name"] not in EDIT_TOOLS:
            continue
        fm = re.search(r"'path':\s*'([^']+)'|\"path\":\s*\"([^\"]+)\"|file_path.*?'([^']+)'", c["arg"])
        f = (fm.group(1) or fm.group(2) or fm.group(3)) if fm else ""
        if not f:
            continue
        idx = next((i for i, e in enumerate(events) if e["kind"] == "assistant" and c in e["tool_calls"]), 0)
        tt = events[idx]["ts"] if idx else 0
        is_test = "test" in f.lower()
        if is_test and first_test_write is None:
            first_test_write = tt
        if not is_test and not f.endswith((".md", ".txt", ".gitignore")) and first_src_write is None:
            first_src_write = tt
    m["tests_before_src"] = bool(first_test_write and first_src_write and first_test_write < first_src_write)

    # final test outcome from the last bash result mentioning tests
    m["final_tests"] = "unknown"
    for e in reversed(results):
        txt = e.get("text", "")
        if re.search(r"passed|OK\b", txt) and re.search(r"pytest|unittest|test", txt, re.I):
            m["final_tests"] = "passing"
            break
        if re.search(r"\bFAILED\b|\bfailed\b|Error", txt) and re.search(r"test", txt, re.I):
            m["final_tests"] = "failing"
            break

    # language stats on thinking
    words = re.findall(r"[a-zA-Z']+", thinking_all.lower())
    m["thinking_words"] = len(words)
    m["thinking_vocab"] = len(set(words))
    sents = re.split(r"[.!?]\s", thinking_all)
    m["thinking_sentences"] = len([s for s in sents if s.strip()])
    m["avg_sentence_words"] = (len(words) / m["thinking_sentences"]) if m["thinking_sentences"] else 0
    m["self_questions"] = thinking_all.count("?")
    m["ellipses"] = thinking_all.count("...")

    inter = {}
    for label, pat in INTERJECTIONS.items():
        inter[label] = len(re.findall(pat, thinking_all.lower()))
    m["interjections"] = inter
    m["panic_mentions"] = len(re.findall(PANIC, thinking_all.lower()))
    m["praise_mentions"] = len(re.findall(PRAISE, thinking_all.lower()))
    m["hedge_mentions"] = len(re.findall(HEDGE, thinking_all.lower()))

    # activity buckets (10 min)
    if events:
        t0 = events[0]["ts"]
        buckets = {}
        for e in events:
            b = int((e["ts"] - t0) // 600)
            buckets[b] = buckets.get(b, 0) + (len(e.get("thinking", "")) + len(e.get("text", "")) + 200 * len(e.get("tool_calls", [])))
        m["activity_buckets"] = buckets
    return m, thinking_all, text_all


# --------------------------------------------------------------- llm digest

def pick_excerpts(events, thinking_all):
    assists = [e for e in events if e["kind"] == "assistant"]
    blocks = [e for e in assists if e["thinking"]] or [e for e in assists if e["text"]]
    picks = []
    seen_ids = set()

    def add(e, why):
        if id(e) in seen_ids:
            return
        seen_ids.add(id(e))
        picks.append({"why": why, "thinking": e["thinking"][:2000], "text": e["text"][:800],
                      "tools": [c["name"] for c in e["tool_calls"]]})

    for e in blocks[:2]:
        add(e, "opening-plan")
    for e in blocks[-2:]:
        add(e, "final-wrap")
    for e in sorted(blocks, key=lambda e: -len(e["thinking"]))[:3]:
        add(e, "longest-thinking")
    errs = [i for i, e in enumerate(events) if e["kind"] == "tool_result" and e["error"]]
    for i in errs[:3]:
        for j in range(i + 1, min(i + 4, len(events))):
            if events[j]["kind"] == "assistant" and events[j]["thinking"]:
                add(events[j], "error-recovery")
                break
    mid = blocks[len(blocks) // 2] if blocks else None
    if mid:
        add(mid, "midpoint")
    return picks[:12]


def call_llm(key, messages, max_tokens=3000):
    body = {"model": READER_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": 0.1,
            "reasoning": {"effort": "low"}}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                out = json.loads(r.read().decode())
            msg = out["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning") or ""
            return content
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))


def extract_json(text):
    i = text.find("{")
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[i:j + 1])
    raise ValueError("no json object in llm output")


PROFILE_PROMPT = """You are analyzing the work transcript of an AI coding agent. The agent was asked to build a complete browser-based 4D tic-tac-toe game in Python from scratch, end to end.

Run: {run} (harness: {harness}, model: {model})

Deterministic stats from the transcript:
{stats}

Sampled transcript excerpts (the agent's own thinking and text):
{excerpts}

Return exactly one JSON object with these keys:
- planning_quality: int 1-5 (did it plan before acting, was the plan sound)
- error_recovery: int 1-5 (how it responded to failures)
- test_discipline: int 1-5 (did tests exist, run, get fixed)
- autonomy: int 1-5 (proceeded vs needed steering)
- polish: int 1-5 (attention to finishing quality, UI polish, docs)
- efficiency: int 1-5 (little wasted motion)
- personality: string, a fun 2-4 word archetype
- strengths: array of 3-6 short strings, concrete and evidence-based
- weaknesses: array of 3-6 short strings, concrete and honest
- quirks: array of 2-5 short strings, funny or distinctive behaviors
- quotes: array of 3-6 short verbatim quotes from the excerpts that best capture its style
- summary: string, one paragraph describing how this run went
Only the JSON object, nothing else."""


def profile_run(key, run, m, excerpts):
    stats = {k: v for k, v in m.items() if k not in ("activity_buckets",)}
    user = PROFILE_PROMPT.format(
        run=run["run"], harness=run["harness"], model=run["model"],
        stats=json.dumps(stats, indent=1)[:6000],
        excerpts=json.dumps(excerpts, indent=1)[:60000])
    out = call_llm(key, [{"role": "user", "content": user}])
    return extract_json(out)


SYNTH_PROMPT = """You wrote individual profiles of coding-agent benchmark runs. Now write the cross-run comparison.

All runs built the same task: a browser-based 4D tic-tac-toe game in Python, from the same TASK.md, measured by tokens, time, tools, and tests.

Profiles (JSON):
{profiles}

Metric table (CSV rows):
{table}

Write markdown with exactly these sections:
## The matchup
One paragraph: what the three runs reveal at a glance.

## Per-combination pros and cons
For each run: bold name, then a short paragraph of genuine, evidence-based pros and cons (not a bullet dump of stats).

## Patterns across harnesses
What differs by harness vs what differs by model.

## Surprises
2-4 bullets of unexpected findings.

## Verdict
Who is best at what. Be opinionated but fair, cite numbers.
Write only the markdown."""


def synthesize(key, profiles, table_md):
    out = call_llm(key, [{"role": "user", "content": SYNTH_PROMPT.format(
        profiles=json.dumps(profiles, indent=1)[:40000], table=table_md)}], max_tokens=4000)
    return out


# -------------------------------------------------------------------- main

def personality(m):
    tags = []
    if m["thinking_share"] > 0.6:
        tags.append("The Ruminator")
    if m["tool_error_rate"] > 0.08:
        tags.append("The Debugger")
    if m["todo_calls"] == 0:
        tags.append("The Freestyler")
    if m["browser_calls"] == 0:
        tags.append("The Blindfolded")
    if m["max_edit_streak"] >= 6:
        tags.append("The Ouroboros")
    if m["test_runs"] >= 10:
        tags.append("The Assurance Officer")
    if m["subagent_calls"] > 0:
        tags.append("The Delegator")
    return tags or ["The Pragmatist"]


def main():
    rows = list(csv.DictReader(open(ROOT / "stats.csv")))
    filled = [r for r in rows if r.get("start_utc")]
    if not filled:
        sys.exit("no filled rows in stats.csv")

    cached = OUT / "semantic.json"
    have = json.loads(cached.read_text()) if cached.exists() else {}
    result = {"runs": {}, "synthesis": have.get("synthesis")}

    need_llm = "--no-llm" not in sys.argv
    synth_only = "--synthesis-only" in sys.argv
    key = openrouter_key() if need_llm else None

    for row in filled:
        name = row["run"]
        events = parse_turns(name, row["harness"], ts(row["start_utc"]))
        m, thinking_all, text_all = metrics(events)
        m["personality_tags"] = personality(m)
        m["top_interjections"] = sorted(m["interjections"].items(), key=lambda kv: -kv[1])[:8]

        excerpts = pick_excerpts(events, thinking_all)
        entry = {"metrics": m, "excerpt_count": len(excerpts)}
        if need_llm and not synth_only:
            print(f"profiling {name} with {READER_MODEL}...", flush=True)
            try:
                entry["profile"] = profile_run(key, row, m, excerpts)
            except Exception as e:
                entry["profile_error"] = str(e)
        elif synth_only and name in have.get("runs", {}):
            entry["profile"] = have["runs"][name].get("profile")
        result["runs"][name] = entry
        print(f"  {name}: {len(events)} events, {m['tool_calls']} tool calls, "
              f"{m['thinking_words']} thinking words, errors={m['tool_errors']}")

    if need_llm:
        profiles = {n: e.get("profile", {}) for n, e in result["runs"].items() if e.get("profile")}
        if profiles:
            table = (OUT / "metrics.csv").read_text() if (OUT / "metrics.csv").exists() else ""
            print("synthesizing cross-run analysis...", flush=True)
            result["synthesis"] = synthesize(key, profiles, table)

    cached.write_text(json.dumps(result, indent=1))
    print("wrote", cached)


if __name__ == "__main__":
    main()
