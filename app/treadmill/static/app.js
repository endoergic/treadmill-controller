"use strict";

const $ = (id) => document.getElementById(id);
const BAD_PIN = 4001;
const PLACED = new Set(["speed_up", "speed_down", "start", "stop", "incline_up", "incline_down"]);
// Rainbow ribbon on HD6 (docs/hardware/button-map.md).
const WIRE = { 1: "black", 2: "white", 3: "grey", 4: "purple", 5: "blue", 6: "green", 7: "yellow", 8: "orange", 9: "red", 10: "brown" };
let ws = null;
let state = null;
let toastTimer = 0;

function toast(text) {
  $("toast").textContent = text;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ($("toast").hidden = true), 2500);
}

function online() {
  return ws && ws.readyState === WebSocket.OPEN;
}

function send(msg) {
  if (online()) ws.send(JSON.stringify(msg));
  else toast("Not connected");
}

function press(command) {
  if (navigator.vibrate) navigator.vibrate(15);
  send({ type: "press", command });
}

function label(name) {
  return name.replace(/_/g, " ");
}

function button(text, data) {
  const b = document.createElement("button");
  b.textContent = text;
  Object.assign(b.dataset, data);
  return b;
}

// Rebuild a container's buttons only when the list changes (keeps taps from landing on replaced nodes).
function fill(box, key, make) {
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  box.replaceChildren(...make());
}

function render() {
  const s = state;
  const on = online();
  $("conn").textContent = on ? "connected" : "reconnecting…";
  $("conn").className = "conn " + (on ? "on" : "off");
  if (!s) return;

  $("speed").textContent = s.speed.toFixed(1);
  $("unit").textContent = s.unit;
  $("max").textContent = `${s.max_speed} ${s.unit}`;
  $("clients").textContent = s.clients > 1 ? `${s.clients} phones` : "";
  const pending = (s.busy ? 1 : 0) + s.queued.length;
  $("busy").innerHTML = s.busy ? `pressing ${label(s.busy)}${pending > 1 ? ` (+${pending - 1})` : ""}` : "&nbsp;";

  const has = new Set(s.commands);
  for (const [id, name] of [["up", "speed_up"], ["down", "speed_down"], ["incline-up", "incline_up"], ["incline-down", "incline_down"]]) {
    $(id).hidden = !has.has(name);
  }
  $("start").hidden = !has.has("start");
  $("stop").hidden = !has.has("stop");
  $("no-stop").hidden = has.has("stop");
  $("incline-box").hidden = !has.has("incline_up") && !has.has("incline_down");

  const presets = Object.entries(s.presets).sort((a, b) => a[1] - b[1]);
  $("presets-box").hidden = presets.length === 0;
  fill($("presets"), presets.map(([n]) => n).join(), () => presets.map(([name, v]) => {
    const b = button(String(v), { command: name, speed: v });
    b.classList.add("preset");
    return b;
  }));
  for (const b of $("presets").children) b.classList.toggle("over", Number(b.dataset.speed) > s.max_speed);

  const extra = s.commands.filter((c) => !PLACED.has(c) && !(c in s.presets));
  fill($("extra"), extra.join(), () => extra.map((c) => button(label(c), { command: c })));

  for (const b of document.querySelectorAll("main button[data-command]")) {
    b.disabled = !on || (b.dataset.speed !== undefined && Number(b.dataset.speed) > s.max_speed);
  }
  renderManual();
}

// ---- troubleshooting panel ------------------------------------------------

const manual = { lines: new Set(), go: null, recent: JSON.parse(localStorage.getItem("manualRecent") || "[]") };

function renderManual() {
  const m = state && state.manual;
  if (!m || $("manual").hidden) return;
  const ground = new Set(m.ground);
  if (manual.go === null) manual.go = m.ground[0] ?? m.pins[0];
  if (!$("m-ms").value) $("m-ms").value = m.press_ms;
  $("m-ms").max = m.max_press_ms;

  const pinLabel = (p) => `${p} ${WIRE[p] || ""}${ground.has(p) ? " · GND" : ""}`;
  fill($("m-lines"), m.pins.join(), () => m.pins.filter((p) => !ground.has(p)).map((p) => button(pinLabel(p), { line: p })));
  fill($("m-go"), m.pins.join(), () => m.pins.map((p) => button(pinLabel(p), { go: p })));
  for (const b of $("m-lines").children) {
    const p = Number(b.dataset.line);
    b.classList.toggle("sel", manual.lines.has(p));
    b.disabled = p === manual.go;
  }
  for (const b of $("m-go").children) b.classList.toggle("sel", Number(b.dataset.go) === manual.go);

  const lines = [...manual.lines].sort((a, b) => a - b);
  const tooMany = lines.length + 1 > m.max_relays_on;
  $("m-summary").textContent = `Lines ${lines.join(" + ") || "none"}, then Go on ${manual.go} for ${$("m-ms").value} ms` +
    (tooMany ? ` · too many relays (max ${m.max_relays_on})` : "");
  $("m-press").disabled = !online() || tooMany;

  fill($("m-recent"), JSON.stringify(manual.recent), () => manual.recent.map((r, i) =>
    button(`${r.select.join("+") || "none"} → Go ${r.go} · ${r.press_ms} ms`, { recent: i })));
}

function openManual(open) {
  $("manual").hidden = !open;
  document.body.classList.toggle("noscroll", open);
  if (open) renderManual();
  if (!open && location.hash === "#manual") history.replaceState(null, "", location.pathname);
}

function pressManual() {
  const msg = { type: "manual", select: [...manual.lines].sort((a, b) => a - b), go: manual.go, press_ms: Number($("m-ms").value) };
  if (navigator.vibrate) navigator.vibrate(15);
  send(msg);
  const key = JSON.stringify([msg.select, msg.go, msg.press_ms]);
  manual.recent = [msg, ...manual.recent.filter((r) => JSON.stringify([r.select, r.go, r.press_ms]) !== key)].slice(0, 8);
  localStorage.setItem("manualRecent", JSON.stringify(manual.recent));
  renderManual();
}

$("manual").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (!b || b.disabled) return;
  if (b.dataset.line) {
    const p = Number(b.dataset.line);
    manual.lines.has(p) ? manual.lines.delete(p) : manual.lines.add(p);
  } else if (b.dataset.go) {
    manual.go = Number(b.dataset.go);
    manual.lines.delete(manual.go);
  } else if (b.dataset.ms) {
    $("m-ms").value = b.dataset.ms;
  } else if (b.dataset.recent) {
    const r = manual.recent[Number(b.dataset.recent)];
    manual.lines = new Set(r.select);
    manual.go = r.go;
    $("m-ms").value = r.press_ms;
  } else if (b.id === "m-press") {
    pressManual();
    return;
  } else if (b.id === "manual-close") {
    openManual(false);
    return;
  }
  renderManual();
});
$("m-ms").addEventListener("input", renderManual);

// Secret door: tap the connection status 5 times within 3 s.
let taps = [];
$("conn").addEventListener("click", () => {
  const now = Date.now();
  taps = [...taps.filter((t) => now - t < 3000), now];
  if (taps.length >= 5) { taps = []; openManual(true); }
});

// ---- connection -----------------------------------------------------------

function connect() {
  const pin = localStorage.getItem("pin") || "";
  const proto = location.protocol === "https:" ? "wss" : "ws";
  ws = new WebSocket(`${proto}://${location.host}/ws?pin=${encodeURIComponent(pin)}`);
  ws.onopen = render;
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.type === "state") { state = msg; render(); }
    else if (msg.type === "error") toast(msg.message);
  };
  ws.onclose = (e) => {
    render();
    if (e.code === BAD_PIN) {
      const entered = prompt(pin ? "Wrong PIN. Try again:" : "PIN:");
      if (entered === null) return;
      localStorage.setItem("pin", entered);
      connect();
      return;
    }
    setTimeout(connect, 1000);
  };
}

document.querySelector("main").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-command]");
  if (b && !b.disabled) press(b.dataset.command);
});
$("reset").addEventListener("click", () => {
  if (confirm("Only do this when the belt has actually stopped. Set estimated speed to 0?")) send({ type: "reset" });
});

if (location.hash === "#manual") openManual(true);
window.addEventListener("hashchange", () => openManual(location.hash === "#manual"));
connect();
