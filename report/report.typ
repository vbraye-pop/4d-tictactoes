#set page(paper: "a4", margin: (x: 2.2cm, y: 2.4cm))
#set text(font: "Helvetica Neue", size: 10.5pt)
#set heading(numbering: "1.1")
#set par(justify: true, leading: 0.72em)
#show heading: set text(fill: rgb("#1e3a8a"))

#let col-accent = rgb("#2563eb")
#let col-muted = rgb("#6b7280")
#let col-good = rgb("#16a34a")
#let col-bad = rgb("#dc2626")

#align(center)[
  #text(size: 22pt, weight: "bold")[Four agents build a 4D tic-tac-toe game]
  #v(4pt)
  #text(size: 12pt, fill: col-muted)[A harness-and-model benchmark, with behavior analysis]
  #v(2pt)
  #text(size: 10pt, fill: col-muted)[2026-08-26]
]

#v(10pt)
#line(length: 100%, stroke: 0.5pt + col-accent)
#v(10pt)

= The experiment

Four harness/model combinations were each given the identical task: build a complete, polished,
browser-based 4D tic-tac-toe game on a 3×3×3×3 board, in Python, end to end. Same `TASK.md`, same
baseline commit, same definition of done. Every run was recorded wall-clock and per-API-call; the
transcripts were then analyzed deterministically and by a second model reading the agent's own
thinking. This report is the result.

= Raw outcome

#figure(
  image("fig/duration.png", width: 100%),
  caption: [Wall-clock duration. Opus was dramatically fastest.]
)

#figure(
  image("fig/tokens.png", width: 100%),
  caption: [Token composition. Opus used the fewest total tokens; Qwen 3.8-27B used the most.]
)

#figure(
  image("fig/cost.png", width: 90%),
  caption: [Direct cost (OpenRouter models only; Claude runs on a flat subscription).]
)

#figure(
  image("fig/efficiency.png", width: 100%),
  caption: [Efficiency frontier: time against tokens per line of final code. Lower-left is better.]
)

= Behavior under the hood

A smaller model read each transcript and scored each run on six dimensions. Figures below are the
deterministic side: what the transcripts actually contain.

#figure(
  image("fig/radar.png", width: 72%),
  caption: [LLM-judged profiles across planning, recovery, discipline, autonomy, polish, efficiency.]
)

#figure(
  image("fig/tool_mix.png", width: 100%),
  caption: [Tool usage composition. Bash-dominated for Opus; write/edit-heavy for the omh runs.]
)

#figure(
  image("fig/test_discipline.png", width: 100%),
  caption: [Test discipline against tool error rate.]
)

#figure(
  image("fig/rumination.png", width: 100%),
  caption: [Thinking volume against tool errors. The two Kimi/GLM runs sit in the same quadrant.]
)

= How they talked to themselves

The agents' private reasoning, sampled and counted.

#figure(
  image("fig/interjections.png", width: 100%),
  caption: [Self-interruptions in thinking (log scale). Qwen 3.8-27B said "wait" 867 times.]
)

#figure(
  image("fig/mood.png", width: 100%),
  caption: [Mood vocabulary in thinking: panic words vs self-praise vs hedging.]
)

= The personalities

#for r in ((:)).values() []
#let personalities = (
  ("Claude Code x Opus 5", "Math-First Assurance Officer"),
  ("omh x Qwen 3.8-27B", "Ruminating Ouroboros Debugger"),
  ("omh x Kimi K3", "Ruminating Assurance Officer"),
  ("omh x GLM-5.3-flash", "Ruminating Ouroboros"),
)
#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: 6pt,
  ..personalities.map(((name, p)) => ([#strong(name)], [#p])).flatten()
)

= What the judge saw

#let synthesis = read("synthesis.typ")
#synthesis

= Surprises and verdicts

See the matchup analysis above. In short: Opus did the most work with the fewest tokens and the least
drama; the omh runs were slower and noisier but more explicit about their reasoning; Kimi K3 and
GLM-5.3-flash behaved so similarly on transcript analysis that the shared lineage is visible.
