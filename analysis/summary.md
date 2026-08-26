# Benchmark analysis

| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code-opus5 | 0h55m22s | 102 | 221,730 | 147,838 | 15,062,878 | 98.5% | 4645.5 | n/a | 52,795 | 128 | 31 | 0.0% | 0 |

## Plots
### tokens over time
![](tokens_over_time.png)
### tokens vs cost
![](tokens_vs_cost.png)
### tool usage
![](tool_usage.png)

## Per-run insights
- **claude-code-opus5**: 0h55m22s, 102 calls, 15,432,446 tokens (98.5% cached), 7 commits, 2890 lines, 2,204,635 tok/commit, 5,340 tok/line
