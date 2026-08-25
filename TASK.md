# Task: 4D Tic-Tac-Toe

Build a fully playable, polished browser game: 4D tic-tac-toe on a 3x3x3x3 board, implemented in Python and served by a local Python server. Read this file completely before you start. This is an end-to-end task. Implement the game, run it, test it, and deliver a finished product. A prototype is not an acceptable deliverable.

## Game rules

- The board is a 3x3x3x3 grid of 81 cells. Each cell is identified by four coordinates, one per dimension, each in {0, 1, 2}.
- Two players, X and O. X moves first. Players alternate, placing one mark on an empty cell per turn.
- A player wins by owning all the cells of a winning cross (defined below).
- The game ends in a draw when all 81 cells are filled and no cross has been formed.

### Winning cross, exact definition

A winning cross is the set of 5 cells:

```
{c, c - d1, c + d1, c - d2, c + d2}
```

where `c` is a board cell (the center), `d1` and `d2` are nonzero vectors in {-1, 0, 1}^4, `d2` is neither `d1` nor `-d1`, and all five cells lie inside the board.

Equivalently, a cross is two straight lines of three consecutive cells (in any of the 40 directions of the 4D grid) that cross at their common middle cell. Diagonal lines count, and the two lines do not need to be axis-aligned.

Intuition check: restricted to a 2D 3x3 board, this rule gives exactly six shapes. The plus (+), the X (both diagonals), and four mixed shapes made of one full line plus one diagonal crossing at the center. The 4D rule is the same idea in four dimensions.

There are exactly **1548** distinct winning crosses on the 3x3x3x3 board. Use this number to verify your implementation. A player wins the moment their move completes any one of these crosses.

### AI opponent

The game offers two modes: Human vs Human and Human vs AI.

The AI does not need to be perfect, but it must satisfy all three of the following:

- Take an immediate winning move when one exists.
- Block the cell where the opponent would complete a cross on the next turn.
- Otherwise play a reasonable heuristic move. Prefer the center, build toward crosses, and never play random cells.

Apply the AI move with a short bounded delay so a human can follow the game.

## UI requirements

- The game runs in a browser at a localhost URL served by the Python server.
- How the player navigates the 4D board is your design decision. Whatever you build, it must be easy to find, read, and play any of the 81 cells.
- The UI must always show whose turn it is and which part of the 4D board is currently displayed (the current 4D coordinates). Every cell must be reachable and its state must be visible.
- Clicking an empty cell in the current view places the current player's mark there. Clicking an occupied cell, or any cell after the game has ended, does nothing.
- On a win, declare the winner clearly and highlight all five cells of the winning cross, including how the cross spans the dimensions. Lock the board.
- On a draw, declare it clearly.
- Provide a new game control, and let the player choose between Human vs Human and Human vs AI.
- This must look and feel like a finished product, not a prototype. Clean modern visuals, consistent styling, clear affordances, no default browser look. Desktop first (modern Chrome or Firefox). A mobile layout is a plus.

## Technical constraints

- Backend in Python 3 (3.10+). Standard library or pip-installable packages, your choice.
- Frontend in vanilla HTML, CSS, and JavaScript, served by the Python server. No npm, no bundler, no build step, no other runtime.
- Fully offline at runtime. No external network calls, no CDNs, no API keys.
- The game starts with a single command from the project root, documented in README.md, which prints the URL to open. Pick a localhost port and document it.
- It must run on a standard macOS machine with nothing installed beyond the Python packages in requirements.txt.

## Tests

- Write automated tests for the game logic, not for the UI.
- Cover at minimum: move legality, win detection, draw detection, and the AI taking a win and blocking a win.
- Include a test that every one of the 1548 winning crosses is detected as a win when a player completes it, and that a set of 5 cells which is not a cross is not detected as a win.
- The suite must run with a single documented command.

## Deliverables

- The game code in this repository.
- README.md updated to match reality: what this is, how to run it (the exact command), how to play, the rules summary, and the project structure.
- requirements.txt, if you use third-party packages.
- Git hygiene: commit your work as you progress, with clear messages. Do not commit this TASK.md. Do not commit caches or artifacts (`__pycache__`, `.pytest_cache`, `.DS_Store`, `node_modules`).

## Definition of done

Before you stop, all of the following must be true:

1. The test command passes.
2. The server starts with the single documented command, and the page loads in a browser with no console errors.
3. You played a real game in the browser: a win was detected and highlighted, the board locked, and new game worked.
4. The draw path works.
5. In AI mode, the AI takes an available win and blocks an imminent opponent win.
6. README.md matches what the project actually does.
