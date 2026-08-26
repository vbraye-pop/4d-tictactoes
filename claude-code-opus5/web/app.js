"use strict";

const AXES = ["x", "y", "z", "w"];
const MIN_AI_DELAY = 480;
const STORAGE_KEY = "fourd-game-id";

const el = {
  board: document.getElementById("board"),
  overlay: document.getElementById("cross-overlay"),
  veil: document.getElementById("board-veil"),
  turnMark: document.getElementById("turn-mark"),
  turnLabel: document.getElementById("turn-label"),
  turnNote: document.getElementById("turn-note"),
  moveCount: document.getElementById("move-count"),
  emptyCount: document.getElementById("empty-count"),
  coords: document.getElementById("coords"),
  cursorContext: document.getElementById("cursor-context"),
  resultCard: document.getElementById("result-card"),
  resultTitle: document.getElementById("result-title"),
  resultBody: document.getElementById("result-body"),
  crossList: document.getElementById("cross-list"),
  resultNew: document.getElementById("result-new"),
  log: document.getElementById("log"),
  modeSelect: document.getElementById("mode-select"),
  sideSelect: document.getElementById("side-select"),
  sideGroup: document.getElementById("side-group"),
  newGame: document.getElementById("new-game"),
  threatToggle: document.getElementById("threat-toggle"),
};

const cellButtons = [];
const ui = {
  state: null,
  cursor: [1, 1, 1, 1],
  hover: null,
  mode: "hvh",
  humanSide: "X",
  busy: false,
  log: [],
};

const index = (c) => c[0] * 27 + c[1] * 9 + c[2] * 3 + c[3];
const coordsOf = (i) => [Math.floor(i / 27), Math.floor(i / 9) % 3, Math.floor(i / 3) % 3, i % 3];
const label = (c) => `x${c[0]} y${c[1]} z${c[2]} w${c[3]}`;

/* ---------- board construction ---------- */

function buildBoard() {
  const fragment = document.createDocumentFragment();
  for (let x = 0; x < 3; x++) {
    for (let y = 0; y < 3; y++) {
      const sub = document.createElement("div");
      sub.className = "subboard";
      sub.dataset.x = x;
      sub.dataset.y = y;

      const head = document.createElement("div");
      head.className = "subboard-label";
      head.innerHTML = `<span>x<b>${x}</b> y<b>${y}</b></span><span>z&darr; w&rarr;</span>`;
      sub.appendChild(head);

      const grid = document.createElement("div");
      grid.className = "subgrid";
      for (let z = 0; z < 3; z++) {
        for (let w = 0; w < 3; w++) {
          const cell = document.createElement("button");
          const i = index([x, y, z, w]);
          cell.type = "button";
          cell.className = "cell";
          cell.dataset.cell = i;
          cell.setAttribute("aria-label", `Cell ${label([x, y, z, w])}, empty`);
          cell.addEventListener("click", () => onCellClick(i));
          cell.addEventListener("mouseenter", () => { ui.hover = i; paintCursor(); });
          cell.addEventListener("mouseleave", () => { ui.hover = null; paintCursor(); });
          cellButtons[i] = cell;
          grid.appendChild(cell);
        }
      }
      sub.appendChild(grid);
      fragment.appendChild(sub);
    }
  }
  el.board.appendChild(fragment);
}

/* ---------- server calls ---------- */

async function api(path, body) {
  const options = body === undefined
    ? { method: "GET" }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.error || `request failed (${response.status})`);
    error.status = response.status;
    error.state = data.state;
    throw error;
  }
  return data;
}

async function newGame() {
  ui.log = [];
  const state = await api("/api/new", { mode: ui.mode, aiSide: ui.humanSide === "X" ? "O" : "X" });
  localStorage.setItem(STORAGE_KEY, state.id);
  ui.state = state;
  ui.cursor = [1, 1, 1, 1];
  render();
  maybeAiMove();
}

async function onCellClick(cell) {
  const state = ui.state;
  if (!state || ui.busy || state.status !== "ongoing" || state.aiToMove) return;
  if (state.cells[cell] !== null) return;
  ui.cursor = coordsOf(cell);
  ui.busy = true;
  try {
    const player = state.toMove;
    const next = await api("/api/move", { id: state.id, cell });
    pushLog(player, cell, "");
    ui.state = next;
    render();
  } catch (error) {
    if (error.state) { ui.state = error.state; render(); }
  } finally {
    ui.busy = false;
  }
  maybeAiMove();
}

async function maybeAiMove() {
  const state = ui.state;
  if (!state || !state.aiToMove || ui.busy) return;
  ui.busy = true;
  setVeil(true, "Computer is thinking…");
  const started = performance.now();
  try {
    const next = await api("/api/ai", { id: state.id });
    const wait = MIN_AI_DELAY - (performance.now() - started);
    if (wait > 0) await new Promise((resolve) => setTimeout(resolve, wait));
    if (next.lastAi) pushLog(state.toMove, next.lastAi.cell, next.lastAi.detail);
    ui.state = next;
    setVeil(false);
    render();
  } catch (error) {
    setVeil(false);
    if (error.state) { ui.state = error.state; render(); }
  } finally {
    ui.busy = false;
  }
}

function pushLog(player, cell, note) {
  ui.log.push({ player, cell, note, n: ui.log.length + 1 });
}

/* ---------- rendering ---------- */

function render() {
  const state = ui.state;
  if (!state) return;
  const finished = state.status !== "ongoing";
  const winners = new Set(state.winningCross || []);

  for (let i = 0; i < 81; i++) {
    const cell = cellButtons[i];
    const owner = state.cells[i];
    cell.className = "cell";
    cell.textContent = owner || "";
    if (owner) cell.classList.add("taken", owner.toLowerCase());
    if (i === state.lastMove) cell.classList.add("last");
    if (winners.has(i)) cell.classList.add("win");
    cell.disabled = finished || owner !== null || state.aiToMove;
    cell.setAttribute("aria-label",
      `Cell ${label(coordsOf(i))}, ${owner ? owner : "empty"}`);
  }

  if (el.threatToggle.checked && !finished && state.threats) {
    for (const cell of state.threats[state.toMove] || []) {
      cellButtons[cell].classList.add("threat");
    }
  }

  el.board.classList.toggle("locked", finished);
  paintCursor();
  renderStatus();
  renderLog();
  renderResult();
  drawCross();
}

function renderStatus() {
  const state = ui.state;
  const finished = state.status !== "ongoing";
  const chip = el.turnMark;
  chip.className = "mark-chip";

  if (state.status === "win") {
    chip.classList.add("done");
    chip.textContent = state.winner;
    el.turnLabel.textContent = `${state.winner} wins`;
    el.turnNote.textContent = "The board is locked. Start a new game to play again.";
  } else if (state.status === "draw") {
    chip.classList.add("done");
    chip.textContent = "=";
    el.turnLabel.textContent = "Draw";
    el.turnNote.textContent = "All 81 cells are filled with no cross.";
  } else {
    chip.classList.add(state.toMove.toLowerCase());
    chip.textContent = state.toMove;
    const isAi = state.mode === "hva" && state.toMove === state.aiSide;
    el.turnLabel.textContent = isAi ? `${state.toMove} to move (computer)` : `${state.toMove} to move`;
    el.turnNote.textContent = isAi
      ? "The computer is choosing a cell."
      : (state.mode === "hva" ? "Your turn. Click any free cell." : "Click any free cell.");
  }

  const filled = state.moveCount;
  el.moveCount.textContent = `Move ${filled}`;
  el.emptyCount.textContent = `${81 - filled} cell${81 - filled === 1 ? "" : "s"} free`;

  const note = state.lastAi;
  if (note && !finished) {
    el.turnNote.textContent =
      `Computer played ${label(coordsOf(note.cell))} — ${note.detail}.`;
  } else if (note && state.status === "win") {
    el.turnNote.textContent =
      `The board is locked. Computer's last move: ${label(coordsOf(note.cell))}.`;
  }
}

function paintCursor() {
  const focus = ui.hover !== null ? ui.hover : index(ui.cursor);
  const coords = coordsOf(focus);

  for (const cell of cellButtons) cell.classList.remove("cursor", "neighbour");
  for (const sub of el.board.children) sub.classList.remove("cursor-board");

  cellButtons[focus].classList.add("cursor");
  el.board.children[coords[0] * 3 + coords[1]].classList.add("cursor-board");

  for (let axis = 0; axis < 4; axis++) {
    for (const step of [-1, 1]) {
      const next = coords.slice();
      next[axis] += step;
      if (next[axis] < 0 || next[axis] > 2) continue;
      cellButtons[index(next)].classList.add("neighbour");
    }
  }

  el.coords.innerHTML = AXES.map((axis, i) =>
    `<div class="coord"><span class="axis">${axis}</span><span class="value">${coords[i]}</span></div>`
  ).join("");

  const owner = ui.state ? ui.state.cells[focus] : null;
  el.cursorContext.innerHTML =
    `Board <b>x${coords[0]} y${coords[1]}</b>, cell <b>z${coords[2]} w${coords[3]}</b> ` +
    `&mdash; ${owner ? `held by ${owner}` : "free"}`;
}

function renderLog() {
  if (!ui.log.length) {
    el.log.innerHTML = `<li class="log-empty">No moves yet.</li>`;
    return;
  }
  el.log.innerHTML = ui.log.slice().reverse().map((entry) =>
    `<li><span class="who ${entry.player.toLowerCase()}">${entry.player}</span>` +
    `<span>${label(coordsOf(entry.cell))}</span>` +
    `<span class="note">${entry.note || ""}</span></li>`
  ).join("");
}

function renderResult() {
  const state = ui.state;
  if (state.status === "ongoing") {
    el.resultCard.hidden = true;
    return;
  }
  el.resultCard.hidden = false;
  if (state.status === "draw") {
    el.resultTitle.textContent = "Draw";
    el.resultBody.textContent = "All 81 cells are filled and no cross was completed.";
    el.crossList.innerHTML = "";
    return;
  }
  el.resultTitle.textContent = "Winner";
  const isAi = state.mode === "hva" && state.winner === state.aiSide;
  el.resultBody.textContent = state.mode === "hva"
    ? (isAi ? `${state.winner} wins — the computer completed a cross.`
            : `${state.winner} wins — you completed a cross.`)
    : `${state.winner} completed a cross.`;

  const cross = state.winningCross || [];
  const centre = crossCentre(cross);
  el.crossList.innerHTML = cross.map((cell) => {
    const tag = cell === centre ? "<b>centre</b>" : "arm";
    return `<li><span>${label(coordsOf(cell))}</span>${tag}</li>`;
  }).join("") + crossSpanNote(cross, centre);
}

function armName(delta) {
  const axes = delta.map((d, i) => (d ? AXES[i] : "")).filter(Boolean);
  if (axes.length === 1) return `along ${axes[0]}`;
  const signs = delta.filter(Boolean);
  const joined = axes.map((axis, i) => (i === 0 ? axis : (signs[i] === signs[0] ? `+${axis}` : `-${axis}`)))
    .join("");
  return `${joined} diagonal`;
}

function crossArms(cross, centre) {
  const centreCoords = coordsOf(centre);
  const seen = new Set();
  const arms = [];
  for (const cell of cross) {
    if (cell === centre) continue;
    const delta = coordsOf(cell).map((v, i) => v - centreCoords[i]);
    const key = delta.map(Math.abs).join(",");
    if (seen.has(key)) continue;
    seen.add(key);
    arms.push({ cell, delta, opposite: index(centreCoords.map((v, i) => v - delta[i])) });
  }
  return arms;
}

function crossSpanNote(cross, centre) {
  if (centre === null) return "";
  const names = crossArms(cross, centre).map((arm) => armName(arm.delta));
  return `<li><span>two lines</span><b>${names.join(" &amp; ")}</b></li>`;
}

function crossCentre(cross) {
  // The centre is the cell whose four partners come in opposite pairs around it.
  const coords = cross.map(coordsOf);
  for (let i = 0; i < cross.length; i++) {
    const deltas = coords
      .filter((_, j) => j !== i)
      .map((c) => c.map((v, k) => v - coords[i][k]).join(","));
    const paired = deltas.every((d) => deltas.includes(d.split(",").map((v) => -Number(v)).join(",")));
    if (paired) return cross[i];
  }
  return cross[2];
}

function drawCross() {
  const state = ui.state;
  el.overlay.innerHTML = "";
  if (!state || !state.winningCross) return;

  const cross = state.winningCross;
  const centre = crossCentre(cross);
  const frame = el.board.getBoundingClientRect();
  el.overlay.setAttribute("viewBox", `0 0 ${frame.width} ${frame.height}`);

  const point = (cell) => {
    const box = cellButtons[cell].getBoundingClientRect();
    return [box.left - frame.left + box.width / 2, box.top - frame.top + box.height / 2];
  };

  const arms = crossArms(cross, centre).map((arm) => [arm.cell, centre, arm.opposite]);

  const svgNs = "http://www.w3.org/2000/svg";
  for (const arm of arms) {
    const points = arm.map(point).map((p) => p.join(",")).join(" ");
    for (const [width, opacity] of [[11, 0.18], [3.5, 0.9]]) {
      const line = document.createElementNS(svgNs, "polyline");
      line.setAttribute("points", points);
      line.setAttribute("fill", "none");
      line.setAttribute("stroke", "#64e39a");
      line.setAttribute("stroke-width", width);
      line.setAttribute("stroke-opacity", opacity);
      line.setAttribute("stroke-linecap", "round");
      line.setAttribute("stroke-linejoin", "round");
      el.overlay.appendChild(line);
    }
  }
}

function setVeil(on, text) {
  el.veil.classList.toggle("on", !!on);
  el.veil.innerHTML = on ? `<span>${text}</span>` : "";
}

/* ---------- input ---------- */

function onKey(event) {
  const map = { ArrowUp: [2, -1], ArrowDown: [2, 1], ArrowLeft: [3, -1], ArrowRight: [3, 1] };
  const outer = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [1, -1], ArrowRight: [1, 1] };
  const move = event.shiftKey ? outer[event.key] : map[event.key];
  if (move) {
    event.preventDefault();
    const next = ui.cursor.slice();
    next[move[0]] = (next[move[0]] + move[1] + 3) % 3;
    ui.cursor = next;
    ui.hover = null;
    paintCursor();
    return;
  }
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    onCellClick(index(ui.cursor));
  }
}

function bindControls() {
  el.modeSelect.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-mode]");
    if (!button) return;
    ui.mode = button.dataset.mode;
    for (const other of el.modeSelect.children) other.classList.toggle("active", other === button);
    el.sideGroup.hidden = ui.mode !== "hva";
    newGame();
  });

  el.sideSelect.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-side]");
    if (!button) return;
    ui.humanSide = button.dataset.side;
    for (const other of el.sideSelect.children) other.classList.toggle("active", other === button);
    newGame();
  });

  el.newGame.addEventListener("click", newGame);
  el.resultNew.addEventListener("click", newGame);
  el.threatToggle.addEventListener("change", render);
  document.addEventListener("keydown", onKey);
  window.addEventListener("resize", drawCross);
}

async function boot() {
  buildBoard();
  bindControls();
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) {
    try {
      const state = await api(`/api/state?id=${encodeURIComponent(saved)}`);
      ui.state = state;
      ui.log = (state.history || []).map(([player, cell], i) => ({ player, cell, note: "", n: i + 1 }));
      ui.mode = state.mode;
      ui.humanSide = state.aiSide === "X" ? "O" : "X";
      for (const button of el.modeSelect.children) {
        button.classList.toggle("active", button.dataset.mode === ui.mode);
      }
      el.sideGroup.hidden = ui.mode !== "hva";
      for (const button of el.sideSelect.children) {
        button.classList.toggle("active", button.dataset.side === ui.humanSide);
      }
      render();
      maybeAiMove();
      return;
    } catch (error) {
      localStorage.removeItem(STORAGE_KEY);
    }
  }
  await newGame();
}

boot();
