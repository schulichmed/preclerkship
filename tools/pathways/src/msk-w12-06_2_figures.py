# -*- coding: utf-8 -*-
"""
Cranial Nerve Anatomy and Function (msk-w12-06_2): one annotated picture per column of the
interactive chart, a red ring and label on exactly what is wrong in each photo.

Purpose: the column pictures on pom2/charts/msk-w12-06_2/, as the Rheumatology
         Investigations page has, but from the lecture's own slides (used with permission).
Input:   --pdf  the "Symptoms of Cranial Nerve Pathology" deck (Shoesmith, Asynch W12)
         --repo the preclerkship checkout
Output:  pom2/charts/img/msk-w12-06_2/<column id>.jpg and their rows in
         pom2/charts/figures.json (merged in place; other charts' rows untouched)

Pictures (page, image index): p6 i0 normal fundus, p6 i1 B papilledema, p10 left abducens
palsy (middle row), p11 complete left third nerve palsy, p12 right trochlear palsy (bottom
row), p13 right Horner's, p15 zoster V1 + V3, p18 UMN and LMN facial weakness, p24 wasted
half tongue. Sides follow the module's answers and were checked on the photos.
IX + X and XI have no pathology photo in the deck, so their columns have none.
"""
import argparse
import io
import json
import sys
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402

CHART = "msk-w12-06_2"
RED = (214, 39, 40)
W = 720            # every photo is scaled to this width before it is marked
LABEL = 46         # label text size at W: about 10 px when the column shows it
PIC_H = 210        # px the column shows each picture at (chart.js reads "h")
CREDIT = {"author": "C. Shoesmith, Symptoms of Cranial Nerve Pathology (PoM 2 lecture slides)",
          "licence": "used with permission, red marks added"}


def grab(doc, page, idx, box=None):
    xref = doc[page - 1].get_images(full=True)[idx][0]
    im = Image.open(io.BytesIO(doc.extract_image(xref)["image"])).convert("RGB")
    return im.crop(box) if box else im


def mark(im, rings=(), labels=()):
    """Scale to W, then draw red rings ((cx, cy, rx, ry) in source px) and labels
    ((text, x, y) in source px, the label's top-left; y < 0 counts from the bottom)."""
    k = W / im.width
    im = im.resize((W, round(im.height * k)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    for cx, cy, rx, ry in rings:
        d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k], outline=RED, width=10)
    f = ps.font("bold", LABEL)
    for text, x, y in labels:
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        x = min(max(4, x * k), W - (r - l) - 20)
        y = y * k if y >= 0 else im.height + y * k - (b - t) - 14
        d.rounded_rectangle([x, y, x + r - l + 16, y + b - t + 14], radius=8, fill=RED)
        d.text((x + 8 - l, y + 7 - t), text, font=f, fill="white")
    return im


def stack(ims, gap=8):
    """Pictures one above another, each at width W, with a white gap."""
    out = Image.new("RGB", (W, sum(i.height for i in ims) + gap * (len(ims) - 1)), "white")
    y = 0
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + gap
    return out


def side(ims, gap=8):
    """Pictures side by side at a shared height, scaled back to width W."""
    h = min(i.height for i in ims)
    ims = [i.resize((round(i.width * h / i.height), h), Image.LANCZOS) for i in ims]
    out = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), h), "white")
    x = 0
    for i in ims:
        out.paste(i, (x, 0))
        x += i.width + gap
    return out.resize((W, round(out.height * W / out.width)), Image.LANCZOS)


def figures(pdf):
    """{column id: (picture, caption)}."""
    doc = pymupdf.open(pdf)
    cn3 = mark(grab(doc, 11, 0), rings=[(352, 148, 62, 50), (330, 462, 70, 38)],
               labels=[("big pupil, down + out", 120, 230), ("lid shut", 120, 535)])
    horner = mark(grab(doc, 13, 0), rings=[(68, 70, 62, 38)], labels=[("Horner's: small pupil", 150, 2)])
    cn4 = mark(grab(doc, 12, 0, (535, 360, 800, 545)), rings=[(82, 142, 38, 28)],
               labels=[("CN IV: looks down-left", 4, 4), ("R eye stays up", 4, -4)])
    cn6 = mark(grab(doc, 10, 0, (805, 265, 1200, 520)), rings=[(300, 160, 70, 48)],
               labels=[("CN VI: looks left", 4, 4), ("L eye stuck", 4, -4)])
    v1 = mark(grab(doc, 15, 0), rings=[(180, 95, 75, 65)], labels=[("V1", 8, -4)])
    v3 = mark(grab(doc, 15, 1), rings=[(420, 320, 130, 95)], labels=[("V3", 8, -4)])
    umn = mark(grab(doc, 18, 2), rings=[(110, 117, 36, 17)],
               labels=[("UMN: forehead spared", 4, 2), ("lower face droops", 4, -2)])
    lmn = side([mark(grab(doc, 18, 0), rings=[(100, 150, 28, 18)], labels=[("mouth flat", 4, -2)]),
                mark(grab(doc, 18, 1), rings=[(106, 100, 26, 18)], labels=[("eye rolls up", 4, -2)])])
    lmn_head = Image.new("RGB", (W, 64), RED)
    ImageDraw.Draw(lmn_head).text((12, 8), "LMN (Bell's): whole half face", font=ps.font("bold", LABEL), fill="white")
    tongue = mark(grab(doc, 24, 0), rings=[(640, 450, 200, 330)], labels=[("patient's L half wasted", 30, 30)])
    normal = mark(grab(doc, 6, 0), labels=[("normal", 6, -4)])
    papill = mark(grab(doc, 6, 1, (545, 0, 1089, 475)), rings=[(240, 225, 120, 120)],
                  labels=[("papilledema", 6, -4)])
    return {
        "cn3": (stack([cn3, horner]),
                "Left CN III palsy: big pupil, eye down and out, lid shut. Below, the look-alike: right Horner's, a SMALL pupil"),
        "cn4_6": (stack([cn4, cn6]),
                  "Right CN IV palsy: looking down to his left, the right eye stays up. Left CN VI palsy: the left eye cannot look out"),
        "cn5": (stack([v1, v3]), "Shingles in CN V1 (forehead, stops at the midline) and in V3 (jaw and lower lip)"),
        "cn7": (stack([umn, lmn_head, lmn], gap=0),
                "CN VII. UMN (stroke): forehead spared. LMN (Bell's): the whole half face, and the eye rolls up when it cannot close"),
        "cn12": (tongue, "LMN CN XII lesion: the patient's left half of the tongue is wasted and wrinkled"),
        "cn1_2_8": (stack([normal, papill]), "CN II: a normal disc with a sharp edge, then papilledema, the disc swollen and blurred"),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--pdf", type=Path, required=True)
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    args = ap.parse_args()
    out = args.repo / "pom2/charts/img" / CHART
    out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for col, (im, caption) in figures(args.pdf).items():
        im.save(out / f"{col}.jpg", quality=82, optimize=True)
        rows[col] = {"file": f"{col}.jpg", "caption": caption, "h": PIC_H, **CREDIT}
        print("wrote", out / f"{col}.jpg", im.size)
    path = args.repo / "pom2/charts/figures.json"
    raw = path.read_text(encoding="utf-8")
    manifest = json.loads(raw)
    manifest[CHART] = rows
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(manifest, ensure_ascii=False, indent=1) + ("\n" if raw.endswith("\n") else ""))
    print("figures.json:", CHART, len(rows), "pictures")


if __name__ == "__main__":
    main()
