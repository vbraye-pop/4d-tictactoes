/* 4D tic-tac-toe client. Cell index encoding matches game.py:
   index = x + 3*(y + 3*(z + 3*w)); x fastest. */

const SIZE = 3;
const AI_DELAY_MS = 650;

let sessionId = null;
let state = null; // serialized game from server

const boardEl = document.getElementById("board");
const statusText = document.getElementById("status-text");
const cursorReadout = document.getElementById("cursor-readout");
const moveLog = document.getElementById("move-log");
const modeSelect = document.getElementById("mode-select");
const sideSelect = document.getElementById("side-select");

function toCoords(idx) {
  const coords = [];
  for (let i = 0; i < 4; i++) {
    coords.push(idx % SIZE);
    idx = Math.floor(idx / SIZE);
  }
  return coords;
}

/* Build the plane-based board: outer grid (w,z), inner (y,x). */
function buildBoard() {
  boardEl.innerHTML = "";
  for (let w = 0; w < SIZE; w++) {
    for (let z = 0; z < SIZE; z++) {
      const plane = document.createElement("div");
      plane.className = "plane";
      const label = document.createElement("span");
      label.className = "plane-label";
      label.textContent = `w=${w} z=${z}`;
      plane.appendChild(label);
      const grid = document.createElement("div");
      grid.className = "plane-grid";
      for (let y = 0; y < SIZE; y++) {
        for (let x = 0; x < SIZE; x++) {
          const idx = x + SIZE * (y + SIZE * (z + SIZE * w));
          const cell = document.createElement("button");
          cell.className = "cell empty";
          cell.dataset.idx = idx;
          const [cx, cy, cz, cw] = [x, y, z, w];
          cell.title = `(x,y,z,w)=(${cx},${cy},${cz},${cw})`;
          cell.addEventListener("click", () => onCellClick(idx));
          cell.addEventListener("mouseenter", () => {
            cursorReadout.textContent = `(x,y,z,w)=(${cx},${cy},${cz},${cw})`;
          });
          grid.appendChild(cell);
        }
      }
      plane.appendChild(grid);
      boardEl.appendChild(plane);
    }
  }
}

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function startGame() {
  const mode = modeSelect.querySelector(".active").dataset.mode;
  const humanPlayer = sideSelect.value;
  const data = await api("/api/new", { mode, human_player: humanPlayer });
  sessionId = data.session;
  state = data;
  moveLog.innerHTML = "";
  render();
  // AI opened the game (human plays O)
  if (data.ai_cell !== undefined) {
    logMove(state.human_player === "X" ? "O" : "X", data.ai_cell);
  }
}

function render() {
  const { board, turn, winner, win_cross } = state;
  boardEl.classList.toggle("locked", winner !== null);

  for (const cellEl of boardEl.querySelectorAll(".cell")) {
    const idx = Number(cellEl.dataset.idx);
    const v = board[idx];
    cellEl.textContent = v || "";
    cellEl.classList.remove("x", "o", "empty", "win");
    cellEl.classList.add(v ? v.toLowerCase() : "empty");
  }
  if (winner === "draw") {
    statusText.textContent = "Draw: all 81 cells filled, no cross completed";
    statusText.className = "status-text done";
  } else if (winner) {
    statusText.textContent = `${winner} wins`;
    statusText.className = `status-text ${winner.toLowerCase()}`;
    for (const idx of win_cross) {
      const el = boardEl.querySelector(`[data-idx="${idx}"]`);
      if (el) el.classList.add("win");
    }
  } else {
    const who = state.mode === "ai" && state.human_player !== turn ? "AI" : turn;
    statusText.textContent = `${who} to move`;
    statusText.className = `status-text ${turn.toLowerCase()}`;
  }
}

function logMove(player, idx) {
  const c = toCoords(idx);
  const row = document.createElement("div");
  row.className = "move-row";
  const who = document.createElement("span");
  who.className = `who ${player.toLowerCase()}`;
  who.textContent = player;
  const coords = document.createElement("span");
  coords.className = "coords";
  coords.textContent = `(x,y,z,w)=(${c[0]},${c[1]},${c[2]},${c[3]})`;
  row.appendChild(who);
  row.appendChild(coords);
  moveLog.appendChild(row);
  moveLog.scrollTop = moveLog.scrollHeight;
}

async function onCellClick(idx) {
  if (!sessionId || state.winner) return;
  if (state.mode === "ai" && state.turn !== state.human_player) return;
  if (state.board[idx] !== null) return;
  try {
    const data = await api("/api/move", { session: sessionId, cell: idx });
    logMove(state.turn, idx);
    state = data;
    render();
    if (state.mode === "ai" && state.winner === null) {
      scheduleAiMove();
    }
  } catch (err) {
    render();
  }
}

function scheduleAiMove() {
  boardEl.classList.add("locked");
  statusText.textContent = "AI thinking…";
  statusText.className = "status-text";
  setTimeout(async () => {
    try {
      const data = await api("/api/ai_move", { session: sessionId });
      logMove(state.turn, data.ai_cell);
      state = data;
      render();
    } catch (err) {
      render();
    }
  }, AI_DELAY_MS);
}

modeSelect.addEventListener("click", (e) => {
  if (!e.target.classList.contains("seg-btn")) return;
  modeSelect.querySelectorAll(".seg-btn").forEach((b) => b.classList.remove("active"));
  e.target.classList.add("active");
  sideSelect.disabled = e.target.dataset.mode !== "ai";
  startGame();
});
sideSelect.addEventListener("change", startGame);
document.getElementById("new-game").addEventListener("click", startGame);

buildBoard();
startGame();
