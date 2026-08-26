# 4D Tic-Tac-Toe

A fully playable browser game: tic-tac-toe on a 3x3x3x3 board (81 cells) in
four dimensions. Two players (X and O, X first) alternate placing marks; the
first to own all five cells of a winning cross wins. Human vs Human or Human
vs AI. Python server, vanilla HTML/CSS/JS frontend, fully offline.

## Run it

From the project root:

```
python3 server.py
```

Then open the printed URL, http://localhost:8742 (use `--port N` to change it).

Python 3.10+ is required. The server itself uses only the standard library.

## Tests

```
pip install -r requirements.txt
python3 -m pytest
```

The suite covers cross geometry (all 1548 crosses, shape invariants, the 2D
limit), move legality, win and draw detection, and the AI (immediate wins,
blocking, provable endgame optimality, determinism). It runs in about two
seconds.

## How to play

You see one W-slice of the board at a time: three Z-layers of 3x3 grids. A
cell's full 4D coordinates (x, y, z, w) are shown on hover; the active slice
and the current turn are always displayed, and the slice overview on the right
tracks all three W-slices (X / O / free counts).

- Click a W tab to switch between the three 27-cell W-slices. Every one of
  the 81 cells is reachable this way.
- Click an empty cell to place the current player's mark.
- Choose Human vs Human or Human vs AI with the buttons in the header (the
  human is X and moves first in AI mode; the AI answers after a short delay).
- On a win, the five cells of the winning cross are highlighted (with a dot on
  every W tab that contains part of the cross) and the panel shows the center,
  both lines, and which axes or diagonals they run along. The board locks.
- A new game can be started at any time.

## Rules

The board is the 4D grid {0, 1, 2}^4, 81 cells. A winning cross is the set of
five cells

    {c, c - d1, c + d1, c - d2, c + d2}

where c is a board cell (the center) and d1, d2 are nonzero vectors in
{-1, 0, 1}^4, d2 not equal to d1 or -d1, all five cells on the board.
Equivalently: two straight 3-cell lines (any of the 40 directions of the 4D
grid, diagonals included) crossing at their common middle cell. Restricted to
a 2D 3x3 board this rule gives exactly six shapes: the plus, the X, and four
mixed line-plus-diagonal crosses.

There are exactly 1548 distinct winning crosses on the full board; the engine
generates them and pins the count in tests.

### A note on draws

The rules define a draw as a full board with no cross formed. That state is
unreachable in play: the 1548-cross hypergraph on 81 cells is not
2-colorable (verified with an independent SAT solve and an MILP infeasibility
proof during development), so every 2-coloring of the full board contains a
monochromatic cross and every game ends in a win, on or before move 81. The
draw rule is implemented and tested at the state-machine level (a full board
with no winner reports a draw), and the UI renders the draw state, but you
will never reach it by playing.

## The AI

The AI (O in AI mode) selects moves in priority order:

1. Take an immediate win if one exists.
2. If the opponent has two or more open winning cells, the position is
   provably lost; play the best principled move anyway.
3. If the opponent has exactly one open winning cell, block it (the only move
   that does not lose at once). In endgame positions the blocked continuation
   is evaluated exactly.
4. In endgame positions (at most 12 empty cells) the game is evaluated
   exactly with alpha-beta search, a transposition table, and forced-line
   pruning; the returned value (+1 win / -1 loss) is provable. Dense 4D
   endgames are saturated with 4-of-5 positions, so in practice the search is
   resolved quickly through the forced lines; a node budget bounds the
   worst case and falls back to the best principled move.
5. Everywhere else the AI plays the highest-scoring principled move: complete
   a cross, build a double threat (a fork the opponent cannot answer), build a
   threat, block a threat, then maximize live-cross potential with a small
   center bias. It never plays randomly.

The move is applied after a short bounded delay (0.7 s) so a human can follow
the game.

## Project structure

```
server.py            HTTP server (stdlib): static files + JSON API, AI worker
game/
  board.py           cells, cross generation (1548), Board state machine
  ai.py              threat/wine detection, exact search, move selection
static/
  index.html         page
  style.css          dark theme, responsive
  app.js             rendering, turn flow, polling, view state
tests/
  test_crosses.py    cross geometry: count, shape, 2D limit
  test_rules.py      legality, alternation, win, draw state, theorem pin
  test_ai.py         wins, blocks, dense endgame proofs, determinism
  test_server.py     game object: flow, rejections, serialization
```

## API

```
GET  /api/state            current state
POST /api/move  {"cell"}   play a human move (409 on illegal)
POST /api/new {"mode"}     new game, mode "pvp" or "ai"
```

State includes the 81 cells, to-move, winner, draw flag, AI-pending flag, the
winning cross (cells, center, lines, labels, per-slice counts) and per-slice
occupancy.
