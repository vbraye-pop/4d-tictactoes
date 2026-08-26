# 4D Tic-Tac-Toe

A four-dimensional tic-tac-toe game for the browser, served by a small Python
HTTP server. Two humans, or human against a strong machine opponent.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```bash
python3 server.py
```

Visit <http://localhost:8420>.

The server prints the URL to its output. Any session you no longer need can
be discarded; sessions live only in server memory.

## Tests

```bash
.venv/bin/python -m pytest tests/ -q
```

## How to play

- Cells of the 3x3x3x3 board are laid out as a 3-by-3 grid of 3-by-3 planes,
  with the outer grid varying along `w` and `z`, and the inner grid varying on
  `y` and `x`. Hover a cell to see its `(x,y,z,w)` coordinates in the status
  bar and as a tooltip.
- Choose Human vs Human or Human vs AI at the top. In AI mode pick X or O,
  then press **New game**.
- Click an empty cell to place your mark. A win is declared when you complete
  a cross of yours; the board highlights all five cells.
- A cross is two straight lines of three consecutive cells (any of the 40
  four-dimensional directions) sharing a common middle cell. There are 1548
  possible winning crosses; the machine precomputes them at import time.

## Rules summary

- 81 cells, coordinates each in {0, 1, 2}. X starts.
- You win the moment a move finishes any of the 1548 crosses.
- A literal draw after 81 full cells is mathematically impossible here:
  SAT-checked, every full coloring contains a monochromatic cross owned by
  that color. The in-game draw branch still exists for robustness but is
  unreachable in real play.

## AI

Priority order: immediate winning move, blocking the opponent's winning move,
exact minimax solving when nine or fewer cells remain, otherwise a heuristic
that weighs partial crosses superlinearly. The machine answers after a short
bounded server-side delay so the game is easy to follow.

## Project structure

- `game.py` — board, cross enumeration, move and game state, AI
- `server.py` — HTTP server, static file serving, session handling, JSON API
- `static/index.html`, `static/style.css`, `static/app.js` — frontend
- `tests/test_game.py` — pure Python test suite for the game logic

## Technical notes

- Python ≥ 3.10, standard library only at runtime. `pytest` listed in
  `requirements.txt` purely for the test suite.
- Fully offline: no external calls, no CDN, no build step.
- Files are served from the `static/` folder with a strict
  path-resolution guard against directory traversal.
