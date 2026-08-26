# Benchmark analysis

| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code-opus5 | 0h55m22s | 102 | 221,730 | 147,838 | 15,062,878 | 98.5% | 4645.5 | n/a | - | - | 31 | 0.0% | 0 |
| oh-my-humanize-kimi-k3 | 0h30m35s | 85 | 89,226 | 34,379 | 3,730,176 | 97.7% | 2100.2 | $1.8073 | - | - | 84 | 10.7% | 147 |
| oh-my-humanize-qwen38 | 3h05m40s | 470 | 14,508,063 | 589,848 | 58,006,080 | 80.0% | 6562.3 | $13.7808 | - | - | 486 | 7.2% | 191 |

## Plots
### tokens over time
![](tokens_over_time.png)
### tokens vs cost
![](tokens_vs_cost.png)
### cost over time
![](cost_over_time.png)
### tool usage
![](tool_usage.png)
### tokens per commit
![](tokens_per_commit.png)

## Per-run insights
- **claude-code-opus5**: 0h55m22s, 102 calls, 15,432,446 tokens (98.5% cached), 0 commits, 0 lines, 15,432,446 tok/commit, 15,432,446 tok/line
- **oh-my-humanize-kimi-k3**: 0h30m35s, 85 calls, 3,853,781 tokens (97.7% cached), 0 commits, 0 lines, 3,853,781 tok/commit, 3,853,781 tok/line, $1.8073
- **oh-my-humanize-qwen38**: 3h05m40s, 470 calls, 73,103,991 tokens (80.0% cached), 0 commits, 0 lines, 73,103,991 tok/commit, 73,103,991 tok/line, $13.7808
