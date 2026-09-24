# Benchmark analysis

| run | duration | api calls | in | out | cached | cache ratio | tokens/s | cost | tokens/commit | tokens/line | tool calls | tool err% | tool avg ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-code-opus5 | 0h55m22s | 102 | 221,730.0 | 147,838.0 | 15,062,878.0 | 98.5% | 4645.5 | n/a | - | 128 | 31 | 0.0% | 0 |
| oh-my-humanize-kimi-k3 | 0h30m41s | 85 | 89,226.0 | 34,379.0 | 3,730,176.0 | 97.7% | 2093.3 | $1.8073 | - | 109 | 84 | 10.7% | 147 |
| oh-my-humanize-qwen38 | 3h05m40s | 385 | 1,359,308.0 | 298,744.0 | 37,919,440.0 | 96.5% | 3552.7 | $4.3427 | - | 664 | 402 | 6.5% | 200 |
| oh-my-humanize-qwen-max | 3h44m25s | 169 | 2,682,280.0 | 238,505.0 | 30,141,440.0 | 91.8% | 2455.4 | $14.3309 | 973,595 | 1,424 | 197 | 7.6% | 604 |
| oh-my-humanize-ox-alpha | 1h38m15s | 204 | 367,789.0 | 121,803.0 | 23,338,432.0 | 98.4% | 4042.1 | $0.4081 | 44,508 | 231 | 227 | 10.1% | 820 |
| oh-my-humanize-glm-53 | 1h55m01s | 156 | 226,885.0 | 160,646.0 | 23,455,360.0 | 99.0% | 3455.0 | $7.1229 | 193,766 | 147 | 177 | 4.0% | 133 |
| claude-code-sonnet | 1h30m36s | 138 | 262,680.0 | 136,794.0 | 23,081,346.0 | 98.9% | 4319.5 | n/a | 66,579 | 176 | 33 | 0.0% | 0 |
| oh-my-humanize-codex | 0h03m09s | 16 | 53,015.0 | 15,055.0 | 422,400.0 | 88.8% | 2595.1 | $0.9279 | - | 820 | 23 | 0.0% | 14 |
| opencode-qwen | 2h00m34s | 0 | 145,441.0 | 139,390.0 | 6,856,800.0 | 97.9% | 987.2 | $1.0001 | 284,831 | 147 | 0 | 0.0% | 0 |
| opencode-kimi | 3h19m02s | 0 | 330,515.0 | 111,177.0 | 6,649,792.0 | 95.3% | 593.8 | $5.5294 | 88,338 | 365 | 0 | 0.0% | 0 |
| aider-qwen | 1h44m24s | 0 | 34,700.0 | 149,000.0 | 0.0 | 0.0% | 29.3 | $0.4000 | 91,850 | 108 | 0 | 0.0% | 0 |
| aider-kimi | 0h29m10s | 0 | 102,400.0 | 91,012.0 | 0.0 | 0.0% | 110.5 | $1.6700 | 96,706 | 172 | 0 | 0.0% | 0 |
| opencode-opus | 3h55m47s | 0 | 1,600,743.0 | 422,575.0 | 24,450,982.0 | 93.9% | 1871.4 | $36.6583 | 674,439 | 447 | 0 | 0.0% | 0 |
| opencode-sonnet | 0h32m05s | 0 | 460,016.0 | 105,152.0 | 6,648,448.0 | 93.5% | 3747.3 | $3.6547 | 565,168 | 290 | 0 | 0.0% | 0 |
| opencode-qwen-max | 1h51m21s | 0 | 404,478.0 | 186,820.0 | 7,949,696.0 | 95.2% | 1278.4 | $4.7083 | 591,298 | 231 | 0 | 0.0% | 0 |
| opencode-glm-53 | 2h28m44s | 0 | 1,306,784.0 | 271,767.0 | 14,945,187.0 | 92.0% | 1851.6 | $4.6555 | 315,710 | 550 | 0 | 0.0% | 0 |
| opencode-codex | 2h54m15s | 0 | 426,045.0 | 91,540.0 | 4,679,168.0 | 91.7% | 497.1 | $8.1218 | 172,528 | 455 | 0 | 0.0% | 0 |
| aider-sonnet | 1h19m47s | 0 | 145,100.0 | 142,946.0 | 0.0 | 0.0% | 60.2 | $1.7300 | 72,012 | 174 | 0 | 0.0% | 0 |
| aider-qwen-max | 0h45m03s | 0 | 0 | 0 | 0 | 0.0% | 0.0 | n/a | 0 | 0 | 0 | 0.0% | 0 |
| aider-glm-53 | 0h41m27s | 0 | 82,600.0 | 234,467.0 | 0.0 | 0.0% | 127.5 | $0.5500 | 105,689 | 216 | 0 | 0.0% | 0 |
| aider-codex | 0h09m28s | 0 | 136,500.0 | 28,833.0 | 0.0 | 0.0% | 291.1 | $1.5500 | 27,556 | 92 | 0 | 0.0% | 0 |
| oh-my-humanize-sonnet | 1h49m42s | 204 | 240,679.0 | 279,817.0 | 25,820,846.0 | 99.1% | 4002.0 | $8.5638 | 520,496 | 231 | 209 | 2.9% | 2385 |
| oh-my-humanize-opus | 1h53m20s | 116 | 293,160.0 | 121,784.0 | 10,394,695.0 | 97.3% | 1589.7 | $10.0739 | 69,157 | 141 | 116 | 4.3% | 1109 |
| oh-my-humanize-fable | 5h33m47s | 110 | 447,839.0 | 165,704.0 | 8,982,027.0 | 95.3% | 479.1 | $22.7280 | 204,514 | 378 | 124 | 7.3% | 169 |
| opencode-fable | 1h01m31s | 0 | 293,786.0 | 104,449.0 | 5,156,804.0 | 94.6% | 1505.0 | $15.2906 | 99,559 | 196 | 0 | 0.0% | 0 |
| aider-fable | 0h51m16s | 0 | 41,200.0 | 75,628.0 | 0.0 | 0.0% | 38.0 | $4.2000 | 58,414 | 78 | 0 | 0.0% | 0 |

## Plots
### tokens over time
![](tokens_over_time.png)
### cost over time
![](cost_over_time.png)
### tool usage
![](tool_usage.png)
### tokens per commit
![](tokens_per_commit.png)

## Per-run insights
- **claude-code-opus5**: 0h55m22s, 102 calls, 15,432,446.0 tokens (98.5% cached), 0 commits, 0 lines added (2891 total), 15,432,446 tok/commit, 5,338 tok/line
- **oh-my-humanize-kimi-k3**: 0h30m41s, 85 calls, 3,853,781.0 tokens (97.7% cached), 0 commits, 0 lines added (1130 total), 3,853,781 tok/commit, 3,410 tok/line, $1.8073
- **oh-my-humanize-qwen38**: 3h05m40s, 385 calls, 39,577,492.0 tokens (96.5% cached), 0 commits, 0 lines added (2496 total), 39,577,492 tok/commit, 15,856 tok/line, $4.3427
- **oh-my-humanize-qwen-max**: 3h44m25s, 169 calls, 33,062,225.0 tokens (91.8% cached), 3 commits, 2051 lines added (2051 total), 11,020,742 tok/commit, 16,120 tok/line, $14.3309
- **oh-my-humanize-ox-alpha**: 1h38m15s, 204 calls, 23,828,024.0 tokens (98.4% cached), 11 commits, 2119 lines added (2202 total), 2,166,184 tok/commit, 11,245 tok/line, $0.4081
- **oh-my-humanize-glm-53**: 1h55m01s, 156 calls, 23,842,891.0 tokens (99.0% cached), 2 commits, 2638 lines added (2721 total), 11,921,446 tok/commit, 9,038 tok/line, $7.1229
- **claude-code-sonnet**: 1h30m36s, 138 calls, 23,480,820.0 tokens (98.9% cached), 6 commits, 2276 lines added (2276 total), 3,913,470 tok/commit, 10,317 tok/line
- **oh-my-humanize-codex**: 0h03m09s, 16 calls, 490,470.0 tokens (88.8% cached), 0 commits, 0 lines added (83 total), 490,470 tok/commit, 5,909 tok/line, $0.9279
- **opencode-qwen**: 2h00m34s, 0 calls, 7,141,631.0 tokens (97.9% cached), 1 commits, 1933 lines added (2016 total), 7,141,631 tok/commit, 3,695 tok/line, $1.0001
- **opencode-kimi**: 3h19m02s, 0 calls, 7,091,484.0 tokens (95.3% cached), 5 commits, 1209 lines added (1209 total), 1,418,297 tok/commit, 5,866 tok/line, $5.5294
- **aider-qwen**: 1h44m24s, 0 calls, 183,700.0 tokens (0.0% cached), 2 commits, 1703 lines added (1786 total), 91,850 tok/commit, 108 tok/line, $0.4000
- **aider-kimi**: 0h29m10s, 0 calls, 193,412.0 tokens (0.0% cached), 2 commits, 1126 lines added (1209 total), 96,706 tok/commit, 172 tok/line, $1.6700
- **opencode-opus**: 3h55m47s, 0 calls, 26,474,300.0 tokens (93.9% cached), 3 commits, 4529 lines added (4529 total), 8,824,767 tok/commit, 5,846 tok/line, $36.6583
- **opencode-sonnet**: 0h32m05s, 0 calls, 7,213,616.0 tokens (93.5% cached), 1 commits, 1949 lines added (1949 total), 7,213,616 tok/commit, 3,701 tok/line, $3.6547
- **opencode-qwen-max**: 1h51m21s, 0 calls, 8,540,994.0 tokens (95.2% cached), 1 commits, 2563 lines added (2646 total), 8,540,994 tok/commit, 3,332 tok/line, $4.7083
- **opencode-glm-53**: 2h28m44s, 0 calls, 16,523,738.0 tokens (92.0% cached), 5 commits, 2871 lines added (2871 total), 3,304,748 tok/commit, 5,755 tok/line, $4.6555
- **opencode-codex**: 2h54m15s, 0 calls, 5,196,753.0 tokens (91.7% cached), 3 commits, 1137 lines added (1220 total), 1,732,251 tok/commit, 4,571 tok/line, $8.1218
- **aider-sonnet**: 1h19m47s, 0 calls, 288,046.0 tokens (0.0% cached), 4 commits, 1658 lines added (1741 total), 72,012 tok/commit, 174 tok/line, $1.7300
- **aider-qwen-max**: 0h45m03s, 0 calls, 0 tokens (0.0% cached), 2 commits, 2034 lines added (2117 total), 0 tok/commit, 0 tok/line
- **aider-glm-53**: 0h41m27s, 0 calls, 317,067.0 tokens (0.0% cached), 3 commits, 1466 lines added (1549 total), 105,689 tok/commit, 216 tok/line, $0.5500
- **aider-codex**: 0h09m28s, 0 calls, 165,333.0 tokens (0.0% cached), 6 commits, 1798 lines added (1881 total), 27,556 tok/commit, 92 tok/line, $1.5500
- **oh-my-humanize-sonnet**: 1h49m42s, 204 calls, 26,341,342.0 tokens (99.1% cached), 1 commits, 2258 lines added (2341 total), 26,341,342 tok/commit, 11,666 tok/line, $8.5638
- **oh-my-humanize-opus**: 1h53m20s, 116 calls, 10,809,639.0 tokens (97.3% cached), 6 commits, 2933 lines added (2933 total), 1,801,606 tok/commit, 3,686 tok/line, $10.0739
- **oh-my-humanize-fable**: 5h33m47s, 110 calls, 9,595,570.0 tokens (95.3% cached), 3 commits, 1623 lines added (1623 total), 3,198,523 tok/commit, 5,912 tok/line, $22.7280
- **opencode-fable**: 1h01m31s, 0 calls, 5,555,039.0 tokens (94.6% cached), 4 commits, 2034 lines added (2117 total), 1,388,760 tok/commit, 2,731 tok/line, $15.2906
- **aider-fable**: 0h51m16s, 0 calls, 116,828.0 tokens (0.0% cached), 2 commits, 1506 lines added (1589 total), 58,414 tok/commit, 78 tok/line, $4.2000
