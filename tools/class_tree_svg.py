# -*- coding: utf-8 -*-
"""Draw a drug-class tree (root -> classes -> drug cards) as a standalone SVG.

Purpose: turn a small JSON spec into the three-column class tree used in the
         lecture-note charts, as vector text rather than a screenshot.
Author:  Noor Simsam
Date:    2026-10-09
Input:   a spec in tools/class_trees/<name>.json
Output:  an .svg written where --out says (normally the vault's Attachments)

Text in an SVG does not wrap, so every line break is decided here, by
measuring words in the font the reader will most likely see: Arial for the
body, Georgia for the class titles. Both ship with Windows and macOS. Where
they are missing the browser substitutes a face of similar width, and WRAP
leaves room for that.

Spec shape:

    {"title": "...", "root": "...",
     "legend": [{"chip": "Ca²⁺ ↓", "kind": "bad", "label": "lowers serum calcium"}],
     "groups": [{"title": "...", "desc": "...", "color": "vitd",
                 "sections": [{"subhead": "optional", "drugs": [
                     {"name": "...", "star": true, "agents": "...", "moa": "...",
                      "chips": [["SC daily", "plain"], ["Ca²⁺ ↑", "warn"]],
                      "lines": [{"label": "Avoid:", "text": "...", "kind": "bad"}]}]}],
                 "after": [{"label": "Too much:", "text": "...", "kind": "bad"}]}]}
"""

import argparse
import io
import json
import logging
import os
import sys
from xml.sax.saxutils import escape

from PIL import ImageFont

LOG = logging.getLogger("class_tree_svg")

FONT_DIRS = ["/mnt/c/Windows/Fonts", "C:/Windows/Fonts", "/Library/Fonts",
             "/usr/share/fonts/truetype/msttcorefonts"]
FONT_FILES = {"reg": "arial.ttf", "bold": "arialbd.ttf", "title": "georgiab.ttf"}
FALLBACK = {"reg": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "title": "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"}
SANS = "Arial, 'Segoe UI Symbol', 'Liberation Sans', Helvetica, sans-serif"
SERIF = "Georgia, 'DejaVu Serif', serif"

# Lines are filled to this share of the measured width, so a substitute face
# a few percent wider than Arial still fits inside its card.
WRAP = 0.93

WIDTH = 1120
PAD = 24
GAP = 18
RAIL = 14                     # rail sits this far in from the column edge
INDENT = 28                   # cards start this far in

PALETTE = {
    "bg": "#f6f7f9", "surface": "#ffffff", "ink": "#18212e", "muted": "#5a6577",
    "line": "#c9d0db", "accent": "#1f5f9e",
    "bad": "#b3261e", "bad_soft": "#fbe5e3", "ok": "#2f7d5b", "ok_soft": "#e2f2ea",
    "warn": "#a45a12", "warn_soft": "#fbeedd",
}
GROUP_COLORS = {
    "vitd": ("#9a6a00", "#fbf1d6"), "anti": ("#1f6f8b", "#e0f0f5"),
    "ana": ("#6a4aa8", "#eee8f8"), "sens": ("#2f7d5b", "#e2f2ea"),
    "secr": ("#a45a12", "#fbeedd"), "abs": ("#6a4aa8", "#eee8f8"),
}
CHIP = {   # kind -> (fill, text, border)
    "plain": (PALETTE["bg"], PALETTE["muted"], PALETTE["line"]),
    "good": (PALETTE["ok_soft"], PALETTE["ok"], None),
    "bad": (PALETTE["bad_soft"], PALETTE["bad"], None),
    "warn": (PALETTE["warn_soft"], PALETTE["warn"], None),
}
LINE_KIND = {"bad": PALETTE["bad"], "ok": PALETTE["ok"], "muted": PALETTE["muted"],
             "ink": PALETTE["ink"]}

_fonts = {}


def font(style, size):
    """The measuring font for a style at a size, Windows faces first."""
    key = (style, size)
    if key not in _fonts:
        path = next((os.path.join(d, FONT_FILES[style]) for d in FONT_DIRS
                     if os.path.exists(os.path.join(d, FONT_FILES[style]))),
                    FALLBACK[style])
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


def measure(text, style, size, spacing=0.0):
    return font(style, size).getlength(text) + spacing * len(text)


def wrap(runs, width, size):
    """Greedy-wrap styled runs [(text, style, colour)] into lines of runs."""
    words = []
    for text, style, colour in runs:
        for w in text.split(" "):
            if w:
                words.append((w, style, colour))
    lines, cur, cur_w = [], [], 0.0
    limit = width * WRAP
    for w, style, colour in words:
        sep = " " if cur else ""
        add = measure(sep + w, style, size)
        if cur and cur_w + add > limit:
            lines.append(cur)
            cur, cur_w, sep = [], 0.0, ""
            add = measure(w, style, size)
        if cur and cur[-1][1] == style and cur[-1][2] == colour:
            cur[-1] = (cur[-1][0] + sep + w, style, colour)
        else:
            cur.append((sep + w, style, colour))
        cur_w += add
    if cur:
        lines.append(cur)
    return lines


class Svg(object):
    def __init__(self):
        self.parts = []

    def rect(self, x, y, w, h, fill, stroke=None, rx=10, sw=1.5, dash=None):
        s = ' stroke="%s" stroke-width="%s"' % (stroke, sw) if stroke else ""
        d = ' stroke-dasharray="%s"' % dash if dash else ""
        self.parts.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" '
                          'fill="%s"%s%s/>' % (x, y, w, h, rx, fill, s, d))

    def line(self, x1, y1, x2, y2, colour=PALETTE["line"], sw=2):
        self.parts.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" '
                          'stroke-width="%s"/>' % (x1, y1, x2, y2, colour, sw))

    def text_lines(self, x, y, lines, size, lh, family=SANS, anchor="start",
                   spacing=None):
        """Draw wrapped lines; y is the top of the first line. Returns the height."""
        ls = ' letter-spacing="%s"' % spacing if spacing else ""
        for i, runs in enumerate(lines):
            base = y + i * lh + size * 0.95 + (lh - size) / 2.0 - 1
            spans = "".join(
                '<tspan font-weight="%s" fill="%s">%s</tspan>'
                % ("700" if style in ("bold", "title") else "400", colour, escape(t))
                for t, style, colour in runs)
            self.parts.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" '
                              'text-anchor="%s"%s>%s</text>'
                              % (x, base, family, size, anchor, ls, spans))
        return len(lines) * lh

    def chips(self, x, y, width, chips, size=11.5):
        """Lay out pill chips left to right, wrapping. Returns the height used."""
        h, padx, gap = 20, 7, 4
        cx, cy = x, y
        for text, kind in chips:
            fill, fg, border = CHIP.get(kind, CHIP["plain"])
            w = measure(text, "bold", size) / WRAP + 2 * padx
            if cx > x and cx + w > x + width:
                cx, cy = x, cy + h + gap
            self.rect(cx, cy, w, h, fill, border, rx=10, sw=1)
            self.parts.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" '
                              'font-weight="700" fill="%s" text-anchor="middle">%s</text>'
                              % (cx + w / 2, cy + 14, SANS, size, fg, escape(text)))
            cx += w + gap
        return cy + h - y


def line_runs(item, base_colour):
    colour = LINE_KIND.get(item.get("kind", "muted"), base_colour)
    runs = []
    if item.get("label"):
        runs.append((item["label"], "bold", colour))
        runs.append((" " + item["text"], "reg", colour))
    else:
        runs.append((item["text"], "reg", colour))
    return runs


def draw_card(svg, x, y, w, drug, dry=False):
    """One drug card. Returns its height; draws only when dry is False."""
    inner = w - 24
    target = Svg() if dry else svg
    parts_at = len(target.parts)
    cy = y + 10
    name = [(drug["name"], "bold", PALETTE["ink"])]
    if drug.get("star"):
        name.insert(0, ("★ ", "bold", PALETTE["accent"]))
    cy += target.text_lines(x + 12, cy, wrap(name, inner, 14.5), 14.5, 20)
    if drug.get("agents"):
        cy += target.text_lines(x + 12, cy, wrap([(drug["agents"], "reg", PALETTE["muted"])],
                                                 inner, 12.5), 12.5, 17)
    if drug.get("moa"):
        cy += 5
        cy += target.text_lines(x + 12, cy, wrap([(drug["moa"], "reg", PALETTE["ink"])],
                                                 inner, 13.5), 13.5, 19)
    if drug.get("chips"):
        cy += 7
        cy += target.chips(x + 12, cy, inner, drug["chips"])
    for item in drug.get("lines", []):
        cy += 6
        cy += target.text_lines(x + 12, cy, wrap(line_runs(item, PALETTE["bad"]), inner, 12.5),
                                12.5, 17)
    height = cy + 10 - y
    if not dry:
        # the card's box goes under the text already drawn
        svg.parts.insert(parts_at, '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="10" '
                         'fill="%s" stroke="%s" stroke-width="1.5"/>'
                         % (x, y, w, height, PALETTE["surface"], PALETTE["line"]))
    return height


def draw_group(svg, x, y, w, group):
    """Class header, then its drug cards on a rail. Returns the bottom y."""
    colour, soft = GROUP_COLORS[group["color"]]
    head_lines = wrap([(group["title"], "title", colour)], w - 28, 18)
    desc_lines = wrap([(group.get("desc", ""), "reg", PALETTE["ink"])], w - 28, 13)
    head_h = 12 + len(head_lines) * 24 + len(desc_lines) * 18 + 12
    svg.rect(x, y, w, head_h, soft, colour, rx=10)
    cy = y + 12
    cy += svg.text_lines(x + 14, cy, head_lines, 18, 24, family=SERIF)
    svg.text_lines(x + 14, cy, desc_lines, 13, 18)
    cy = y + head_h + 10

    rail_x = x + RAIL
    rail_top = cy - 10
    last_tick = rail_top
    for section in group["sections"]:
        if section.get("subhead"):
            cy += 4
            lines = wrap([(section["subhead"].upper(), "bold", colour)], w - INDENT, 11.5)
            cy += svg.text_lines(x + RAIL, cy, lines, 11.5, 16, spacing="0.06em")
            cy += 4
        for drug in section["drugs"]:
            h = draw_card(svg, x + INDENT, cy, w - INDENT, drug)
            svg.line(rail_x, cy + 20, x + INDENT, cy + 20)
            last_tick = cy + 20
            cy += h + 10
    svg.line(rail_x, rail_top, rail_x, last_tick)
    for item in group.get("after", []):
        cy += 2
        cy += svg.text_lines(x + RAIL, cy, wrap(line_runs(item, PALETTE["muted"]),
                                                w - RAIL, 12.5), 12.5, 17)
    return cy


def draw_legend(svg, x, y, width, legend):
    """Chip + label pairs across the top. Returns the height."""
    cx, cy, h = x, y, 20
    for item in legend:
        fill, fg, border = CHIP.get(item["kind"], CHIP["plain"])
        cw = measure(item["chip"], "bold", 11.5) / WRAP + 14
        lw = measure(item["label"], "reg", 12.5) / WRAP
        if cx > x and cx + cw + 6 + lw > x + width:
            cx, cy = x, cy + h + 6
        svg.rect(cx, cy, cw, h, fill, border, rx=10, sw=1)
        svg.parts.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="11.5" '
                         'font-weight="700" fill="%s" text-anchor="middle">%s</text>'
                         % (cx + cw / 2, cy + 14, SANS, fg, escape(item["chip"])))
        svg.parts.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="12.5" '
                         'fill="%s">%s</text>'
                         % (cx + cw + 6, cy + 14.5, SANS, PALETTE["muted"],
                            escape(item["label"])))
        cx += cw + 6 + lw + 16
    return cy + h - y


def build(spec):
    svg = Svg()
    y = PAD
    if spec.get("legend"):
        y += draw_legend(svg, PAD, y, WIDTH - 2 * PAD, spec["legend"]) + 18

    root_w = measure(spec["root"], "bold", 15) / WRAP + 36
    root_x = (WIDTH - root_w) / 2
    svg.rect(root_x, y, root_w, 40, PALETTE["ink"], rx=10)
    svg.parts.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="15" '
                     'font-weight="700" fill="%s" text-anchor="middle">%s</text>'
                     % (WIDTH / 2, y + 25.5, SANS, PALETTE["bg"], escape(spec["root"])))
    y += 40

    n = len(spec["groups"])
    colw = (WIDTH - 2 * PAD - (n - 1) * GAP) / float(n)
    centres = [PAD + i * (colw + GAP) + colw / 2 for i in range(n)]
    bar = y + 22
    svg.line(WIDTH / 2, y, WIDTH / 2, bar)
    svg.line(centres[0], bar, centres[-1], bar)
    for c in centres:
        svg.line(c, bar, c, bar + 22)
    top = bar + 22

    bottom = top
    for i, group in enumerate(spec["groups"]):
        bottom = max(bottom, draw_group(svg, PAD + i * (colw + GAP), top, colw, group))
    height = int(bottom + PAD)

    head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d" role="img" aria-labelledby="t">'
            '<title id="t">%s</title>'
            '<rect width="100%%" height="100%%" rx="14" fill="%s"/>'
            % (WIDTH, height, WIDTH, height, escape(spec["title"]), PALETTE["bg"]))
    body = "\n".join(p for p in svg.parts if p)
    return head + "\n" + body + "\n</svg>\n", height


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", help="tools/class_trees/<name>.json")
    ap.add_argument("--out", required=True, help="where to write the .svg")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    spec = json.load(io.open(args.spec, encoding="utf-8"))
    text, height = build(spec)
    io.open(args.out, "w", encoding="utf-8", newline="\n").write(text)
    LOG.info("%s -> %s  %dx%d  %.0f KB", args.spec, args.out, WIDTH, height,
             len(text.encode("utf-8")) / 1024.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
