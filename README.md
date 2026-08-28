# 4D Tic-Tac-Toe agent comparison

Each subdirectory is an independent git repository, starting from an identical baseline commit. Run one agent per directory, fill in `stats.csv`, and the analysis pipeline produces a report.

## Test matrix

Legend: done = x, planned = o

|  | claude-code | omh | opencode | aider |
|---|---|---|---|---|
| **Opus 5** | x | o | o | o |
| **Sonnet 5** | x | x | o | o |
| **Fable 5** |  | o | x | o |
| **Qwen 3.8-27B** |  | x | x | x |
| **Qwen 3.8 Max** |  | x | o | o |
| **Kimi K3** |  | x | o | o |
| **GLM-5.3** |  | x | o | o |
| **GLM-5.3-flash** |  | x |  |  |
| **GPT-5.5** |  | o | o | o |

Completed: opus@claude-code, sonnet@claude-code, sonnet@omh, qwen38@omh, qwen-max@omh, kimi-k3@omh, glm-5.3@omh, glm-5.3-flash@omh, opencode-qwen, opencode-fable, aider-qwen.
Killed before completion: gpt-5.5@omh (189s, partial data in stats.csv).

## Launching a run

`./run.sh <target>` does the whole thing: sanity-checks the agent directory, launches the harness with the task prompt, and records the run into `stats.csv` when the harness exits.

- `./run.sh opus` — Claude Code, model `opus`, in `claude-code-opus5/`
- `./run.sh qwen` — omh, `openrouter/qwen/qwen3.8-27b`, in `oh-my-humanize-qwen38/`
- `./run.sh kimi` — omh, `openrouter/moonshotai/kimi-k3`, in `oh-my-humanize-kimi-k3/`
- `./run.sh opencode-qwen` — opencode, `openrouter/qwen/qwen3.8-27b`, in `opencode-qwen/`
- `./run.sh aider-qwen` — aider, `openrouter/qwen/qwen3.8-27b`, in `aider-qwen/`

Any target containing the name matches, e.g. `./run.sh qwen3.8-max`.

Flags: `--reset` restores the agent directory to its baseline before the run. `--dry-run` runs the sanity checks and prints the launch command without starting anything. `--new` scaffolds a fresh agent directory.

The model is pinned per target on purpose, since a wrong default silently changes what you are benchmarking.

## Recording stats

`run.sh` fills `start_utc`, `end_utc`, `duration_s`, the token columns and `cost_usd` automatically when the harness exits (normal exit or Ctrl-C). The sources below are for cross-checking a row by hand.

### Claude Code (subscription)

- `/cost` inside the session shows input, output, cache-read and cache-write tokens plus an estimated cost. The dollar figure on a subscription is only a reference, so leave `cost_usd` empty and put the estimate in `notes` if you want it.
- Exact fallback: the session transcript is at `~/.claude/projects/<dir-slug>/<session>.jsonl`. Each assistant entry carries a `usage` object (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`). Sum those fields over the file for exact session totals.
- CSV mapping: `tokens_in` = input + cache writes, `tokens_out` = output, `tokens_cached` = cache reads. Use the same mapping for the OpenRouter runs.

### oh-my-humanize (OpenRouter)

- The activity page at openrouter.ai/activity is the source of truth. Filter by model name and by the run's time window, then sum the cost column into `cost_usd` and the token columns into `tokens_in`, `tokens_out`, `tokens_cached`.
- Programmatic alternative: `GET https://openrouter.ai/api/v1/generations` with your key returns per-request tokens, cost and `created_at`. Filter by model and window, sum with jq.
- If omh prints its own session usage summary at the end, take tokens from there and take the money from OpenRouter, since OpenRouter is what bills.

### opencode (OpenRouter)

- opencode stores per-message token usage in `~/.local/share/opencode/opencode.db` (SQLite). The collector reads it directly.

### aider (OpenRouter)

- aider writes `.aider.chat.history.md` in the project dir. Duration only; no per-message token store.

For cross-run comparison use `tokens_in`, `tokens_out` and wall-clock time. Claude Code reports cache reads and writes separately, OpenRouter folds caching into per-token prices, and `cost_usd` only exists for the OpenRouter rows unless you deliberately fill the subscription row with an API-priced reference.

## Analysis

- `analyze.py` — reads `stats.csv` and transcripts, produces `analysis/summary.md`, `analysis/metrics.csv`, and PNG plots.
- `semantic.py` — reads transcripts, computes behavioral metrics, and asks a small model for per-run profiles and a cross-run synthesis.
- `report.py` — generates the typst report (`report/report.pdf`) with figures and per-run deep dives.

Run order: `analyze.py`, then `semantic.py`, then `report.py`.
