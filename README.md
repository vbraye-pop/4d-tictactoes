# 4D Tic-Tac-Toe agent comparison

Each subdirectory is an independent git repository, starting from an identical baseline commit `1e40f677`. Run one agent per directory, then fill in `stats.csv`.

| Directory | Harness | Model | Provider / billing |
|---|---|---|---|
| `claude-code-opus5/` | Claude Code | Claude Opus 5 | Anthropic subscription, flat monthly |
| `oh-my-humanize-kimi-k3/` | oh-my-humanize | Kimi K3 | OpenRouter, per token |
| `oh-my-humanize-qwen38/` | oh-my-humanize | Qwen 3.8 | OpenRouter, per token |

## Test matrix

Legend: done = x, running = ~, planned = o

|  | claude-code | omh | opencode | aider |
|---|---|---|---|---|
| **Opus 5** | x | o | ~ | o |
| **Sonnet 5** | x | x | o | o |
| **Fable 5** |  | o | o | o |
| **Qwen 3.8-27B** |  | x | ~ | ~ |
| **Qwen 3.8 Max** |  | x | o | o |
| **Kimi K3** |  | x | o | o |
| **GLM-5.3** |  | x | o | o |
| **GLM-5.3-flash** |  | x |  |  |
| **GPT-5.5** |  | o | o | o |

Completed: opus@claude-code, sonnet@claude-code, sonnet@omh, qwen38@omh, qwen-max@omh, kimi-k3@omh, glm-5.3@omh, glm-5.3-flash@omh.
Running now: opus@opencode, qwen27b@opencode, qwen27b@aider.
Killed before completion: gpt-5.5@omh (189s, partial data in stats.csv).

Per agent: `git -C <dir> diff 1e40f677` shows the work, `git -C <dir> log --oneline` shows the history.

The agent directories are gitignored here, so this repo tracks only the harness files (this README and `stats.csv`).

## Launching a run

`./run.sh <target>` handles the whole run: sanity-checks the agent directory (baseline commit, clean tree, TASK.md present, harness on PATH), launches the harness in it with the task prompt, and records the run into `stats.csv` when the harness exits.

- `./run.sh opus` — Claude Code, model `opus`, in `claude-code-opus5/`
- `./run.sh qwen` — omh, `openrouter/qwen/qwen3.8-27b`, in `oh-my-humanize-qwen38/`
- `./run.sh kimi` — omh, `openrouter/moonshotai/kimi-k3`, in `oh-my-humanize-kimi-k3/`

Any target containing the name matches, e.g. `./run.sh qwen/qwen3.8-27B`.

Flags: `--reset` restores the agent directory to its baseline before the run. `--dry-run` runs the sanity checks and prints the launch command without starting anything.

The model is pinned per target on purpose, since a wrong default silently changes what you are benchmarking.

## Recording stats

`run.sh` fills `start_utc`, `end_utc`, `duration_s`, the token columns and `cost_usd` automatically when the harness exits (normal exit or Ctrl-C). The sources below are for cross-checking a row by hand.

### Claude Code (subscription)

- `/cost` inside the session shows input, output, cache-read and cache-write tokens plus an estimated cost. The dollar figure on a subscription is only a reference, so leave `cost_usd` empty and put the estimate in `notes` if you want it.
- Exact fallback: the session transcript is at `~/.claude/projects/<dir-slug>/<session>.jsonl`. Each assistant entry carries a `usage` object (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`). Sum those fields over the file for exact session totals.
- CSV mapping: `tokens_in` = input + cache writes, `tokens_out` = output, `tokens_cached` = cache reads. Use the same mapping for the OpenRouter runs.

### oh-my-humanize (OpenRouter)

- The activity page at openrouter.ai/activity is the source of truth. Filter by model name (the two runs are different models, so they separate cleanly) and by the run's time window, then sum the cost column into `cost_usd` and the token columns into `tokens_in`, `tokens_out`, `tokens_cached`.
- Programmatic alternative: `GET https://openrouter.ai/api/v1/generations` with your key returns per-request tokens, cost and `created_at`. Filter by model and window, sum with jq.
- If omh prints its own session usage summary at the end, take tokens from there and take the money from OpenRouter, since OpenRouter is what bills.

For cross-run comparison use `tokens_in`, `tokens_out` and wall-clock time. Claude Code reports cache reads and writes separately, OpenRouter folds caching into per-token prices, and `cost_usd` only exists for the two OpenRouter rows unless you deliberately fill the subscription row with an API-priced reference.
