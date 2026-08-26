"""The JSON API the browser talks to."""

import json
import threading
import unittest
import urllib.error
import urllib.request

from fourd.crosses import RULES_4D
from fourd.server import make_server


def build_toward_a_cross(cells):
    """A human move that extends the most advanced cross the computer has not touched."""
    mine = {i for i, owner in enumerate(cells) if owner == "X"}
    theirs = {i for i, owner in enumerate(cells) if owner == "O"}
    best_count, best_cell = -1, None
    for cross in RULES_4D.cross_cells:
        if theirs.intersection(cross):
            continue
        free = [cell for cell in cross if cell not in mine]
        if not free:
            continue
        count = 5 - len(free)
        if count > best_count:
            best_count, best_cell = count, free[0]
    return best_cell


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = make_server("127.0.0.1", 0)
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, payload=None):
        url = self.base + path
        if payload is None:
            request = urllib.request.Request(url)
        else:
            request = urllib.request.Request(
                url, data=json.dumps(payload).encode(), method="POST",
                headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            with error:
                body = error.read()
            try:
                return error.code, json.loads(body)
            except json.JSONDecodeError:
                return error.code, {}

    def test_serves_the_page_and_its_assets(self):
        for path in ("/", "/style.css", "/app.js"):
            with urllib.request.urlopen(self.base + path, timeout=30) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())

    def test_rejects_paths_outside_the_web_directory(self):
        for path in ("/../fourd/ai.py", "/%2e%2e/fourd/ai.py", "/../../etc/hosts"):
            status, _ = self.request(path)
            self.assertEqual(status, 404, path)

    def test_new_game_starts_empty(self):
        status, state = self.request("/api/new", {"mode": "hvh"})
        self.assertEqual(status, 200)
        self.assertEqual(state["cells"], [None] * RULES_4D.cell_count)
        self.assertEqual(state["toMove"], "X")
        self.assertEqual(state["status"], "ongoing")
        self.assertFalse(state["aiToMove"])

    def test_moves_alternate_and_are_recorded(self):
        _, state = self.request("/api/new", {"mode": "hvh"})
        _, state = self.request("/api/move", {"id": state["id"], "cell": 40})
        self.assertEqual(state["cells"][40], "X")
        self.assertEqual(state["toMove"], "O")
        self.assertEqual(state["lastMove"], 40)
        _, state = self.request("/api/move", {"id": state["id"], "cell": 0})
        self.assertEqual(state["cells"][0], "O")
        self.assertEqual(state["moveCount"], 2)

    def test_replaying_an_occupied_cell_is_rejected(self):
        _, state = self.request("/api/new", {"mode": "hvh"})
        self.request("/api/move", {"id": state["id"], "cell": 40})
        status, body = self.request("/api/move", {"id": state["id"], "cell": 40})
        self.assertEqual(status, 409)
        self.assertEqual(body["state"]["moveCount"], 1)

    def test_a_win_is_reported_with_its_cross(self):
        _, state = self.request("/api/new", {"mode": "hvh"})
        for cell in (40, 0, 13, 1, 67, 2, 4, 3, 76):
            _, state = self.request("/api/move", {"id": state["id"], "cell": cell})
        self.assertEqual(state["status"], "win")
        self.assertEqual(state["winner"], "X")
        self.assertEqual(sorted(state["winningCross"]), [4, 13, 40, 67, 76])
        status, _ = self.request("/api/move", {"id": state["id"], "cell": 5})
        self.assertEqual(status, 409)

    def test_the_computer_answers_in_ai_mode(self):
        _, state = self.request("/api/new", {"mode": "hva", "aiSide": "O"})
        _, state = self.request("/api/move", {"id": state["id"], "cell": 40})
        self.assertTrue(state["aiToMove"])
        _, state = self.request("/api/ai", {"id": state["id"]})
        self.assertEqual(state["moveCount"], 2)
        self.assertEqual(state["toMove"], "X")
        self.assertIsNotNone(state["lastAi"])
        self.assertIn(state["lastAi"]["reason"], ("win", "block", "solved", "search"))

    def test_the_computer_blocks_an_imminent_human_win(self):
        _, state = self.request("/api/new", {"mode": "hva", "aiSide": "O"})
        blocked = False
        for _ in range(25):
            _, state = self.request(
                "/api/move", {"id": state["id"], "cell": build_toward_a_cross(state["cells"])})
            if state["status"] != "ongoing":
                break
            threats = state["threats"]["X"]
            computer_can_win = state["threats"]["O"]
            _, state = self.request("/api/ai", {"id": state["id"]})
            if threats and not computer_can_win:
                self.assertEqual(state["lastAi"]["reason"], "block")
                self.assertEqual(state["cells"][threats[0]], "O")
                blocked = True
                break
            if state["status"] != "ongoing":
                break
        self.assertTrue(blocked, "the human never managed to threaten a cross")

    def test_the_computer_takes_a_win_that_is_available(self):
        _, state = self.request("/api/new", {"mode": "hva", "aiSide": "O"})
        while state["status"] == "ongoing":
            if state["aiToMove"]:
                _, state = self.request("/api/ai", {"id": state["id"]})
            else:
                cell = next(i for i, owner in enumerate(state["cells"]) if owner is None)
                _, state = self.request("/api/move", {"id": state["id"], "cell": cell})
        self.assertEqual(state["status"], "win")
        self.assertEqual(state["winner"], "O")
        self.assertEqual(state["lastAi"]["reason"], "win")
        self.assertEqual(state["cells"][state["lastAi"]["cell"]], "O")
        self.assertIn(state["lastAi"]["cell"], state["winningCross"])

    def test_the_history_is_reported_for_reloads(self):
        _, state = self.request("/api/new", {"mode": "hvh"})
        for cell in (40, 0, 13):
            _, state = self.request("/api/move", {"id": state["id"], "cell": cell})
        _, again = self.request(f"/api/state?id={state['id']}")
        self.assertEqual(again["history"], [["X", 40], ["O", 0], ["X", 13]])

    def test_a_human_cannot_move_for_the_computer(self):
        _, state = self.request("/api/new", {"mode": "hva", "aiSide": "O"})
        _, state = self.request("/api/move", {"id": state["id"], "cell": 40})
        status, _ = self.request("/api/move", {"id": state["id"], "cell": 41})
        self.assertEqual(status, 409)

    def test_the_computer_can_take_the_first_move(self):
        _, state = self.request("/api/new", {"mode": "hva", "aiSide": "X"})
        self.assertTrue(state["aiToMove"])
        _, state = self.request("/api/ai", {"id": state["id"]})
        self.assertEqual(state["moveCount"], 1)
        self.assertEqual(state["toMove"], "O")

    def test_unknown_games_and_bad_payloads_are_reported(self):
        status, _ = self.request("/api/state?id=nope")
        self.assertEqual(status, 404)
        status, _ = self.request("/api/move", {"id": "nope", "cell": 0})
        self.assertEqual(status, 404)
        _, state = self.request("/api/new", {"mode": "hvh"})
        status, _ = self.request("/api/move", {"id": state["id"], "cell": "middle"})
        self.assertEqual(status, 400)
        status, _ = self.request("/api/new", {"mode": "chess"})
        self.assertEqual(status, 400)

    def test_state_can_be_fetched_again(self):
        _, state = self.request("/api/new", {"mode": "hvh"})
        self.request("/api/move", {"id": state["id"], "cell": 40})
        status, again = self.request(f"/api/state?id={state['id']}")
        self.assertEqual(status, 200)
        self.assertEqual(again["cells"][40], "X")


if __name__ == "__main__":
    unittest.main()
