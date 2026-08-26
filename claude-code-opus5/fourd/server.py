"""Local HTTP server: static frontend plus a small JSON game API."""

from __future__ import annotations

import json
import mimetypes
import threading
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .ai import choose_move
from .board import DRAW, ONGOING, O, WIN, X, Game, IllegalMove, other
from .crosses import RULES_4D

WEB_ROOT = Path(__file__).resolve().parent.parent / "web"
HUMAN_VS_HUMAN = "hvh"
HUMAN_VS_AI = "hva"
MAX_SESSIONS = 200
AI_BUDGET = 0.8


class Session:
    def __init__(self, mode: str, ai_side: str):
        self.id = uuid.uuid4().hex
        self.mode = mode
        self.ai_side = ai_side
        self.game = Game()
        self.last_ai = None

    @property
    def ai_to_move(self) -> bool:
        return (self.mode == HUMAN_VS_AI and self.game.status == ONGOING
                and self.game.to_move == self.ai_side)

    def snapshot(self) -> dict:
        game = self.game
        cells = [None] * RULES_4D.cell_count
        for player in (X, O):
            board = game.boards[player]
            for cell in range(RULES_4D.cell_count):
                if board >> cell & 1:
                    cells[cell] = player
        return {
            "id": self.id,
            "mode": self.mode,
            "aiSide": self.ai_side if self.mode == HUMAN_VS_AI else None,
            "cells": cells,
            "toMove": game.to_move,
            "status": game.status,
            "winner": game.winner,
            "winningCross": list(game.winning_cross) if game.winning_cross else None,
            "lastMove": game.history[-1][1] if game.history else None,
            "history": [[player, cell] for player, cell in game.history],
            "moveCount": game.move_count,
            "aiToMove": self.ai_to_move,
            "lastAi": self.last_ai,
            "threats": self._threats(),
        }

    def _threats(self) -> dict:
        """Cells that would win right now, per player, for the hint overlay."""
        from .engine import Position
        position = Position(self.game.boards[X], self.game.boards[O])
        return {player: sorted(position.winning_cells(player)) for player in (X, O)}


class Sessions:
    def __init__(self):
        self._lock = threading.Lock()
        self._store: "OrderedDict[str, Session]" = OrderedDict()

    def create(self, mode: str, ai_side: str) -> Session:
        session = Session(mode, ai_side)
        with self._lock:
            self._store[session.id] = session
            while len(self._store) > MAX_SESSIONS:
                self._store.popitem(last=False)
        return session

    def get(self, session_id: str) -> Session:
        with self._lock:
            session = self._store.get(session_id)
            if session is None:
                raise KeyError(session_id)
            self._store.move_to_end(session_id)
            return session


SESSIONS = Sessions()


class Handler(BaseHTTPRequestHandler):
    server_version = "FourDTicTacToe/1.0"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if self.server.verbose:
            super().log_message(fmt, *args)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            query = parse_qs(urlparse(self.path).query)
            ids = query.get("id") or [""]
            self._with_session(ids[0], lambda session: session.snapshot())
            return
        self._static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            payload = self._body()
        except ValueError as exc:
            self._json(400, {"error": str(exc)})
            return

        if path == "/api/new":
            mode = payload.get("mode", HUMAN_VS_HUMAN)
            ai_side = payload.get("aiSide", O)
            if mode not in (HUMAN_VS_HUMAN, HUMAN_VS_AI) or ai_side not in (X, O):
                self._json(400, {"error": "bad mode or side"})
                return
            session = SESSIONS.create(mode, ai_side)
            self._json(200, session.snapshot())
            return

        if path == "/api/move":
            cell = payload.get("cell")
            if not isinstance(cell, int):
                self._json(400, {"error": "cell must be an integer"})
                return
            self._with_session(payload.get("id", ""), lambda s: self._play(s, cell))
            return

        if path == "/api/ai":
            self._with_session(payload.get("id", ""), self._ai_move)
            return

        self._json(404, {"error": "unknown endpoint"})

    def _play(self, session: Session, cell: int) -> dict:
        if session.ai_to_move:
            raise IllegalMove("it is the computer's turn")
        session.game.play(cell)
        session.last_ai = None
        return session.snapshot()

    def _ai_move(self, session: Session) -> dict:
        if not session.ai_to_move:
            raise IllegalMove("it is not the computer's turn")
        game = session.game
        decision = choose_move(game.boards[X], game.boards[O], game.to_move, AI_BUDGET)
        game.play(decision.cell)
        session.last_ai = {
            "cell": decision.cell,
            "reason": decision.reason,
            "detail": decision.detail,
            "exact": decision.exact,
            "depth": decision.depth,
            "nodes": decision.nodes,
            "seconds": round(decision.elapsed, 3),
        }
        return session.snapshot()

    def _with_session(self, session_id, action):
        try:
            session = SESSIONS.get(session_id or "")
        except KeyError:
            self._json(404, {"error": "no such game"})
            return
        try:
            self._json(200, action(session))
        except IllegalMove as exc:
            self._json(409, {"error": str(exc), "state": session.snapshot()})

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        if length > 64_000:
            raise ValueError("request too large")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("invalid JSON body")

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path: str):
        relative = "index.html" if path in ("/", "") else path.lstrip("/")
        target = (WEB_ROOT / relative).resolve()
        if not target.is_file() or WEB_ROOT not in target.parents:
            self._json(404, {"error": "not found"})
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def make_server(host: str, port: int, verbose: bool = False) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.verbose = verbose
    httpd.daemon_threads = True
    return httpd


def serve(host: str = "127.0.0.1", port: int = 8421, verbose: bool = False) -> None:
    httpd = make_server(host, port, verbose)
    url = f"http://{host}:{httpd.server_address[1]}/"
    print("4D tic-tac-toe is running.", flush=True)
    print(f"Open {url} in your browser. Press Ctrl+C to stop.", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        httpd.server_close()
