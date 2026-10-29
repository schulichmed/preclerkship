/* Interactive overview chart: the content spec of a drawn chart, laid out as an HTML grid
   with Look / Walk / Test modes. D = {spec, walk?} is set by the page. */
(function () {
/* ?embed: the chart inside a lecture note (portal.js frames it). No page header, the note's
   theme, and the height reported up so the note scrolls rather than the frame. */
var Q = new URLSearchParams(location.search), EMBED = Q.has("embed"), ROOT = document.documentElement;
function theme(t) { if (t === "dark" || t === "light") ROOT.setAttribute("data-theme", t); }
if (EMBED) {
  ROOT.classList.add("embed"); theme(Q.get("theme"));
  window.addEventListener("message", function (e) { if (e.source === window.parent && e.data && e.data.chartTheme) theme(e.data.chartTheme); });
}
var S = D.spec;
var COL = {"teal": "#1f6f8b", "purple": "#6a4aa8", "orange": "#b5600f", "blue": "#1f5f9e", "magenta": "#a3336b", "brown": "#8a5a2b", "olive": "#4f6d1f", "slate": "#46607a"};
var ROWS = S.sections.filter(function (k) { return k !== "head"; }).map(function (k) { return [k, (S.row_names || {})[k] || k]; });
var DASHED = S.dashed_sections || [];
var GROUPS = S.groups || [], TIERS = S.tiers || [], PRES = S.pres || [], PANELS = S.panels || [], SPANS = S.spans || [];
var colById = {}; S.columns.forEach(function (c, i) { c.i = i; colById[c.id] = c; });

/* who feeds whom, exactly as column_pathway.py draws it */
function groupOf(i) { return GROUPS.filter(function (g) { return g.cols[0] <= i && i <= g.cols[1]; })[0]; }
function presOf(g) { return PRES.filter(function (p) { return p.group === g.id; })[0]; }
function feedOfGroup(g) { var p = presOf(g); return p ? p.id : g.id; }
var parent = { };
GROUPS.forEach(function (g) { parent[g.id] = "root"; var p = presOf(g); if (p) parent[p.id] = g.id; });
TIERS.forEach(function (t) { var g = groupOf(t.cols[0]); parent[t.id] = g ? feedOfGroup(g) : "root"; });
S.columns.forEach(function (c) { var g = groupOf(c.i); parent["c:" + c.id] = c.drop_from || (g ? feedOfGroup(g) : "root"); });
function chain(k) { var out = [k]; while (parent[k]) { k = parent[k]; out.push(k); } return out; }

function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
function lines(host, ls) {
  var ul = null;
  (ls || []).forEach(function (l) {
    var muted = l.charAt(0) === "~"; if (muted) l = l.slice(1);
    if (l.indexOf("• ") === 0) {
      if (!ul) { ul = el("ul"); host.appendChild(ul); }
      ul.appendChild(el("li", muted ? "mut" : null, l.slice(2)));
    } else { ul = null; host.appendChild(el("p", muted ? "mut" : null, l)); }
  });
}
function cell(b, c) {
  var d = el("div", "cell " + b[0]); d.style.setProperty("--c", COL[c.colour]);
  d.appendChild(el("div", "ct", b[1])); lines(d, b[2]); return d;
}
function stages(host, c, row, dashed) {
  (c[row] || []).forEach(function (stage, i) {
    if (i) host.appendChild(el("div", dashed ? "arr dash" : "arr"));
    var s = el("div", "stage"); stage.forEach(function (b) { s.appendChild(cell(b, c)); }); host.appendChild(s);
  });
}
function head(c) {
  var h = c.head[0][0], d = el("div", "colhead"); d.style.setProperty("--c", COL[c.colour]);
  d.appendChild(el("div", "nt", h[1])); (h[2] || []).forEach(function (l) { d.appendChild(el("div", "nl", l.replace(/^~/, ""))); });
  return d;
}
function node(o, cls) {
  var d = el("div", "node " + (cls || "")); d.appendChild(el("div", "nt", o.title));
  var ls = o.lines || []; if (ls.length) { var w = el("div", "nl"); lines(w, ls); d.appendChild(w); }
  return d;
}
function span(cols) { return (cols[0] + 1) + " / " + (cols[1] + 2); }

function buildMap(host) {
  host.innerHTML = "";
  var g = el("div", "grid"); g.style.gridTemplateColumns = "repeat(" + S.columns.length + ",minmax(150px,1fr))";
  g.style.minWidth = (S.columns.length * 158) + "px";
  var row = 1;
  function put(e, cols) { e.style.gridColumn = cols ? span(cols) : "1 / -1"; e.style.gridRow = String(row); g.appendChild(e); }
  function gap() { row++; var a = el("div", "gap"); put(a); row++; }
  var r = node(S.root, "root"); r.dataset.k = "root"; put(r);
  if (GROUPS.length) { gap(); GROUPS.forEach(function (gr) { var n = node(gr); n.dataset.k = gr.id; put(n, gr.cols); }); }
  if (PRES.length) { gap(); PRES.forEach(function (p) { var gr = GROUPS.filter(function (x) { return x.id === p.group; })[0]; var n = node(p, "pres"); n.dataset.k = p.id; put(n, gr.cols); }); }
  if (TIERS.length) { gap(); TIERS.forEach(function (t) { var n = node(t); n.dataset.k = t.id; put(n, t.cols); }); }
  gap();
  S.columns.forEach(function (c) {
    var col = el("div", "col"); col.style.setProperty("--c", COL[c.colour]); col.dataset.k = "c:" + c.id;
    col.style.gridColumn = (c.i + 1) + " / " + (c.i + 2); col.style.gridRow = String(row);
    col.appendChild(el("div", "sp"));
    col.appendChild(el("div", "drop", c.drop_label || " "));
    col.appendChild(head(c));
    ROWS.forEach(function (rw) {
      if (!(c[rw[0]] || []).length) return;
      var sec = el("div", "sec"); sec.dataset.row = rw[0];
      sec.appendChild(el("div", "arr"));
      sec.appendChild(el("div", "rowlabel", rw[1]));
      var wrap = el("div", "stagewrap"); stages(wrap, c, rw[0], DASHED.indexOf(rw[0]) > -1); sec.appendChild(wrap);
      col.appendChild(sec);
    });
    g.appendChild(col);
  });
  /* a section shared by adjacent columns (column_pathway.py "spans"): one block below them */
  if (SPANS.length) row++;
  SPANS.forEach(function (sp, i) {
    var b = el("div", "spanblk"); b.dataset.span = String(i);
    var sec = el("div", "sec"); sec.dataset.row = sp.section;
    sec.appendChild(el("div", "rowlabel", (S.row_names || {})[sp.section] || sp.section));
    var wrap = el("div", "stagewrap"); stages(wrap, { colour: "slate", s: sp.rows }, "s", false); sec.appendChild(wrap);
    b.appendChild(sec); put(b, sp.cols);
  });
  host.appendChild(g);
  if (PANELS.length) {
    var p = el("div", "panels"); p.style.minWidth = g.style.minWidth;
    PANELS.forEach(function (pn) {
      var d = el("div", "panel"); d.appendChild(el("b", null, pn.title));
      var ul = el("ul"); pn.items.forEach(function (it) { ul.appendChild(el("li", null, it.replace(/^~/, "").replace(/^• /, ""))); }); d.appendChild(ul); p.appendChild(d);
    });
    host.appendChild(p);
  }
  return host;
}

var map = buildMap(document.getElementById("map")), bar = document.getElementById("bar");
var mode = "look", trail = [], lit = [], focus = null;

/* connectors drawn like the chart in the notes: elbows that branch from a box, straight drops into each diagnosis through its label */
var NS = "http://www.w3.org/2000/svg";
function drawLinks() {
  var g = map.querySelector(".grid"), old = g.querySelector(".links"); if (old) old.remove();
  var gr = g.getBoundingClientRect(), svg = document.createElementNS(NS, "svg");
  svg.setAttribute("class", "links"); svg.setAttribute("width", g.scrollWidth); svg.setAttribute("height", g.scrollHeight);
  svg.innerHTML = '<defs><marker id="lk-ah" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="10" orient="auto"><path d="M0 0L10 5L0 10z"/></marker></defs>';
  function box(e) { var r = e.getBoundingClientRect(); return { t: r.top - gr.top, b: r.bottom - gr.top, x: (r.left + r.right) / 2 - gr.left }; }
  function path(d, key, arrow) {
    var p = document.createElementNS(NS, "path"); p.setAttribute("d", d); p.setAttribute("data-a", key);
    if (arrow) p.setAttribute("marker-end", "url(#lk-ah)"); svg.appendChild(p);
  }
  var q = function (k) { return g.querySelector('[data-k="' + k + '"]'); };
  Object.keys(parent).forEach(function (k) {
    var from = q(parent[k]), to = q(k); if (!from || !to) return;
    var a = box(from);
    if (k.indexOf("c:") === 0) {
      var col = to, h = box(col.querySelector(".colhead")), x = h.x, c = colById[k.slice(2)], lab = col.querySelector(".drop");
      if (c.drop_label && lab) {
        var lb = box(lab);
        path("M" + x + " " + a.b + "V" + (lb.t - 2), k, false);
        path("M" + x + " " + (lb.b + 2) + "V" + (h.t - 1), k, true);
      } else path("M" + x + " " + a.b + "V" + (h.t - 1), k, true);
    } else {
      var b = box(to), mid = (a.b + b.t) / 2;
      path("M" + a.x + " " + a.b + "V" + mid + "H" + b.x + "V" + (b.t - 1), k, true);
    }
  });
  SPANS.forEach(function (sp, i) {
    var first = g.querySelector('[data-span="' + i + '"] .stage'); if (!first) return;
    var t = box(first).t;
    S.columns.slice(sp.cols[0], sp.cols[1] + 1).forEach(function (c) {
      var col = q("c:" + c.id), st = col && col.querySelectorAll(".stage"); if (!st || !st.length) return;
      var x = box(col.querySelector(".colhead")).x;
      path("M" + x + " " + box(st[st.length - 1]).b + "V" + (t - 1), "c:" + c.id, true);
    });
  });
  g.appendChild(svg);
  if (map.classList.contains("walking")) light();
}

function clearMarks() {
  map.classList.remove("walking");
  map.querySelectorAll(".on").forEach(function (e) { e.classList.remove("on"); });
  map.querySelectorAll(".sec.hidden").forEach(function (e) { e.classList.remove("hidden", "next"); });
}
function light() {
  map.classList.add("walking");
  map.querySelectorAll(".on").forEach(function (e) { e.classList.remove("on"); });
  lit.forEach(function (k) {
    var e = map.querySelector('[data-k="' + k + '"]'); if (e) e.classList.add("on");
    map.querySelectorAll('[data-a="' + k + '"]').forEach(function (a) { a.classList.add("on"); });
  });
}
function trailEl() { var ul = el("ul", "trail"); trail.forEach(function (t) { ul.appendChild(el("li", null, t)); }); return ul; }
function again(a) { var r = el("button", "ghost", "Start again"); r.addEventListener("click", walkStart); a.appendChild(r); }
function scrollToCol(k) {
  var col = map.querySelector('[data-k="' + k + '"]');
  if (col) map.scrollTo({ left: col.offsetLeft - map.clientWidth / 2 + col.offsetWidth / 2, behavior: "smooth" });
}

/* Look */
function lookStart() {
  clearMarks(); focus = null;
  bar.innerHTML = ""; bar.appendChild(el("p", "qh", "Click any column to focus it and fade the rest. Click it again to see them all."));
}
map.querySelectorAll(".col").forEach(function (col) {
  col.addEventListener("click", function () {
    if (mode !== "look") return;
    var k = col.dataset.k;
    if (focus === k) { lookStart(); return; }
    focus = k; lit = chain(k); light();
    bar.innerHTML = ""; bar.appendChild(el("p", "q", colById[k.slice(2)].head[0][0][1]));
    bar.appendChild(el("p", "qh", "The route to it is lit. Click it again to see everything."));
  });
});

/* Walk: the chart's own branches, asked as questions from the top */
function kids(k) { return Object.keys(parent).filter(function (x) { return parent[x] === k; }); }
function info(k) {
  if (k === "root") return S.root;
  if (k.indexOf("c:") === 0) return null;
  return GROUPS.concat(TIERS, PRES).filter(function (x) { return x.id === k; })[0];
}
function label(k) {
  if (k.indexOf("c:") === 0) { var c = colById[k.slice(2)]; return c.drop_label ? c.drop_label + " → " + c.head[0][0][1] : c.head[0][0][1]; }
  var t = info(k).title, cut = t.split(/:\s| · /)[0];
  return cut.length >= 3 && cut.length < t.length ? cut : t;
}
function step(k) {
  var ks = kids(k);
  while (ks.length === 1 && k.indexOf("c:") !== 0) { k = ks[0]; lit.push(k); ks = kids(k); }
  light();
  if (k.indexOf("c:") === 0) { walkEnd(k); return; }
  var o = info(k), w = (D.walk || {})[k] || {};
  bar.innerHTML = ""; if (trail.length) bar.appendChild(trailEl());
  bar.appendChild(el("p", "q", w.q || o.title));
  if (w.help) bar.appendChild(el("p", "qh", w.help));
  var a = el("div", "ans"); bar.appendChild(a);
  ks.forEach(function (x) {
    var b = el("button", null, label(x)); a.appendChild(b);
    b.addEventListener("click", function () { trail.push(label(x)); lit.push(x); step(x); });
  });
  if (trail.length) again(a);
}
function walkEnd(k) {
  bar.innerHTML = ""; bar.appendChild(trailEl());
  bar.appendChild(el("p", "q", colById[k.slice(2)].head[0][0][1])); bar.appendChild(el("p", "qh", "Its column is lit below."));
  var a = el("div", "ans"); bar.appendChild(a); again(a); scrollToCol(k);
}
function walkStart() { clearMarks(); trail = []; lit = ["root"]; step("root"); }

/* Test: each column starts as just its name; every tap reveals the next row, in order */
function testStart() {
  clearMarks(); bar.innerHTML = "";
  var names = ROWS.map(function (r) { return r[1].toLowerCase(); });
  bar.appendChild(el("p", "qh", "Each column shows only its name. Recall its " + names[0] + ", then tap to check." + (names.length > 1 ? " Each tap reveals the next row: " + names.slice(1).join(", then ") + "." : "")));
  var a = el("div", "ans"); bar.appendChild(a);
  var r = el("button", "ghost", "Hide them all again"); r.addEventListener("click", testStart); a.appendChild(r);
  map.querySelectorAll(".col").forEach(function (col) {
    col.querySelectorAll(".sec").forEach(function (s, i) { s.classList.add("hidden"); if (i === 0) s.classList.add("next"); });
  });
  map.querySelectorAll(".spanblk .sec").forEach(function (s) { s.classList.add("hidden", "next"); });
}
map.querySelectorAll(".spanblk").forEach(function (b) {
  b.addEventListener("click", function () { if (mode === "test") b.querySelectorAll(".sec").forEach(function (s) { s.classList.remove("hidden", "next"); }); });
});
map.querySelectorAll(".col").forEach(function (col) {
  col.addEventListener("click", function () {
    if (mode !== "test") return;
    var s = col.querySelector(".sec.hidden"); if (!s) return;
    s.classList.remove("hidden", "next");
    var n = col.querySelector(".sec.hidden"); if (n) n.classList.add("next");
  });
});

document.querySelectorAll("#modes .chip").forEach(function (b) {
  b.addEventListener("click", function () {
    mode = b.dataset.mode;
    document.querySelectorAll("#modes .chip").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
    map.classList.toggle("is-look", mode === "look"); map.classList.toggle("is-test", mode === "test");
    if (mode === "look") lookStart(); else if (mode === "walk") walkStart(); else testStart();
  });
});
map.classList.add("is-look"); lookStart();
drawLinks();
if (window.ResizeObserver) new ResizeObserver(function () { drawLinks(); }).observe(map.querySelector(".grid"));
if (document.fonts && document.fonts.ready) document.fonts.ready.then(drawLinks);
if (EMBED && window.parent !== window) {
  var tell = function () { window.parent.postMessage({ chartHeight: document.querySelector(".wrap").getBoundingClientRect().height }, "*"); };
  tell(); if (window.ResizeObserver) new ResizeObserver(tell).observe(document.querySelector(".wrap"));
}

/* #col=<column id> opens the chart with that diagnosis focused (the body map links straight to one) */
function focusFromHash() {
  var m = /col=([\w-]+)/.exec(location.hash), col = m && map.querySelector('[data-k="c:' + m[1] + '"]');
  if (!col) return;
  focus = null; col.click(); setTimeout(function () { scrollToCol("c:" + m[1]); drawLinks(); }, 80);
}
window.addEventListener("hashchange", focusFromHash); focusFromHash();

/* a picture of each diagnosis under its name, from charts/figures.json (openly licensed, credited at the foot); tap for full size */
var CHART = location.pathname.replace(/\/(index\.html)?$/, "").split("/").pop();
fetch("../figures.json").then(function (r) { return r.ok ? r.json() : {}; }).then(function (all) {
  var figs = all[CHART]; if (!figs) return;
  var used = [];
  S.columns.forEach(function (c) {
    var f = figs[c.id], col = f && map.querySelector('.col[data-k="c:' + c.id + '"]'); if (!col) return;
    var fig = el("figure", "colfig"), a = el("a"); a.href = "../img/" + CHART + "/" + f.file; a.target = "_blank"; a.rel = "noopener";
    a.addEventListener("click", function (e) { e.stopPropagation(); });
    var img = el("img"); img.src = a.href; img.alt = f.caption; img.loading = "lazy"; a.appendChild(img); fig.appendChild(a);
    fig.appendChild(el("figcaption", null, f.caption));
    col.querySelector(".colhead").after(fig); used.push(f);
  });
  if (!used.length) return;
  var cr = el("section", "credits"); cr.appendChild(el("h3", null, "Image credits"));
  cr.appendChild(el("p", null, "Pictures reused under their open licences (Creative Commons or public domain); drawn ones were made for this page. Tap a picture to open it full size."));
  var ul = el("ul"); cr.appendChild(ul);
  used.forEach(function (f) {
    var li = el("li", null, f.caption + ": " + f.author + ", " + f.licence + (f.source_page_url ? ", " : ""));
    if (f.source_page_url) { var s = el("a", null, "source"); s.href = f.source_page_url; s.rel = "noopener"; li.appendChild(s); }
    ul.appendChild(li);
  });
  document.querySelector(".wrap").appendChild(cr);
  drawLinks();
}).catch(function () {});
})();
