# 4D Tic-Tac-Toe agent comparison

Each subdirectory is an independent git repository, starting from an identical baseline commit `1e40f677`. Run one agent per directory, then fill in `stats.csv`.

| Directory | Harness | Model | Provider / billing |
|---|---|---|---|
| `claude-code-opus5/` | Claude Code | Claude Opus 5 | Anthropic subscription, flat monthly |
| `oh-my-humanize-kimi-k3/` | oh-my-humanize | Kimi K3 | OpenRouter, per token |
| `oh-my-humanize-qwen38/` | oh-my-humanize | Qwen 3.8 | OpenRouter, per token |

Per agent: `git -C <dir> diff 1e40f677` shows the work, `git -C <dir> log --oneline` shows the history.

The agent directories are gitignored here, so this repo tracks only the harness files (this README and `stats.csv`).

For the subscription run there is no per-token cost. Record its tokens for reference and leave `cost_usd` empty (or fill an allocated share if you want a comparable figure).
