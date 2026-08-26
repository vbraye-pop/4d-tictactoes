# 4D Tic-Tac-Toe

Tic-tac-toe on a 3 x 3 x 3 x 3 board: 81 cells, 1548 ways to win, and an
opponent that solves the position exactly whenever it can afford to.

The game logic, the search and the web server are plain Python 3 with no
third-party packages. The browser front end is vanilla HTML, CSS and
JavaScript served by that server. Nothing is fetched from the network at
runtime.

## Run it

From the project root:

```
python3 run.py
```

The server prints the URL and listens on **http://127.0.0.1:8421/**. Open that
in Chrome or Firefox. Use `--port` to pick a different port.

Nothing needs installing. `requirements.txt` exists but is empty of packages,
so `python3 -m pip install -r requirements.txt` is a no-op if you prefer to run
it.

## Run the tests

```
python3 -m unittest discover -s tests -t .
```

58 tests, about 30 seconds. They cover the cross geometry (including a check
that all 1548 crosses are detected and that non-cross shapes are not), move
legality, win and draw detection, the incremental search state, the AI's
tactics and endgame optimality, and the HTTP API.

## How to play

All 81 cells are on screen at once. The board is a 3 x 3 grid of 3 x 3
boards:

- the **outer** grid picks the first two coordinates, `x` down and `y` across;
- the **inner** grid picks the last two, `z` down and `w` across.

Every sub-board is labelled with its own `x` and `y`, so any cell can be read
off directly as `x y z w`. The side panel always shows the coordinates of the
cell under the cursor, whose turn it is, and the move log.

- **Mouse**: click a free cell to place a mark.
- **Keyboard**: arrow keys move inside the current sub-board, `Shift` + arrows
  jump between sub-boards, `Enter` or `Space` places a mark.
- **Opponent**: choose *Two players* or *Computer*; in computer mode pick
  whether you play X or O. Changing either starts a new game.
- **New game** resets at any time. The game is also restored if you reload the
  page.
- **Mark cells that win immediately** highlights, for the side to move, every
  cell that would complete a cross right now. It is off by default.

When someone wins, the five cells light up, the two lines of the cross are
drawn across the sub-boards they span, the five coordinates and the directions
of the two lines are listed in the result card, and the board locks.

## The rules

A **winning cross** is five cells:

```
{ c, c - d1, c + d1, c - d2, c + d2 }
```

for a centre cell `c` and two directions `d1`, `d2` in {-1, 0, 1}^4, neither
zero, with `d2` not parallel to `d1`, all five cells on the board. Put
differently: two straight three-in-a-row lines that cross at their middle cell.
Any of the 40 directions of the 4D grid counts, diagonals included, and the two
lines need not be axis-aligned.

There are exactly **1548** such crosses. X moves first; players alternate;
the first to own all five cells of any cross wins.

### A draw cannot happen

Every way of filling all 81 cells with two colours contains a monochromatic
cross. This was checked with a SAT solver: the constraint "no cross is
monochromatic" over 81 boolean variables is unsatisfiable, and the largest
cross-free position covers 80 of the 81 cells. So a 4D game always produces a
winner, usually well before the board fills.

The code still implements and reports draws, because the rules call for it. The
draw path is exercised in the tests through the same engine restricted to two
dimensions, where the board is a 3 x 3 grid with six crosses and draws do
occur.

## The opponent

`fourd/ai.py` picks a move in three layers.

1. **Tactics.** If a cross can be completed now, complete it. Otherwise, if the
   opponent can complete one next turn, take that cell. Both are forced.
2. **Exact solution.** A negamax search with alpha-beta pruning and a
   transposition table, given a time budget. Two observations make this cheap
   far earlier than the endgame: a side to move that has a winning cell simply
   wins, and a side facing two distinct winning cells has already lost. With
   1548 crosses on 81 cells, positions are dense in threats, so most midgame
   positions solve outright in well under a second, and the move played is then
   provably optimal.
3. **Threat search.** When the exact search runs out of time, an
   iterative-deepening alpha-beta over the most promising cells, scored by how
   close each cross is to completion.

Positions are bitboards, two 81-bit integers. `fourd/engine.py` keeps a running
count of both players' marks in every cross, and maintains from those counts an
evaluation and a per-player map of cells that win immediately, updated on each
make and unmake. That map is what makes the forced-move shortcuts above cheap.

A move is bounded by the search budgets: 1.5 s for an exact solve near the end,
0.5 s for the attempt earlier on, and 0.8 s for the fallback search, so roughly
2.4 s in the worst case. In practice moves land in well under a second. The
browser holds every computer move on screen for at least 480 ms so it can be
followed.

## Project structure

```
run.py               start the server, print the URL
requirements.txt     no third-party packages
fourd/
  crosses.py         cross generation for a 3^n board; the 1548 masks
  board.py           game state, move legality, win and draw detection
  engine.py          incremental bitboard position used by the search
  ai.py              tactics, exact solver, threat search
  server.py          static files plus the JSON game API
web/
  index.html         the page
  style.css          the styling
  app.js             board rendering, input, and API calls
tests/
  helpers.py         reference minimax and shared fixtures
  test_crosses.py    cross geometry, the count of 1548, the 2D shapes
  test_board.py      legality, win detection, draw detection
  test_engine.py     incremental state against a direct scan
  test_ai.py         tactics, endgame optimality, general strength
  test_server.py     the HTTP API
```

## The HTTP API

| Method | Path            | Body                        | Returns                |
|--------|-----------------|-----------------------------|------------------------|
| GET    | `/`             |                             | the page               |
| GET    | `/api/state`    | `?id=<game>`                | the game state         |
| POST   | `/api/new`      | `{mode, aiSide}`            | a new game state       |
| POST   | `/api/move`     | `{id, cell}`                | the state after a move |
| POST   | `/api/ai`       | `{id}`                      | the state after the computer moves |

`mode` is `hvh` or `hva`, `cell` is an index in 0..80 equal to
`27x + 9y + 3z + w`. Illegal moves answer `409` with the unchanged state, so
the board can never drift out of step with the server.
