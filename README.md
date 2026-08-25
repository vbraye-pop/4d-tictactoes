# 4D Tic-Tac-Toe agent comparison

Each subdirectory is an independent git repository, starting from an identical baseline commit `1e40f677`. Run one agent per directory, then fill in `stats.csv`.

| Directory | Harness | Model | Provider / billing |
|---|---|---|---|
| `claude-code-opus5/` | Claude Code | Claude Opus 5 | Anthropic subscription, flat monthly |
| `oh-my-humanize-kimi-k3/` | oh-my-humanize | Kimi K3 | OpenRouter, per token |
| `oh-my-humanize-qwen38/` | oh-my-humanize | Qwen 3.8 | OpenRouter, per token |

Per agent: `git -C <dir> diff 1e40f677` shows the work, `git -C <dir> log --oneline` shows the history.

The agent directories are gitignored here, so this repo tracks only the harness files (this README and `stats.csv`).

## Launching a run

Run the matching command from inside the agent's directory. It starts an interactive session with the task prompt already sent, so the agent begins planning and executing immediately.

- `claude-code-opus5/`: `claude --model opus "Read TASK.md and start planning and executing the task."`
- `oh-my-humanize-qwen38/`: `omh --model openrouter/qwen/qwen3.8-27b "Read TASK.md and start planning and executing the task."`
- `oh-my-humanize-kimi-k3/`: `omh --model <slug> "Read TASK.md and start planning and executing the task."`

Pin the model under test in both harnesses, since a wrong default silently changes what you are benchmarking. `omh models` lists the slugs for the kimi run. Drop the flag if your default is already the model under test.

## Recording stats

For each run, record wall-clock time with `date -u` right before launch and right after the agent stops. Those go in `start_utc` and `end_utc`, duration is the difference.

### Claude Code (subscription)

- `/cost` inside the session shows input, output, cache-read and cache-write tokens plus an estimated cost. The dollar figure on a subscription is only a reference, so leave `cost_usd` empty and put the estimate in `notes` if you want it.
- Exact fallback: the session transcript is at `~/.claude/projects/<dir-slug>/<session>.jsonl`. Each assistant entry carries a `usage` object (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`). Sum those fields over the file for exact session totals.
- CSV mapping: `tokens_in` = input + cache writes, `tokens_out` = output, `tokens_cached` = cache reads. Use the same mapping for the OpenRouter runs.

### oh-my-humanize (OpenRouter)

- The activity page at openrouter.ai/activity is the source of truth. Filter by model name (the two runs are different models, so they separate cleanly) and by the run's time window, then sum the cost column into `cost_usd` and the token columns into `tokens_in`, `tokens_out`, `tokens_cached`.
- Programmatic alternative: `GET https://openrouter.ai/api/v1/generations` with your key returns per-request tokens, cost and `created_at`. Filter by model and window, sum with jq.
- If omh prints its own session usage summary at the end, take tokens from there and take the money from OpenRouter, since OpenRouter is what bills.

For cross-run comparison use `tokens_in`, `tokens_out` and wall-clock time. Claude Code reports cache reads and writes separately, OpenRouter folds caching into per-token prices, and `cost_usd` only exists for the two OpenRouter rows unless you deliberately fill the subscription row with an API-priced reference.
