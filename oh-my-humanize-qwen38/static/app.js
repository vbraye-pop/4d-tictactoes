"use strict";

const N_CELLS = 81;
const AI_PLAYER = 1;
const PLAYER_MARK = ["X", "O"];

let state = null;
let view = { w: 1 };
let pollTimer = null;
let prevLastMove = null;
let inFlight = false;

const $ = (sel) => document.querySelector(sel);
const cellsEls = Array.from(document.querySelectorAll(".cell"));
const tabEls = Array.from(document.querySelectorAll(".w-tab"));
const chipEls = Array.from(document.querySelectorAll(".chip"));

function cellIndex(x, y, z, w) {
  return x + 3 * y + 9 * z + 27 * w;
}

function coordText(i) {
  const x = i % 3;
  const y = Math.floor(i / 3) % 3;
  const z = Math.floor(i / 9) % 3;
  const w = Math.floor(i / 27);
  return `(${x}, ${y}, ${z}, ${w})`;
}

async function fetchState() {
  const res = await fetch("/api/state");
  if (!res.ok) throw new Error("state request failed");
  return res.json();
}

async function refresh() {
  try {
    state = await fetchState();
    renderState(state);
  } catch (err) {
    console.error(err);
    stopPoll();
    return;
  }
  if (state.ai_pending) schedulePoll();
  else stopPoll();
}
function schedulePoll() {
  if (!pollTimer) pollTimer = setInterval(refresh, 450);
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function renderState(s) {
  const over = s.winner !== null || s.draw;
  document.body.dataset.turn = String(s.to_move);
  document.body.dataset.over = over ? "true" : "false";
  document.body.dataset.aiThinking = s.ai_pending ? "true" : "false";
  document.body.classList.toggle("winner-x", over && s.winner === 0);
  document.body.classList.toggle("winner-o", over && s.winner === 1);

  renderBadge(s, over);
  renderCells(s);
  renderTabs(s);
  renderOverview(s);
  renderResult(s);
  renderStatus(s, over);
  renderModeButtons(s);

  $("#view-readout").innerHTML =
    `Viewing W = <b>${view.w}</b> &middot; layers Z 0&ndash;2`;
}

function renderBadge(s, over) {
  const mark = $("#badge-mark");
  const text = $("#badge-text");
  if (over) {
    if (s.winner !== null) {
      mark.textContent = PLAYER_MARK[s.winner];
      text.textContent = "wins";
    } else {
      mark.textContent = "–";
      text.textContent = "draw";
    }
    return;
  }
  mark.textContent = PLAYER_MARK[s.to_move];
  if (s.mode === "ai" && s.to_move === AI_PLAYER) {
    text.textContent = "AI thinking…";
  } else {
    text.textContent = "to move";
  }
}

function renderCells(s) {
  const winCells = s.winning_cross ? new Set(s.winning_cross.cells) : null;
  for (const el of cellsEls) {
    const x = Number(el.dataset.x);
    const y = Number(el.dataset.y);
    const z = Number(el.dataset.z);
    const i = cellIndex(x, y, z, view.w);
    const owner = s.cells[i];
    el.dataset.cell = i;
    el.setAttribute("aria-label", `cell ${coordText(i)}`);
    let mark = el.querySelector(".mark");
    if (!mark) {
      mark = document.createElement("span");
      mark.className = "mark";
      el.appendChild(mark);
    }
    if (owner === ".") {
      mark.textContent = "";
      el.classList.remove("filled", "m-x", "m-o");
    } else {
      mark.textContent = owner;
      el.classList.add("filled");
      mark.classList.toggle("m-x", owner === "X");
      mark.classList.toggle("m-o", owner === "O");
    }
    el.classList.toggle("win", !!winCells && winCells.has(i));
    el.classList.toggle("last", i === s.last_move && !winCells?.has(i));
  }
  if (s.last_move !== null && s.last_move !== prevLastMove) {
    const el = cellsEls.find((e) => Number(e.dataset.cell) === s.last_move);
    if (el && view.w === Math.floor(s.last_move / 27)) {
      el.querySelector(".mark").classList.add("pop");
    }
  }
  prevLastMove = s.last_move;
}

function renderTabs(s) {
  const counts = s.winning_cross ? s.winning_cross.slice_counts : null;
  for (const el of tabEls) {
    const w = Number(el.dataset.w);
    el.classList.toggle("active", w === view.w);
    const dot = el.querySelector(".tab-dot");
    dot.hidden = !(counts && counts[String(w)] > 0);
  }
}

function renderOverview(s) {
  for (const el of chipEls) {
    const w = Number(el.dataset.w);
    const c = s.slice_counts[String(w)];
    el.querySelector(".chip-nums").innerHTML =
      `<span class="nx">X ${c.X}</span> &middot; ` +
      `<span class="no">O ${c.O}</span> &middot; <span class="nf">${c.free} free</span>`;
  }
}

function renderResult(s) {
  const panel = $("#result-panel");
  const title = $("#result-title");
  const cross = $("#result-cross");
  const note = $("#result-note");
  const over = s.winner !== null || s.draw;
  if (!over) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.classList.toggle("draw-result", s.draw);
  if (s.draw) {
    title.textContent = "Draw";
    title.className = "result-title";
    cross.hidden = true;
    note.hidden = false;
    note.textContent = "All 81 cells are filled and no cross has been formed.";
    return;
  }
  const p = PLAYER_MARK[s.winner];
  title.textContent = `${p} wins on move ${s.move_count}`;
  title.className = "result-title " + (s.winner === 0 ? "t-x" : "t-o");
  const wc = s.winning_cross;
  cross.hidden = !wc;
  if (!wc) return;
  $("#cross-center").innerHTML =
    `center <b>${coordText(wc.center)}</b>`;
  fillLine($("#cross-line-1"), wc.lines[0], wc.line_labels[0]);
  fillLine($("#cross-line-2"), wc.lines[1], wc.line_labels[1]);
  const parts = [];
  for (const w of [0, 1, 2]) {
    const n = wc.slice_counts[String(w)];
    if (n > 0) parts.push(`${n} in W=${w}`);
  }
  $("#cross-slices").textContent =
    `cross cells: ${parts.join(" · ")}` +
    (parts.length > 1 ? " — switch W tabs to see every highlighted cell." : "");
  note.hidden = true;
}

function fillLine(el, line, label) {
  el.innerHTML =
    `<span class="coords">${coordText(line[0])} &ndash; ${coordText(line[1])} &ndash; ${coordText(line[2])}</span>` +
    `<span class="label">${label}</span>`;
}

function renderStatus(s, over) {
  const el = $("#status-line");
  if (over) {
    if (s.winner !== null) el.textContent = `Game over. ${PLAYER_MARK[s.winner]} completed a winning cross.`;
    else el.textContent = "Game over. Draw.";
    return;
  }
  if (s.mode === "ai") {
    if (s.to_move === AI_PLAYER) el.textContent = "AI is thinking…";
    else el.textContent = `You are ${PLAYER_MARK[0]}. Place your mark.`;
  } else {
    el.textContent = `${PLAYER_MARK[s.to_move]}'s turn. Click any empty cell.`;
  }
}

function renderModeButtons(s) {
  $("#mode-pvp").classList.toggle("active", s.mode === "pvp");
  $("#mode-ai").classList.toggle("active", s.mode === "ai");
}

async function onCellClick(el) {
  if (!state || inFlight) return;
  if (state.winner !== null || state.draw) return;
  if (state.ai_pending) return;
  if (state.mode === "ai" && state.to_move === AI_PLAYER) return;
  const i = Number(el.dataset.cell);
  if (state.cells[i] !== ".") return;
  inFlight = true;
  try {
    const res = await fetch("/api/move", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cell: i }),
    });
    if (res.ok) {
      state = await res.json();
      renderState(state);
      if (state.ai_pending) schedulePoll();
    }
  } catch (err) {
    console.error(err);
  } finally {
    inFlight = false;
  }
}

async function startGame(mode) {
  if (inFlight) return;
  inFlight = true;
  try {
    const res = await fetch("/api/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) return;
    state = await res.json();
    prevLastMove = null;
    renderState(state);
    stopPoll();
  } catch (err) {
    console.error(err);
  } finally {
    inFlight = false;
  }
}

// Events
for (const el of cellsEls) {
  el.addEventListener("click", () => onCellClick(el));
  el.addEventListener("mouseenter", () => {
    if (el.dataset.cell !== undefined) {
      $("#coord-readout").textContent = `cell ${coordText(Number(el.dataset.cell))}`;
    }
  });
}
document.getElementById("layers").addEventListener("mouseleave", () => {
  $("#coord-readout").textContent = "cell (x, y, z, w)";
});
for (const el of tabEls) {
  el.addEventListener("click", () => {
    view.w = Number(el.dataset.w);
    if (state) renderState(state);
  });
}
$("#mode-pvp").addEventListener("click", () => startGame("pvp"));
$("#mode-ai").addEventListener("click", () => startGame("ai"));

refresh();
