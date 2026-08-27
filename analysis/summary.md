# Benchmark analysis

| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code-opus5 | 0h55m22s | 102 | 221,730 | 147,838 | 15,062,878 | 98.5% | 4645.5 | n/a | - | - | 31 | 0.0% | 0 |
| oh-my-humanize-kimi-k3 | 0h30m41s | 645 | 4,498,603 | 693,431 | 95,129,488 | 95.5% | 54493.0 | $20.8890 | - | - | 709 | 7.8% | 510 |
| oh-my-humanize-qwen38 | 3h05m40s | 843 | 17,558,132 | 950,156 | 111,485,952 | 86.4% | 11669.1 | $28.5198 | - | - | 910 | 8.0% | 438 |
| oh-my-humanize-qwen-max | 3h44m25s | 169 | 2,682,280 | 238,505 | 30,141,440 | 91.8% | 2455.4 | $14.3309 | - | - | 197 | 7.6% | 604 |
| oh-my-humanize-ox-alpha | 1h38m15s | 645 | 4,498,603 | 693,431 | 95,129,488 | 95.5% | 17018.1 | n/a | - | - | 709 | 7.8% | 510 |

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
- **oh-my-humanize-kimi-k3**: 0h30m41s, 645 calls, 100,321,522 tokens (95.5% cached), 0 commits, 0 lines, 100,321,522 tok/commit, 100,321,522 tok/line, $20.8890
- **oh-my-humanize-qwen38**: 3h05m40s, 843 calls, 129,994,240 tokens (86.4% cached), 0 commits, 0 lines, 129,994,240 tok/commit, 129,994,240 tok/line, $28.5198
- **oh-my-humanize-qwen-max**: 3h44m25s, 169 calls, 33,062,225 tokens (91.8% cached), 0 commits, 0 lines, 33,062,225 tok/commit, 33,062,225 tok/line, $14.3309
- **oh-my-humanize-ox-alpha**: 1h38m15s, 645 calls, 100,321,522 tokens (95.5% cached), 0 commits, 0 lines, 100,321,522 tok/commit, 100,321,522 tok/line
