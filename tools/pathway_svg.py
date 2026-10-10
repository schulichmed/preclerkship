# -*- coding: utf-8 -*-
"""Draw a clinical pathway (boxes, arrows, decisions) as a standalone SVG.

Purpose: replace a lecture chart's mermaid flowchart with a hand-placed SVG in
         the class-tree palette, so arrows never cross a box and every line of
         text is measured to fit inside its card.
Author:  Noor Simsam
Date:    2026-10-10
Input:   a spec in tools/pathways/<name>.json
Output:  <name>.svg written where --out says (normally the vault's Attachments),
         plus a --png preview and a list of layout problems on stderr

Usage:
    python tools/pathway_svg.py tools/pathways/osteoporosis_pathway.json \\
        --out "$VAULT/Attachments/osteoporosis pathway.svg" --png /tmp/p.png

The exit code is 1 when the check finds an error (a box overlapping another, a
word too wide for its box, an edge to an unknown node). Warnings - an edge
passing through a box, a label sitting on a box - print but do not fail; look
at the preview for those.

Spec shape (every coordinate is in px on a canvas `width` wide, default 920):

    {"name": "osteoporosis pathway",
     "title": "one sentence read by screen readers",
     "any_of": {"heading": "Osteoporosis is diagnosed by ANY ONE of these:",
                "items": [{"title": "Fragility fracture", "lines": ["~not skull ..."]}, ...]},
     "nodes": [{"id": "start", "x": 270, "y": 10, "w": 360, "kind": "plain",
                "title": "Postmenopausal woman or man >= 50", "lines": ["..."]}],
     "edges": [{"from": "start", "to": "q1", "label": "yes",
                "from_side": "bottom", "to_side": "top", "from_dx": 0, "to_dx": 0,
                "path": "M450 58V88"}],
     "panels": [{"x": 15, "y": 782, "w": 655, "title": "Risk factors",
                 "items": ["..."], "cols": 2}],
     "note": "an italic footnote under everything"}

- `any_of` draws the free-standing boxes with OR between them across the top
  and pushes everything else down; leave it out when the chart has no such row.
- A node's height is worked out from its text unless `h` is given. Lines that
  start with "~" are drawn muted and italic (a qualifier, not a fact). Text
  wraps to the box, so give `w` and let `h` follow.
- kinds: plain (a step or question), bad (no / stop / do not), warn (maybe,
  intermediate, caution), ok (yes / treat / the answer), anti and ana (two drug
  families), info (a neutral highlight), dark (a root heading), lo (a plain
  step the lecture's learning objectives ask for - the vault's yellow "classDef
  lo"). Colour is for outcomes and answers; the steps leading to them stay plain.
- `"dashed": true` on an edge draws it dashed (mermaid's -.- : "goes with", not "leads to").
- An edge without `path` runs from the middle of `from_side` of one box to the
  middle of `to_side` of the other, nudged by from_dx/to_dx (px along that
  side). Straight when the two points line up, a smooth curve otherwise. Give
  `path` (SVG path data, ending at the target) for a rail around the outside.
  `label_at` [x, y] places a label by hand when the midpoint is crowded.
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import ImageFont

LOG = logging.getLogger("pathway_svg")

FONT_DIRS = ["/mnt/c/Windows/Fonts", "C:/Windows/Fonts", "/Library/Fonts",
             "/usr/share/fonts/truetype/msttcorefonts"]
FONT_FILES = {"reg": "arial.ttf", "bold": "arialbd.ttf", "ital": "ariali.ttf",
              "serif": "georgiab.ttf"}
FALLBACK = {"reg": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "ital": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
            "serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"}
SANS = "Arial, 'Segoe UI Symbol', 'Liberation Sans', Helvetica, sans-serif"
SERIF = "Georgia, 'DejaVu Serif', serif"

P = {"bg": "#f6f7f9", "surface": "#ffffff", "ink": "#18212e", "muted": "#5a6577",
     "line": "#c9d0db", "bad": "#b3261e", "bad_soft": "#fbe5e3", "ok": "#2f7d5b",
     "ok_soft": "#e2f2ea", "warn": "#a45a12", "warn_soft": "#fbeedd",
     "anti": "#1f6f8b", "anti_soft": "#e0f0f5", "ana": "#6a4aa8", "ana_soft": "#eee8f8",
     "info": "#1f5f9e", "info_soft": "#e3edf8"}
KIND = {  # kind -> (fill, stroke, title colour, body colour)
    "plain": (P["surface"], P["line"], P["ink"], P["ink"]),
    "bad": (P["bad_soft"], P["bad"], P["bad"], P["ink"]),
    "warn": (P["warn_soft"], P["warn"], P["warn"], P["ink"]),
    "ok": (P["ok_soft"], P["ok"], P["ok"], P["ink"]),
    "anti": (P["anti_soft"], P["anti"], P["anti"], P["ink"]),
    "ana": (P["ana_soft"], P["ana"], P["ana"], P["ink"]),
    "info": (P["info_soft"], P["info"], P["info"], P["ink"]),
    "dark": (P["ink"], P["ink"], P["bg"], P["bg"]),
    "lo": ("#fff4c2", "#c9a227", "#6b5200", P["ink"]),
}
TITLE_SIZE, BODY_SIZE = 14.5, 12.5
TITLE_STEP, BODY_STEP = 20, 18
PAD_X, PAD_Y = 10, 12          # inside a box, each side
WRAP = 0.95                    # fill to this share of the inner width, for wider substitute faces
WIDTH = 920
ANY_TOP = 175                  # the OR row's height, when there is one

_fonts = {}


def font(style: str, size: float) -> ImageFont.FreeTypeFont:
    """The measuring font for a style at a size, Windows faces first."""
    key = (style, size)
    if key not in _fonts:
        path = next((os.path.join(d, FONT_FILES[style]) for d in FONT_DIRS
                     if os.path.exists(os.path.join(d, FONT_FILES[style]))), FALLBACK[style])
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def measure(text: str, style: str, size: float) -> float:
    return font(style, size).getlength(text)


def wrap(text: str, style: str, size: float, width: float) -> list:
    """Greedy word wrap to `width` px; a single word wider than that stays whole."""
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if cur and measure(trial, style, size) > width * WRAP:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines or [""]


class Chart(object):
    def __init__(self, spec: dict):
        self.spec = spec
        self.width = spec.get("width", WIDTH)
        self.top = ANY_TOP if spec.get("any_of") else 0
        self.parts, self.errors, self.warnings = [], [], []
        self.boxes = {}          # id -> (x, y, w, h), in canvas coordinates
        self.label_boxes = []

    # ---------- primitives ----------

    def text(self, x, y, s, size=BODY_SIZE, weight=400, fill=None, anchor="middle",
             family=SANS, italic=False, halo=False):
        extra = ' font-style="italic"' if italic else ""
        if halo:
            extra += (' stroke="%s" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'
                      % P["bg"])
        self.parts.append(
            '<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" font-weight="%s" '
            'fill="%s" text-anchor="%s"%s>%s</text>'
            % (x, y, family, size, weight, fill or P["ink"], anchor, extra, escape(s)))

    def rect(self, x, y, w, h, fill, stroke, sw=1.5, rx=10):
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" '
                          'fill="%s" stroke="%s" stroke-width="%s"/>'
                          % (x, y, w, h, rx, fill, stroke, sw))

    # ---------- boxes ----------

    def layout_text(self, node: dict, w: float) -> list:
        """[(text, style, size, step)] for a node, wrapped to its inner width."""
        inner = w - 2 * PAD_X
        rows = []
        for line in wrap(node["title"], "bold", TITLE_SIZE, inner):
            rows.append((line, "bold", TITLE_SIZE, TITLE_STEP))
        for raw in node.get("lines", []):
            style = "ital" if raw.startswith("~") else "reg"
            for line in wrap(raw.lstrip("~"), style, BODY_SIZE, inner):
                rows.append((line, style, BODY_SIZE, BODY_STEP))
        for line, style, size, _ in rows:
            if measure(line, style, size) > inner:
                self.errors.append("%s: %r is wider than its box (%.0f > %.0f px); widen it"
                                   % (node.get("id", node["title"]), line,
                                      measure(line, style, size), inner))
        return rows

    def box(self, node: dict, dy: float = 0, stroke_width: float = 1.5, stroke_override: str = None):
        kind = node.get("kind", "plain")
        if kind not in KIND:
            self.errors.append("%s: unknown kind %r" % (node.get("id"), kind))
            kind = "plain"
        fill, stroke, tcol, bcol = KIND[kind]
        x, y, w = node["x"], node["y"] + dy, node["w"]
        rows = self.layout_text(node, w)
        block = sum(r[3] for r in rows) - rows[-1][3] + (TITLE_SIZE if rows[-1][1] == "bold" else BODY_SIZE)
        h = node.get("h") or round(block + 2 * PAD_Y + 4)
        if h < block + 2 * PAD_Y - 2:
            self.errors.append("%s: h=%s is too short for its text (needs %.0f)"
                               % (node.get("id"), h, block + 2 * PAD_Y))
        self.rect(x, y, w, h, fill, stroke_override or stroke, stroke_width)
        cy = y + (h - block) / 2 + (TITLE_SIZE if rows[0][1] == "bold" else BODY_SIZE) * 0.8
        for line, style, size, step in rows:
            muted = style == "ital"
            self.text(x + w / 2, cy, line, size, 700 if style == "bold" else 400,
                      (P["muted"] if muted else (tcol if style == "bold" else bcol)),
                      italic=muted)
            cy += step
        if "id" in node:
            if node["id"] in self.boxes:
                self.errors.append("duplicate node id %r" % node["id"])
            self.boxes[node["id"]] = (x, y, w, h)
        return h

    def any_of(self, spec: dict):
        """The diagnosis row: free-standing boxes with OR between them."""
        self.text(self.width / 2, 34, spec["heading"], 18, 700, P["ink"], family=SERIF)
        items = spec["items"]
        gap = 70
        w = (self.width - 30 - gap * (len(items) - 1)) / len(items)
        heights = []
        for i, it in enumerate(items):
            node = {"x": 15 + i * (w + gap), "y": 56, "w": w, "kind": "plain",
                    "title": it["title"], "lines": it.get("lines", []), "id": "_any%d" % i}
            heights.append(len(self.layout_text(node, w)))
        rows = max(heights)
        h = round(TITLE_STEP + BODY_STEP * (rows - 1) + 2 * PAD_Y + 2)
        for i, it in enumerate(items):
            node = {"x": 15 + i * (w + gap), "y": 56, "w": w, "h": h, "kind": "plain",
                    "title": it["title"], "lines": it.get("lines", []), "id": "_any%d" % i}
            # an ink border sets the alternatives apart from the steps below
            self.box(node, stroke_width=2, stroke_override=P["ink"])
        for i in range(len(items) - 1):
            cx = 15 + (i + 1) * (w + gap) - gap / 2
            self.text(cx, 56 + h / 2 + 7, spec.get("joiner", "OR"), 20, 700, P["ink"], family=SERIF)
        if 56 + h + 20 > ANY_TOP:
            self.errors.append("any_of row is %.0f px tall; shorten its lines" % (56 + h))

    # ---------- edges ----------

    def port(self, nid: str, side: str, d: float):
        x, y, w, h = self.boxes[nid]
        return {"top": (x + w / 2 + d, y), "bottom": (x + w / 2 + d, y + h),
                "left": (x, y + h / 2 + d), "right": (x + w, y + h / 2 + d)}[side]

    def edge(self, e: dict):
        for k in ("from", "to"):
            if e[k] not in self.boxes:
                self.errors.append("edge %s -> %s: unknown node %r" % (e["from"], e["to"], e[k]))
                return
        if "path" in e:
            d = shift_path(e["path"], self.top)
            pts = path_points(d)
            mid = pts[len(pts) // 2]
        else:
            fs, ts = e.get("from_side", "bottom"), e.get("to_side", "top")
            (x1, y1) = self.port(e["from"], fs, e.get("from_dx", 0))
            (x2, y2) = self.port(e["to"], ts, e.get("to_dx", 0))
            back = {"top": (0, -2), "bottom": (0, 2), "left": (-2, 0), "right": (2, 0)}[ts]
            x2, y2 = x2 + back[0], y2 + back[1]
            if abs(x1 - x2) < 0.5 or abs(y1 - y2) < 0.5:
                d = "M%.1f %.1fL%.1f %.1f" % (x1, y1, x2, y2)
                pts = [(x1 + (x2 - x1) * t / 20, y1 + (y2 - y1) * t / 20) for t in range(21)]
            else:
                if fs in ("top", "bottom"):
                    c1 = (x1, (y1 + y2) / 2)
                else:
                    c1 = ((x1 + x2) / 2, y1)
                if ts in ("top", "bottom"):
                    c2 = (x2, (y1 + y2) / 2)
                else:
                    c2 = ((x1 + x2) / 2, y2)
                d = "M%.1f %.1fC%.1f %.1f %.1f %.1f %.1f %.1f" % (x1, y1, c1[0], c1[1], c2[0], c2[1], x2, y2)
                pts = [bezier((x1, y1), c1, c2, (x2, y2), t / 40.0) for t in range(41)]
            mid = pts[len(pts) // 2]
        self.parts.insert(0, '<path d="%s" fill="none" stroke="%s" stroke-width="2" '
                             'marker-end="url(#ah)"%s/>'
                          % (d, P["muted"], ' stroke-dasharray="6 5"' if e.get("dashed") else ""))
        for nid, (x, y, w, h) in self.boxes.items():
            if nid in (e["from"], e["to"]):
                continue
            inside = [p for p in pts[1:-1] if x + 2 < p[0] < x + w - 2 and y + 2 < p[1] < y + h - 2]
            if inside:
                self.warnings.append("edge %s -> %s runs through box %s" % (e["from"], e["to"], nid))
        if e.get("label"):
            lx, ly = e.get("label_at", (mid[0], mid[1] + 4))
            if "label_at" in e:
                ly += self.top
            self.text(lx, ly, e["label"], 13, 700, P["muted"], halo=True)
            lw = measure(e["label"], "bold", 13)
            self.label_boxes.append((e["label"], lx - lw / 2, ly - 11, lw, 14))

    # ---------- panels ----------

    def panel(self, p: dict):
        """A titled box of bullet points, in `cols` columns sized to their longest item."""
        x, y, w = p["x"], p["y"] + self.top, p["w"]
        cols = p.get("cols", 1)
        items = p["items"]
        per = -(-len(items) // cols)
        groups = [items[c * per:(c + 1) * per] for c in range(cols)]
        bullet = measure("• ", "reg", BODY_SIZE)
        natural = [max(measure(it, "reg", BODY_SIZE) for it in g) / WRAP + bullet + 26 for g in groups]
        if sum(natural) <= w - 32:
            widths = natural[:-1] + [w - 32 - sum(natural[:-1])]
        else:
            widths = [(w - 32) / cols] * cols
        laid = []
        for g, cw in zip(groups, widths):
            rows = []
            for it in g:
                for i, l in enumerate(wrap(it, "reg", BODY_SIZE, cw - 24 - bullet)):
                    rows.append((("• " if i == 0 else "") + l, 0 if i == 0 else bullet))
            laid.append(rows)
        n = max(len(r) for r in laid)
        h = p.get("h") or round(50 + n * 20 + 6)
        self.rect(x, y, w, h, P["surface"], P["line"])
        self.text(x + 16, y + 26, p["title"], TITLE_SIZE, 700, anchor="start")
        cx = x + 16
        for rows, cw in zip(laid, widths):
            for r, (l, indent) in enumerate(rows):
                self.text(cx + indent, y + 50 + r * 20, l, BODY_SIZE, anchor="start")
            cx += cw
        self.boxes["_panel_%s" % p["title"]] = (x, y, w, h)

    # ---------- the whole chart ----------

    def build(self) -> str:
        s = self.spec
        if s.get("any_of"):
            self.any_of(s["any_of"])
        any_parts = self.parts
        self.parts = []
        for n in s["nodes"]:
            self.box(dict(n, y=n["y"] + self.top))
        for p in s.get("panels", []):
            self.panel(p)
        for e in s.get("edges", []):
            self.edge(e)
        self.check_overlaps()
        bottom = max(y + h for (x, y, w, h) in self.boxes.values())
        if s.get("note"):
            self.text(15, bottom + 24, s["note"], 12, 400, P["muted"], anchor="start", italic=True)
            bottom += 24
        height = round(bottom + 22)
        right = max(x + w for (x, y, w, h) in self.boxes.values())
        if right > self.width - 10:
            self.errors.append("a box reaches x=%.0f, past the %d px canvas" % (right, self.width))
        head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
                'role="img" aria-labelledby="t"><title id="t">%s</title>'
                '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                'markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="%s"/>'
                '</marker></defs><rect width="100%%" height="100%%" rx="14" fill="%s"/>'
                % (self.width, height, self.width, height, escape(s["title"]), P["muted"], P["bg"]))
        return head + "\n" + "\n".join(any_parts + self.parts) + "\n</svg>\n"

    def check_overlaps(self):
        items = [(k, v) for k, v in self.boxes.items() if not k.startswith("_any")]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (a, (ax, ay, aw, ah)), (b, (bx, by, bw, bh)) = items[i], items[j]
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    self.errors.append("boxes %s and %s overlap" % (a, b))
        for (label, lx, ly, lw, lh) in self.label_boxes:
            for nid, (x, y, w, h) in self.boxes.items():
                if lx < x + w and x < lx + lw and ly < y + h and y < ly + lh:
                    self.warnings.append("label %r sits on box %s; set label_at" % (label, nid))
        if self.top:
            for nid, (x, y, w, h) in self.boxes.items():
                if not nid.startswith("_any") and y < self.top:
                    self.errors.append("box %s starts above the any_of row" % nid)


def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1])


def shift_path(d: str, dy: float) -> str:
    """Move hand-written path data down by dy (the any_of row), keeping H and x values."""
    if not dy:
        return d
    out, cmd = [], None
    for tok in re.findall(r"[MLHVCQZmlhvcqz]|-?\d+(?:\.\d+)?", d):
        if tok.isalpha():
            cmd, idx = tok, 0
            out.append(tok)
            continue
        v = float(tok)
        if cmd == "V" or (cmd in "MLCQ" and idx % 2 == 1):
            v += dy
        out.append("%g" % v)
        idx += 1
    return " ".join(out)


def path_points(d: str) -> list:
    """Rough polyline through a path's absolute M/L/H/V/C endpoints, for the checks."""
    pts, x, y, cmd, nums = [], 0.0, 0.0, None, []
    toks = re.findall(r"[MLHVC]|-?\d+(?:\.\d+)?", d)
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            continue
        if cmd in ("M", "L"):
            nx, ny = float(toks[i]), float(toks[i + 1]); i += 2
        elif cmd == "H":
            nx, ny = float(toks[i]), y; i += 1
        elif cmd == "V":
            nx, ny = x, float(toks[i]); i += 1
        elif cmd == "C":
            c = [float(v) for v in toks[i:i + 6]]; i += 6
            for k in range(1, 11):
                pts.append(bezier((x, y), (c[0], c[1]), (c[2], c[3]), (c[4], c[5]), k / 10.0))
            x, y = c[4], c[5]
            continue
        else:
            i += 1
            continue
        if pts:
            for k in range(1, 11):
                pts.append((x + (nx - x) * k / 10.0, y + (ny - y) * k / 10.0))
        else:
            pts.append((nx, ny))
        x, y = nx, ny
    return pts


def render_png(svg: str, out: Path):
    """Preview with the real Arial and Georgia where Windows has them."""
    try:
        import resvg_py
    except ImportError:
        sys.path.insert(0, str(Path.home() / ".cache" / "preclerkship-pylib"))
        import resvg_py
    files = [os.path.join(d, f) for d in FONT_DIRS for f in
             ("arial.ttf", "arialbd.ttf", "ariali.ttf", "georgia.ttf", "georgiab.ttf")
             if os.path.exists(os.path.join(d, f))]
    png = resvg_py.svg_to_bytes(svg_string=svg, font_files=files or None,
                                sans_serif_family="Arial" if files else None)
    out.write_bytes(bytes(png))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--out", type=Path, help="where the SVG goes")
    ap.add_argument("--png", type=Path, help="write a preview PNG here")
    args = ap.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    chart = Chart(spec)
    svg = chart.build()
    for w in chart.warnings:
        LOG.warning("warning: %s", w)
    for e in chart.errors:
        LOG.error("ERROR: %s", e)
    if args.out:
        args.out.write_text(svg, encoding="utf-8", newline="\n")
        LOG.info("wrote %s", args.out)
    if args.png:
        render_png(svg, args.png)
        LOG.info("preview %s", args.png)
    return 1 if chart.errors else 0


if __name__ == "__main__":
    sys.exit(main())
