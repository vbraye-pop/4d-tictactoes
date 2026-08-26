"""HTTP server for 4D tic-tac-toe. Serves static files and a JSON API."""

import json
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import game as game_logic

PORT = 8420
STATIC_ROOT = Path(__file__).resolve().parent / "static"

CONTENT_TYPES = {
    ".html": "text/html",
    ".css": "text/css",
    ".js": "text/javascript",
    ".svg": "image/svg+xml",
    ".json": "application/json",
}


class Session:
    def __init__(self, mode, human_player):
        self.mode = mode  # "human" or "ai"
        self.human_player = human_player  # player's symbol in ai mode
        self.game = game_logic.Game()

    def ai_turn(self):
        if self.mode != "ai":
            return False
        return self.game.turn != self.human_player


SESSIONS = {}


def serialize(session):
    g = session.game
    return {
        "board": g.board,
        "turn": g.turn,
        "winner": g.winner,
        "win_cross": g.win_cross,
        "mode": session.mode,
        "human_player": session.human_player,
    }


def handle_new(payload):
    mode = payload.get("mode", "ai")
    human_player = payload.get("human_player", "X")
    if mode not in ("human", "ai") or human_player not in ("X", "O"):
        return 400, {"error": "invalid mode or human_player"}
    sid = uuid.uuid4().hex
    SESSIONS[sid] = Session(mode, human_player)
    # in AI mode, if human picked O, machine (X) opens immediately
    session = SESSIONS[sid]
    if session.ai_turn():
        idx = game_logic.ai_move(session.game)
        session.game.move(idx)
        out = serialize(session)
        out["ai_cell"] = idx
    else:
        out = serialize(session)
    out["session"] = sid
    return 200, out


def handle_move(payload):
    sid = payload.get("session")
    cell = payload.get("cell")
    session = SESSIONS.get(sid)
    if session is None:
        return 404, {"error": "unknown session"}
    if not isinstance(cell, int) or not (0 <= cell < game_logic.N_CELLS):
        return 400, {"error": "invalid cell"}
    if session.mode == "ai" and session.game.turn != session.human_player:
        return 400, {"error": "not your turn"}
    ok = session.game.move(cell)
    if not ok:
        return 400, {"error": "illegal move"}
    out = serialize(session)
    out["ok"] = True
    return 200, out


def handle_ai_move(payload):
    sid = payload.get("session")
    session = SESSIONS.get(sid)
    if session is None:
        return 404, {"error": "unknown session"}
    if session.mode != "ai":
        return 400, {"error": "not in AI mode"}
    if session.game.winner is not None:
        return 400, {"error": "game over"}
    if session.game.turn == session.human_player:
        return 400, {"error": "human turn pending"}
    idx = game_logic.ai_move(session.game)
    session.game.move(idx)
    out = serialize(session)
    out["ai_cell"] = idx
    return 200, out


ROUTES = {
    "/api/new": handle_new,
    "/api/move": handle_move,
    "/api/ai_move": handle_ai_move,
}


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        target = (STATIC_ROOT / path.lstrip("/")).resolve()
        if not str(target).startswith(str(STATIC_ROOT)) or not target.is_file():
            self.send_error(404)
            return
        ctype = CONTENT_TYPES.get(target.suffix, "application/octet-stream")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._serve_static(self.path)

    def do_POST(self):
        route = self.path.split("?", 1)[0]
        handler = ROUTES.get(route)
        if handler is None:
            self._json(404, {"error": "unknown route"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (json.JSONDecodeError, ValueError):
            self._json(400, {"error": "bad json"})
            return
        status, body = handler(payload)
        self._json(status, body)

    def log_message(self, *args):
        pass


def main():
    print(f"4D tic-tac-toe ready at http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
