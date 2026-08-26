# Benchmark analysis

| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code-opus5 | 0h55m22s | 102 | 221,730 | 147,838 | 15,062,878 | 98.5% | 4645.5 | n/a | - | - | 31 | 0.0% | 0 |
| oh-my-humanize-qwen38 | 3h16m27s | 385 | 14,418,837 | 555,469 | 54,275,904 | 79.0% | 5875.1 | $11.9735 | 7,487,153 | 6,002 | 402 | 6.5% | 200 |

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
- **oh-my-humanize-qwen38**: 3h16m27s, 385 calls, 69,250,210 tokens (79.0% cached), 2 commits, 2495 lines, 34,625,105 tok/commit, 27,756 tok/line, $11.9735
