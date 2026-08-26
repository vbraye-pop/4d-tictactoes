#!/usr/bin/env python3
"""Local server for 4D tic-tac-toe.

Serves the static frontend and a small JSON API:

    GET  /api/state       current game state
    POST /api/move        {"cell": n} play a human move
    POST /api/new         {"mode": "pvp" | "ai"} start a new game

In "ai" mode the human is X (moves first); the AI is O and answers after a
short bounded delay. The AI move is computed on a worker thread.

Usage:
    python3 server.py [--port 8742]
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game import O, X, Board, coord_of  # noqa: E402
from game import ai  # noqa: E402

DEFAULT_PORT = 8742
AI_DELAY_SECONDS = 0.7
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

DIM_NAMES = ("X", "Y", "Z", "W")


def line_label(a: int, b: int) -> str:
    """Human label for the direction of the 3-cell line a - c - b."""
    ca, cb = coord_of(a), coord_of(b)
    changed = [DIM_NAMES[i] for i in range(4) if ca[i] != cb[i]]
    if not changed:
        return "degenerate"
    if len(changed) == 1:
        return f"{changed[0]} axis"
    return "-".join(changed) + " diagonal"


def cross_payload(cross) -> dict:
    cells = list(cross.cells)
    counts = {str(w): 0 for w in range(3)}
    for cell in cells:
        counts[str(coord_of(cell)[3])] += 1
    return {
        "cells": cells,
        "center": cross.center,
        "lines": [list(cross.line1), list(cross.line2)],
        "line_labels": [line_label(cross.line1[0], cross.line1[2]),
                        line_label(cross.line2[0], cross.line2[2])],
        "slice_counts": counts,
    }


class Game:
    """One game with thread-safe state and an AI worker."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.mode = "pvp"
        self.board = Board()
        self.ai_pending = False
        self.generation = 0

    def new_game(self, mode: str) -> dict:
        with self.lock:
            self.board = Board()
            self.mode = mode
            self.ai_pending = False
            self.generation += 1
        return self.state()

    def human_move(self, cell: int) -> tuple[dict | None, str | None]:
        with self.lock:
            if not isinstance(cell, int) or not 0 <= cell < 81:
                return None, "cell must be an integer 0..80"
            if self.board.is_over:
                return None, "game is over"
            if self.mode == "ai" and self.board.to_move == O:
                return None, "the AI is thinking"
            if not self.board.is_legal(cell):
                return None, "cell is already taken"
            self.board.play(cell)
            need_ai = (
                self.mode == "ai"
                and not self.board.is_over
                and self.board.to_move == O
            )
            gen = self.generation
            self.ai_pending = need_ai
        if need_ai:
            threading.Thread(target=self._ai_play, args=(gen,), daemon=True).start()
        return self.state(), None

    def _ai_play(self, gen: int) -> None:
        start = time.monotonic()
        with self.lock:
            x, o = self.board.x, self.board.o
        cell, _value = ai.ai_move(x, o, O)
        elapsed = time.monotonic() - start
        if elapsed < AI_DELAY_SECONDS:
            time.sleep(AI_DELAY_SECONDS - elapsed)
        with self.lock:
            if gen != self.generation or self.board.is_over or self.board.to_move != O:
                return
            self.board.play(cell)
            self.ai_pending = False

    def state(self) -> dict:
        with self.lock:
            b = self.board
            cells = ["."] * 81
            for i in range(81):
                if b.x >> i & 1:
                    cells[i] = "X"
                elif b.o >> i & 1:
                    cells[i] = "O"
            slice_counts = {str(w): {"X": 0, "O": 0, "free": 0} for w in range(3)}
            for i in range(81):
                slot = slice_counts[str(coord_of(i)[3])]
                if cells[i] == ".":
                    slot["free"] += 1
                else:
                    slot[cells[i]] += 1
            return {
                "mode": self.mode,
                "to_move": b.to_move,
                "winner": b.winner,
                "draw": b.draw,
                "ai_pending": self.ai_pending,
                "move_count": b.move_count(),
                "cells": cells,
                "last_move": b.last_move,
                "winning_cross": cross_payload(b.winning_cross) if b.winning_cross else None,
                "slice_counts": slice_counts,
            }


GAME = Game()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # quiet
        pass

    def _send_json(self, obj: dict, status: int = 200) -> None:
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str) -> None:
        if not os.path.isfile(path):
            self._send_json({"error": "not found"}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/api/state":
            self._send_json(GAME.state())
            return
        if path == "/":
            path = "/index.html"
        root = os.path.realpath(STATIC_DIR)
        target = os.path.realpath(os.path.join(root, path.lstrip("/")))
        if not target.startswith(root):
            self._send_json({"error": "forbidden"}, 403)
            return
        self._send_file(target)

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b""
            return json.loads(raw) if raw else None
        except (ValueError, json.JSONDecodeError):
            return None

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        payload = self._read_json()
        if payload is None:
            self._send_json({"error": "invalid JSON body"}, 400)
            return
        if path == "/api/move":
            state, error = GAME.human_move(payload.get("cell"))
            if error:
                self._send_json({"error": error}, 409)
            else:
                self._send_json(state)
        elif path == "/api/new":
            mode = payload.get("mode")
            if mode not in ("pvp", "ai"):
                self._send_json({"error": "mode must be 'pvp' or 'ai'"}, 400)
                return
            self._send_json(GAME.new_game(mode))
        else:
            self._send_json({"error": "not found"}, 404)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve 4D tic-tac-toe.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://localhost:{args.port}"
    print(f"4D Tic-Tac-Toe is running at {url}  (Ctrl+C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
