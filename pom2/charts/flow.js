/* Interactive drawn chart: Look / Walk / Test laid over the chart exactly as it is drawn in the
   notes (a pathway flow or a drug-class tree). D = {model: {kind, nodes, edges}} is set by the
   page; the SVG is already in #map. Built by tools/interactive_charts.py. */
(function () {
var Q = new URLSearchParams(location.search), EMBED = Q.has("embed"), ROOT = document.documentElement;
function theme(t) { if (t === "dark" || t === "light") ROOT.setAttribute("data-theme", t); }
if (EMBED) {
  ROOT.classList.add("embed"); theme(Q.get("theme"));
  window.addEventListener("message", function (e) { if (e.source === window.parent && e.data && e.data.chartTheme) theme(e.data.chartTheme); });
}

var M = D.model, NS = "http://www.w3.org/2000/svg";
var byId = {}; M.nodes.forEach(function (n) { byId[n.id] = n; });
var kidsOf = {}, ups = {};
M.edges.forEach(function (e) {
  (kidsOf[e.from] = kidsOf[e.from] || []).push(e);
  (ups[e.to] = ups[e.to] || []).push(e.from);
});
var linked = {}; M.edges.forEach(function (e) { linked[e.from] = linked[e.to] = 1; });
var starts = M.nodes.filter(function (n) { return linked[n.id] && !ups[n.id]; })
  .sort(function (a, b) { return a.y - b.y || a.x - b.x; });

var map = document.getElementById("map"), bar = document.getElementById("bar");
var svg = map.querySelector("svg");
var VB = svg.viewBox.baseVal, BG = "#f6f7f9";
function mk(tag, attrs, parent) {
  var e = document.createElementNS(NS, tag);
  for (var k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }

/* the overlay: a veil with holes cut for what is lit, covers for Test, and a hit area per box */
var defs = mk("defs", {}, svg);
var mask = mk("mask", { id: "fl-m", maskUnits: "userSpaceOnUse", x: 0, y: 0, width: VB.width, height: VB.height }, defs);
mk("rect", { x: 0, y: 0, width: VB.width, height: VB.height, fill: "#fff" }, mask);
var holes = mk("g", {}, mask);
var veil = mk("rect", { class: "fl-veil", x: 0, y: 0, width: VB.width, height: VB.height, fill: BG, mask: "url(#fl-m)" }, svg);
var ring = mk("g", { class: "fl-ring" }, svg);
var covers = mk("g", { class: "fl-covers" }, svg);
var hits = mk("g", { class: "fl-hits" }, svg);
M.nodes.forEach(function (n) {
  var r = mk("rect", { x: n.x, y: n.y, width: n.w, height: n.h, rx: 10, "data-k": n.id }, hits);
  r.addEventListener("click", function () { tap(n.id); });
});

function route(k) {           // k and everything above it
  var out = {}, todo = [k];
  while (todo.length) { var x = todo.pop(); if (out[x]) continue; out[x] = 1; (ups[x] || []).forEach(function (p) { todo.push(p); }); }
  return out;
}
var lit = null;
function light(set, current) {
  lit = set; holes.innerHTML = ""; ring.innerHTML = "";
  veil.style.display = set ? "" : "none";
  if (!set) return;
  M.nodes.forEach(function (n) {
    if (set[n.id]) mk("rect", { x: n.x - 4, y: n.y - 4, width: n.w + 8, height: n.h + 8, rx: 12, fill: "#000" }, holes);
  });
  M.edges.forEach(function (e) {
    if (!(set[e.from] && set[e.to])) return;
    if (e.d) mk("path", { d: e.d, fill: "none", stroke: "#000", "stroke-width": 16 }, holes);
    if (e.lb) mk("rect", { x: e.lb[0] - 6, y: e.lb[1] - 4, width: e.lb[2] + 12, height: e.lb[3] + 8, fill: "#000" }, holes);
  });
  (current || []).forEach(function (k) {
    var n = byId[k]; mk("rect", { x: n.x - 4, y: n.y - 4, width: n.w + 8, height: n.h + 8, rx: 12 }, ring);
  });
}
function scrollTo(k) {
  var n = byId[k], sc = svg.getBoundingClientRect().width / VB.width;
  map.scrollTo({ left: (n.x + n.w / 2) * sc - map.clientWidth / 2, behavior: "smooth" });
  if (EMBED) return;   // the note scrolls itself; a frame cannot
  var top = svg.getBoundingClientRect().top + window.scrollY + n.y * sc - 140;
  if (Math.abs(top - window.scrollY) > window.innerHeight * 0.6) window.scrollTo({ top: top, behavior: "smooth" });
}

var mode = "look", focus = null, trail = [], path = {};

/* Look */
function lookStart() {
  focus = null; light(null); covers.innerHTML = "";
  bar.innerHTML = ""; bar.appendChild(el("p", "qh", "Click any box to light the route to it and fade the rest. Click it again to see everything."));
}
function look(k) {
  if (focus === k) { lookStart(); return; }
  focus = k; var set = route(k);
  if (M.kind === "tree" && /^g/.test(k)) (kidsOf[k] || []).forEach(function (e) { set[e.to] = 1; });
  light(set, [k]);
  bar.innerHTML = ""; bar.appendChild(el("p", "q", byId[k].title));
  bar.appendChild(el("p", "qh", "The route to it is lit. Click it again to see everything."));
}

/* Walk: the chart's own arrows, asked as questions from the top */
function short(t) { return t.length > 70 ? t.slice(0, 68) + "…" : t; }
function answer(e) { return e.label ? e.label + " → " + short(byId[e.to].title) : short(byId[e.to].title); }
function trailEl() { var ul = el("ul", "trail"); trail.forEach(function (t) { ul.appendChild(el("li", null, t)); }); return ul; }
function again(a) { var r = el("button", "ghost", "Start again"); r.addEventListener("click", walkStart); a.appendChild(r); }
function step(k) {
  path[k] = 1;
  var ks = kidsOf[k] || [];
  while (ks.length === 1 && !ks[0].label) { k = ks[0].to; path[k] = 1; ks = kidsOf[k] || []; }
  light(path, [k]);
  bar.innerHTML = ""; if (trail.length) bar.appendChild(trailEl());
  bar.appendChild(el("p", "q", byId[k].title));
  var a = el("div", "ans");
  if (!ks.length) {
    bar.appendChild(el("p", "qh", "The end of this route: its box is lit below."));
    bar.appendChild(a); again(a); scrollTo(k); return;
  }
  bar.appendChild(el("p", "qh", ks.length > 1 ? "Which way?" : "Then:")); bar.appendChild(a);
  ks.forEach(function (e) {
    var b = el("button", null, answer(e)); a.appendChild(b);
    b.addEventListener("click", function () { trail.push(e.label || short(byId[e.to].title)); step(e.to); });
  });
  if (trail.length) again(a);
  scrollTo(k);
}
function walkStart() {
  covers.innerHTML = ""; trail = []; path = {};
  if (starts.length === 1) { step(starts[0].id); return; }
  light({}, []);
  bar.innerHTML = ""; bar.appendChild(el("p", "q", "Where do you start?"));
  var a = el("div", "ans"); bar.appendChild(a);
  starts.forEach(function (n) {
    var b = el("button", null, short(n.title)); a.appendChild(b);
    b.addEventListener("click", function () { trail.push(short(n.title)); step(n.id); });
  });
}

/* Test: every box below the start is covered; tap the next one to uncover it */
var shown = {};
function canShow(n) { return n.req.every(function (r) { return shown[r]; }); }
function drawCovers() {
  covers.innerHTML = "";
  M.nodes.forEach(function (n) {
    if (shown[n.id]) return;
    var next = canShow(n);
    mk("rect", { x: n.x - 2, y: n.y - 2, width: n.w + 4, height: n.h + 4, rx: 11, class: next ? "fl-cover next" : "fl-cover" }, covers);
    if (next) {
      var t = mk("text", { x: n.x + n.w / 2, y: n.y + Math.min(n.h / 2, 40) + 5, "text-anchor": "middle", class: "fl-pill" }, covers);
      t.textContent = "Tap to reveal";
    }
  });
}
function testStart() {
  light(null); shown = {};
  M.nodes.forEach(function (n) { if (!n.hide) shown[n.id] = 1; });
  bar.innerHTML = "";
  bar.appendChild(el("p", "qh", M.kind === "tree"
    ? "Each card is covered. Recall the next one in each column, then tap to check it."
    : "Everything after the start is covered. Recall what comes next, then tap a box marked 'Tap to reveal' to check."));
  var a = el("div", "ans"); bar.appendChild(a);
  var r = el("button", "ghost", "Cover them all again"); r.addEventListener("click", testStart); a.appendChild(r);
  drawCovers();
}
function tap(k) {
  if (mode === "look") look(k);
  else if (mode === "test" && !shown[k] && canShow(byId[k])) { shown[k] = 1; drawCovers(); }
}

document.querySelectorAll("#modes .chip").forEach(function (b) {
  b.addEventListener("click", function () {
    mode = b.dataset.mode;
    document.querySelectorAll("#modes .chip").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    map.classList.toggle("is-look", mode === "look"); map.classList.toggle("is-test", mode === "test");
    if (mode === "look") lookStart(); else if (mode === "walk") walkStart(); else testStart();
  });
});
map.classList.add("is-look"); lookStart();

if (EMBED && window.parent !== window) {
  var tell = function () { window.parent.postMessage({ chartHeight: document.querySelector(".wrap").getBoundingClientRect().height }, "*"); };
  tell(); if (window.ResizeObserver) new ResizeObserver(tell).observe(document.querySelector(".wrap"));
}
})();
