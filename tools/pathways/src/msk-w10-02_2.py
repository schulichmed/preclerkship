# -*- coding: utf-8 -*-
"""
Purpose: Draw the lower extremity radiology overview: a visual map of the lecture's own
         X-rays, read joint by joint (hip -> knee -> ankle -> osteoarthritis).
Author:  Noor Simsam
Date:    2026-10-31
Input:   the X-ray images already in the vault's Attachments folder (--attachments)
Output:  an SVG with the crops embedded as JPEG data URIs (--out), optional PNG preview (--png)

Same layout as the upper extremity overview (msk-w9-02_2.py): a root card, then one coloured
band per joint, each row a standard view or a finding, with the film above its caption.
The note has no deck behind it yet, so every line comes from the lecture note itself.

    python3 tools/pathways/src/msk-w10-02_2.py --attachments "<vault>/Attachments" \
        --out "<vault>/Attachments/lower extremity radiology overview.svg" --png /tmp/p.png
"""

import argparse
import base64
import io
import logging
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402
from column_pathway import PALETTE  # noqa: E402

LOG = logging.getLogger("lower_extremity_radiology")

WIDTH = 1240
MARGIN = 16
RAIL_X = 30                 # the left rail that feeds every band
BAND_X = 52
BAND_W = WIDTH - BAND_X - MARGIN
GAP = 14                    # between cards, and inside a band
CARD_PAD = 10
MAX_IMG_H = 300
EMBED_W = 640               # embedded pixel width: zoomable, without a 5 MB file
JPEG_Q = 72
RUN = 12                    # film columns in a row that end a white border
FIT = 0.88                  # wrap short of the box: a substitute face runs wider than Arial
HEADER_H = 34


# key -> (file, crop box as fractions of the image). A list of entries is set side by side.
# Each normal film is a plain | labelled pair: the labelled half is kept, minus the logo in its
# corner (bottom-left, or top-left on the hip lateral) and the knee OA footer.
CROPS = {
    "hip_ap": ("x-ray normal hip (AP view).png", (0.5, 0, 1, 0.91)),
    "pelvis": ("x-ray normal pelvis (AP view).png", (0.5, 0, 1, 1)),
    "hip_lat": ("x-ray normal hip (lateral).png", (0.5, 0.12, 1, 1)),
    "hip_oa": ("hip osteoarthritis x-ray.png", (0, 0, 1, 1)),
    "hip_fx": ("types of hip fractures (x-rays).png", (0, 0, 1, 1)),
    "knee_ap": ("x-ray normal knee (AP view).png", (0.5, 0, 1, 0.91)),
    "knee_lat": ("x-ray normal knee (lateral view).png", (0.5, 0, 1, 0.91)),
    "knee_oa": ("x-ray of knee osteoarthritis.png", (0, 0, 1, 0.94)),
    "ankle_ap": ("x-ray normal ankle (AP view).png", (0.5, 0, 1, 0.91)),
    "ankle_lat": ("x-ray normal ankle (lateral view).png", (0.5, 0, 1, 0.91)),
    "ankle_mortise": ("x-ray normal ankle (mortise view).png", (0.5, 0, 1, 0.91)),
    "weber": ("Weber ankle fracture types A B C - x-rays.jpg", (0, 0, 1, 1)),
    "medial": [("medial malleolus fracture x-ray (chip fracture).png", (0, 0, 1, 1)),
               ("medial malleolus fracture x-ray (transverse fracture).png", (0, 0, 1, 1)),
               ("medial malleolus fracture x-ray (vertical fracture).png", (0, 0, 1, 1)),
               ("medial malleolus fracture x-ray (comminuted fracture).png", (0, 0, 1, 1))],
    "bimalleolar": ("bimalleolar fracture.png", (0, 0, 1, 1)),
    "trimalleolar": ("trimalleolar fracture.png", (0, 0, 1, 1)),
}

INK, MUTED = ps.P["ink"], ps.P["muted"]
BAD = ps.P["bad"]

# A card: title, picture (or None), lines. "• " lines hang-indent; **x** is bold.
ROOT = {
    "title": "Each joint: a standard pair of views, plus one extra for a specific question",
    "img": None,
    "lines": [
        "• **Hip**: AP · cross-table lateral, **+ AP pelvis** to compare the two sides",
        "• **Knee**: AP · lateral, **+ tunnel, skyline or standing** when the differential needs it",
        "• **Ankle**: AP · lateral, **+ mortise** to open up the tibiofibular syndesmosis",
        "• Osteoarthritis looks the same at every joint · a fracture is named by where it sits",
    ],
}

BANDS = [
    {"name": "HIP", "colour": "teal", "rows": [
        {"label": "STANDARD VIEWS: AP hip · AP pelvis · cross-table lateral", "cards": [
            {"title": "AP hip", "img": "hip_ap", "lines": [
                "• The standard front-to-back view"]},
            {"title": "AP pelvis", "img": "pelvis", "lines": [
                "• Ordered **alongside** a hip X-ray to check for **asymmetry** between the two sides"]},
            {"title": "Cross-table lateral", "img": "hip_lat", "lines": [
                "• Femoral head in the acetabulum · neck · greater and lesser trochanter · femoral shaft"]},
        ]},
        {"label": "FINDINGS: FRACTURE", "cards": [
            {"title": "Hip fracture: named by where the proximal femur breaks", "img": "hip_fx",
             "kind": "bad", "wide": True, "lines": [
                "• **Femoral neck** · greater trochanter · **intertrochanteric** · subtrochanteric"]},
        ]},
    ]},
    {"name": "KNEE", "colour": "purple", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral", "cards": [
            {"title": "AP", "img": "knee_ap", "lines": [
                "• The standard front-to-back view"]},
            {"title": "Lateral", "img": "knee_lat", "lines": [
                "• The second standard view"]},
            {"title": "Extra views", "img": None, "lines": [
                "• **Tunnel** · **skyline** · **standing**",
                "• Added only when the differential needs them"]},
        ]},
    ]},
    {"name": "ANKLE", "colour": "orange", "rows": [
        {"label": "STANDARD VIEWS: AP · lateral · mortise", "cards": [
            {"title": "AP", "img": "ankle_ap", "lines": [
                "• The tibia and fibula **overlap** at the syndesmosis"]},
            {"title": "Lateral", "img": "ankle_lat", "lines": [
                "• The second standard view"]},
            {"title": "Mortise", "img": "ankle_mortise", "lines": [
                "• **Opens up the tibiofibular syndesmosis**, a full view of the joint"]},
        ]},
        {"label": "FINDINGS: LATERAL MALLEOLUS, graded by Weber type", "cards": [
            {"title": "Weber: the fibular break against the syndesmosis", "img": "weber",
             "kind": "bad", "wide": True, "lines": [
                "• **A: below** · usually stable if the medial malleolus is intact · boot + crutches 6 weeks, weight-bear as tolerated",
                "• **B: at** · variable, depends on the medial malleolus and deltoid ligament · surgery if unstable",
                "• **C: above** · unstable, often with a bimalleolar fracture or deltoid injury · usually surgery",
                "• **Maisonneuve** (high fibula) counts as **Weber C**"]},
        ]},
        {"label": "FINDINGS: MEDIAL, BI- AND TRIMALLEOLAR", "cards": [
            {"title": "Medial malleolus: chip · transverse · vertical · comminuted", "img": "medial",
             "kind": "bad", "wide": True, "lines": [
                "• **Chip** = an avulsion: the deltoid ligament pulls off a flake of bone as it ruptures",
                "• **Comminuted** = several pieces, usually high-energy trauma"]},
            {"title": "Bimalleolar", "img": "bimalleolar", "kind": "bad", "lines": [
                "• **Lateral + medial** malleolus"]},
            {"title": "Trimalleolar", "img": "trimalleolar", "kind": "bad", "wide": True, "lines": [
                "• Both malleoli **+ the back of the distal tibia**",
                "• No stable bony link between leg and foot: **the ankle dislocates**"]},
        ]},
    ]},
    {"name": "OSTEOARTHRITIS", "colour": "brown", "rows": [
        {"label": "SAME 4 SIGNS AT EVERY JOINT", "cards": [
            {"title": "The four signs", "img": None, "lines": [
                "1 · **Loss of joint space**",
                "2 · **Osteophytes**",
                "3 · **Subchondral cysts**",
                "4 · **Subchondral sclerosis**"]},
            {"title": "Hip", "img": "hip_oa", "lines": [
                "• Joint space narrowing and osteophytes, including one on the femoral head"]},
            {"title": "Knee", "img": "knee_oa", "lines": [
                "• The same four signs at the knee"]},
        ]},
    ]},
]


def load_crops(folder: Path) -> dict:
    """Crop every picture out of the vault's Attachments, keyed as in CROPS."""

    def crop(entry: tuple) -> Image.Image:
        name, (a, b, c, d) = entry
        im = Image.open(folder / name).convert("RGB")
        w, h = im.size
        return im.crop((int(a * w), int(b * h), int(c * w), int(d * h)))

    return {key: side_by_side([crop(e) for e in src]) if isinstance(src, list) else crop(src)
            for key, src in CROPS.items()}


def side_by_side(ims: list) -> Image.Image:
    """Films at one height in a row, on black with a thin gap."""
    h = min(im.height for im in ims)
    ims = [im.resize((round(im.width * h / im.height), h)) for im in ims]
    gap = 6
    row = Image.new("RGB", (sum(im.width for im in ims) + gap * (len(ims) - 1), h), "black")
    x = 0
    for im in ims:
        row.paste(im, (x, 0))
        x += im.width + gap
    return row


def trim_white(im: Image.Image) -> Image.Image:
    """Drop the white slide background (and any thin divider in it) left at a crop's edges:
    each edge moves in to the first run of RUN columns or rows that are all film."""
    grey = im.convert("L")
    w, h = grey.size
    px = grey.load()
    col = [sum(px[x, y] for y in range(0, h, 4)) / len(range(0, h, 4)) for x in range(w)]
    row = [sum(px[x, y] for x in range(0, w, 4)) / len(range(0, w, 4)) for y in range(h)]

    def first_film(means: list) -> int:
        for i in range(len(means) - RUN):
            if all(m < 215 for m in means[i:i + RUN]):
                return i
        return 0

    left, top = first_film(col), first_film(row)
    right, bottom = w - first_film(col[::-1]), h - first_film(row[::-1])
    return im.crop((left, top, right, bottom))


def data_uri(im: Image.Image) -> str:
    """A JPEG data URI no wider than EMBED_W."""
    im = im.copy()
    im.thumbnail((EMBED_W, EMBED_W * 3))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=JPEG_Q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def words(line: str) -> list:
    """Split a line into words, each a list of (text, is_bold) segments on **markers**,
    so "**neck**:" stays one word with no space before the colon."""
    out, cur = [], []
    for i, part in enumerate(line.split("**")):
        bold = i % 2 == 1
        for j, chunk in enumerate(part.split(" ")):
            if j:
                if cur:
                    out.append(cur)
                cur = []
            if chunk:
                cur.append((chunk, bold))
    if cur:
        out.append(cur)
    return out


def word_width(word: list) -> float:
    return sum(ps.measure(t, "bold" if b else "reg", ps.BODY_SIZE) for t, b in word)


def wrap_rich(line: str, width: float) -> list:
    """Greedy wrap of a **bold**-marked line; returns lines as lists of words."""
    width *= FIT
    lines, cur, cur_w = [], [], 0.0
    space = ps.measure(" ", "reg", ps.BODY_SIZE)
    for w in words(line):
        ww = word_width(w)
        if cur and cur_w + space + ww > width:
            lines.append(cur)
            cur, cur_w = [], 0.0
        cur_w += (space if cur else 0) + ww
        cur.append(w)
    if cur:
        lines.append(cur)
    return lines


def text_block(lines: list, x: float, y: float, width: float,
               ink: str = INK, muted_ink: str = MUTED) -> tuple:
    """SVG for a list of card lines, starting at baseline y. Returns (svg, height)."""
    svg, h = [], 0
    for line in lines:
        item = ps.LIST_ITEM.match(line)
        indent = ps.measure(item.group(1), "reg", ps.BODY_SIZE) if item else 0
        muted = line.startswith("(")
        for k, seg in enumerate(wrap_rich(line, width - indent)):
            sx = x + (indent if k else 0)
            spans = []
            for j, w in enumerate(seg):
                for t, b in w:
                    spans.append(f'<tspan font-weight="bold">{escape(t)}</tspan>' if b else escape(t))
                if j < len(seg) - 1:
                    spans.append(" ")
            fill = muted_ink if muted else ink
            style = ' font-style="italic"' if muted else ""
            svg.append(f'<text x="{sx:.1f}" y="{y + h:.1f}" font-size="{ps.BODY_SIZE}" '
                       f'fill="{fill}"{style} xml:space="preserve">{"".join(spans)}</text>')
            h += ps.BODY_STEP
    return svg, h


def card_size(card: dict, w: float, crops: dict) -> tuple:
    """(image box w, image box h, text height) for a card of width w."""
    inner = w - 2 * CARD_PAD
    iw = ih = 0
    if card.get("img"):
        im = crops[card["img"]]
        iw, ih = inner, inner * im.height / im.width
        if ih > MAX_IMG_H:
            iw, ih = MAX_IMG_H * im.width / im.height, MAX_IMG_H
    _, th = text_block(card["lines"], 0, 0, inner)
    return iw, ih, th


def draw_card(card: dict, x: float, y: float, w: float, h: float, colour: str, crops: dict) -> list:
    strong, soft, _ = PALETTE[colour]
    edge = BAD if card.get("kind") == "bad" else strong
    svg = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="8" '
           f'fill="#ffffff" stroke="{edge}" stroke-width="1.6"/>']
    title = escape(card["title"])
    svg.append(f'<text x="{x + CARD_PAD:.1f}" y="{y + CARD_PAD + 14:.1f}" font-size="{ps.TITLE_SIZE}" '
               f'font-weight="bold" fill="{edge}">{title}</text>')
    cy = y + CARD_PAD + 24
    iw, ih, _ = card_size(card, w, crops)
    if card.get("img"):
        ix = x + (w - iw) / 2
        svg.append(f'<rect x="{ix:.1f}" y="{cy:.1f}" width="{iw:.1f}" height="{ih:.1f}" fill="#000"/>')
        svg.append(f'<image x="{ix:.1f}" y="{cy:.1f}" width="{iw:.1f}" height="{ih:.1f}" '
                   f'preserveAspectRatio="xMidYMid meet" href="{data_uri(crops[card["img"]])}"/>')
        cy += ih + 8
    body, _ = text_block(card["lines"], x + CARD_PAD, cy + 13, w - 2 * CARD_PAD)
    return svg + body


def card_widths(cards: list, total: float, crops: dict) -> list:
    """Share a row's width: a picture-less card takes less, a "wide" film takes more."""
    weight = [0.7 if not c.get("img") else 1.6 if c.get("wide") else 1.0 for c in cards]
    if len(cards) == 1:
        return [min(total, 520)]
    free = total - GAP * (len(cards) - 1)
    return [free * wt / sum(weight) for wt in weight]


def arrow(x1: float, y1: float, x2: float, y2: float, colour: str = MUTED) -> str:
    """A straight arrow; each colour has its own solid head, defined in main()."""
    return (f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" stroke="{colour}" stroke-width="1.8" '
            f'fill="none" marker-end="url(#ah{colour[1:]})"/>')


def build(crops: dict) -> tuple:
    """The whole SVG body and its height."""
    svg = []
    y = MARGIN

    # the root: the systematic read, its text beside the bone-parts film
    rw = WIDTH - 2 * MARGIN
    im = crops[ROOT["img"]] if ROOT["img"] else None
    img_w = 360 if im else 0
    img_h = img_w * im.height / im.width if im else 0
    _, th = text_block(ROOT["lines"], 0, 0, rw - img_w - 3 * CARD_PAD - 14)
    rh = max(img_h, th + 30) + 2 * CARD_PAD
    svg.append(f'<rect x="{MARGIN}" y="{y}" width="{rw}" height="{rh:.1f}" rx="10" fill="{INK}"/>')
    if im:
        svg.append(f'<image x="{WIDTH - MARGIN - img_w - CARD_PAD}" y="{y + CARD_PAD}" width="{img_w}" '
                   f'height="{img_h:.1f}" href="{data_uri(im)}"/>')
    svg.append(f'<text x="{MARGIN + 14}" y="{y + CARD_PAD + 18}" font-size="17" font-weight="bold" '
               f'fill="#ffffff">{escape(ROOT["title"])}</text>')
    svg += text_block(ROOT["lines"], MARGIN + 14, y + CARD_PAD + 44, rw - img_w - 3 * CARD_PAD - 14,
                      ink="#ffffff", muted_ink="#cfd6e0")[0]
    y += rh
    rail_top = y
    y += 26

    band_heads = []
    for band in BANDS:
        strong, soft, tint = PALETTE[band["colour"]]
        top = y
        parts = []
        cy = top + HEADER_H + GAP
        prev_bottom = None
        for row in band["rows"]:
            label_x = BAND_X + GAP
            if prev_bottom is not None:
                parts.append(arrow(label_x + 6, prev_bottom + 2, label_x + 6, cy + 2, strong))
                cy += 12
            parts.append(f'<text x="{label_x + 18}" y="{cy + 13}" font-size="12.5" font-weight="bold" '
                         f'letter-spacing="0.6" fill="{strong}">{escape(row["label"])}</text>')
            cy += 22
            if row.get("note"):
                parts.append(f'<text x="{label_x + 18}" y="{cy + 10}" font-size="12" font-style="italic" '
                             f'fill="{MUTED}">{escape(row["note"])}</text>')
                cy += 20
            cards = row["cards"]
            ws = card_widths(cards, BAND_W - 2 * GAP, crops)
            sizes = [card_size(c, w, crops) for c, w in zip(cards, ws)]
            h = max(CARD_PAD * 2 + 24 + (ih + 8 if ih else 0) + th for (_, ih, th) in sizes) + 6
            cx = BAND_X + GAP
            for c, w in zip(cards, ws):
                parts += draw_card(c, cx, cy, w, h, band["colour"], crops)
                cx += w + GAP
            prev_bottom = cy + h
            cy += h + GAP
        bh = cy - top
        svg.append(f'<rect x="{BAND_X}" y="{top}" width="{BAND_W}" height="{bh}" rx="10" fill="{tint}" '
                   f'stroke="{strong}" stroke-width="1.4"/>')
        svg.append(f'<path d="M{BAND_X},{top + HEADER_H} V{top + 10} a10,10 0 0 1 10,-10 '
                   f'H{BAND_X + BAND_W - 10} a10,10 0 0 1 10,10 V{top + HEADER_H} Z" fill="{strong}"/>')
        svg.append(f'<text x="{BAND_X + GAP}" y="{top + 23}" font-size="17" font-weight="bold" '
                   f'letter-spacing="1.5" fill="#ffffff">{band["name"]}</text>')
        svg += parts
        band_heads.append((top + HEADER_H / 2, strong))
        y = cy + 22

    # one rail down the left margin, a branch into each band's header
    last = band_heads[-1][0]
    svg.append(f'<path d="M{RAIL_X},{rail_top} V{last}" stroke="{MUTED}" stroke-width="1.8" fill="none"/>')
    for hy, _ in band_heads:
        svg.append(arrow(RAIL_X, hy, BAND_X - 2, hy))
    return svg, y - 22 + MARGIN


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--attachments", type=Path, required=True, help="the vault's Attachments folder")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--png", type=Path)
    args = ap.parse_args()

    crops = load_crops(args.attachments)
    body, height = build(crops)
    colours = [MUTED] + [PALETTE[b["colour"]][0] for b in BANDS]
    markers = "".join(f'<marker id="ah{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                      f'markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
                      for c in dict.fromkeys(colours))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'viewBox="0 0 {WIDTH} {height:.0f}" width="{WIDTH}" height="{height:.0f}" '
           f'font-family="{ps.SANS}">'
           f'<defs>{markers}</defs>'
           f'<rect width="{WIDTH}" height="{height:.0f}" fill="{ps.P["bg"]}"/>' + "".join(body) + "</svg>")
    args.out.write_text(svg, encoding="utf-8")
    LOG.info("wrote %s (%d KB, %d px tall)", args.out, len(svg) // 1024, height)
    if args.png:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(args.png), output_width=WIDTH)


if __name__ == "__main__":
    main()
