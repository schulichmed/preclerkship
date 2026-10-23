"""
Purpose: Put the FoM and PoM 1 overview charts on the portal the way PoM 2 has them: the drawn
         chart as the first figure of every lecture it covers, with an "interactive" link to its
         Look / Walk / Test page.
Author: nsimsam (with Claude Code)
Date: 2026-10-19
Input: tools/pathways/src/{fom-b*,cardio,resp,ent,gi,gu}-*.content.json, the vault's rendered
       Attachments/<name>.svg and the lecture notes that embed it, and {fom,pom1}/data/notes.
Output: {fom,pom1}/charts/<chart id>/index.html and {fom,pom1}/charts/index.html (sharing
        pom2/charts/chart.js and chart.css), {fom,pom1}/assets/figures/<md5>.svg, and a figure
        block at the top of each covered lecture in {fom,pom1}/data/notes/<block>.json.
        FoM and PoM 1 notes are curated JSON, not rebuilt from the vault, so this tool is the
        only thing that places the figure; rerun it after a chart changes. It is idempotent.

Usage: python3 tools/overview_charts_fom_pom1.py [--vault /mnt/c/Users/nsims/medwiki]
"""
import argparse
import hashlib
import json
import logging
import re
from pathlib import Path

import interactive_charts as ic

REPO = Path(__file__).resolve().parent.parent
# chart-id prefix -> (course, notes block, block name)
PREFIXES = {
    "fom-b1": ("fom", "b1", "Principles & Development"),
    "fom-b2": ("fom", "b2", "Regulation, Neoplasia & Aging"),
    "fom-b3": ("fom", "b3", "Hematology"),
    "fom-b4": ("fom", "b4", "Infection & Immunity"),
    "cardio": ("pom1", "cardio", "Cardiology"),
    "resp": ("pom1", "resp", "Respirology"),
    "ent": ("pom1", "ent", "Ear, Nose & Throat"),
    "gi": ("pom1", "gi", "Gastroenterology"),
    "gu": ("pom1", "gu", "Nephrology & Urology"),
}
VAULT_DIRS = {"fom": "99 - FoM/Block */Week */*.md", "pom1": "99 - PoM 1/*/Week */*.md"}
SVG_SIZE = re.compile(r'<svg\b[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"')
SHARED = "../../../pom2/charts/"

log = logging.getLogger("overviews")


def load_notes(course: str) -> dict:
    """block -> notes document."""
    blocks = {b for (c, b, _) in PREFIXES.values() if c == course}
    return {b: json.loads((REPO / course / "data/notes" / f"{b}.json").read_text()) for b in blocks}


def note_lecture(doc: dict, stem: str):
    """The lecture whose vault note is `stem` ("NN - Name"), or None."""
    num, _, name = stem.partition(" - ")
    for week in doc["weeks"]:
        for lec in week["lectures"]:
            if lec.get("num") == num.strip() and lec["name"].strip().lower() == name.strip().lower():
                return week, lec
    for week in doc["weeks"]:
        for lec in week["lectures"]:
            if lec["name"].strip().lower() == stem.strip().lower():
                return week, lec
    return None


def ship_svg(course: str, path: Path) -> dict:
    """Copy the SVG into the course's figure assets, named after its bytes."""
    raw = path.read_bytes()
    w, h = (int(float(x)) for x in SVG_SIZE.search(raw[:2000].decode("utf-8", "replace")).groups())
    digest = hashlib.md5(raw).hexdigest()[:12]
    dest = REPO / course / "assets/figures" / f"{digest}.svg"
    if not dest.exists():
        dest.write_bytes(raw)
    return {"src": f"assets/figures/{digest}.svg", "w": w, "h": h}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", type=Path, default=Path("/mnt/c/Users/nsims/medwiki"))
    args = ap.parse_args()
    ic.BLOCKS.update({b: name for (_, b, name) in PREFIXES.values()})
    notes = {c: load_notes(c) for c in ("fom", "pom1")}
    vault_notes = {c: list((args.vault / "01 - Lectures").glob(g)) for c, g in VAULT_DIRS.items()}
    entries = {"fom": [], "pom1": []}
    placed = {}  # (course, block, lecture id) -> figure block
    for src in sorted((REPO / "tools/pathways/src").glob("*.content.json")):
        chart_id = src.name.replace(".content.json", "")
        prefix = next((p for p in PREFIXES if chart_id.startswith(p + "-")), None)
        if prefix is None:
            continue
        course, block, _ = PREFIXES[prefix]
        spec = json.loads(src.read_text())
        svg_name = spec["name"] + ".svg"
        svg_path = args.vault / "Attachments" / svg_name
        if not svg_path.exists():
            log.warning("%s: %s not rendered into the vault, skipped", chart_id, svg_name)
            continue
        needle = f"![[{svg_name}"
        stems = sorted(p.stem for p in vault_notes[course] if needle in p.read_text(errors="ignore"))
        fig = dict(ship_svg(course, svg_path), t="figure", alt=svg_name, interactive=f"charts/{chart_id}/")
        fig = {k: fig[k] for k in ("t", "src", "alt", "w", "h", "interactive")}
        lec_id = re.sub(r"_\d+$", "", chart_id)
        lec_id = lec_id[len("fom-"):] if course == "fom" else lec_id
        title, week_n, num = lec_id, 0, ""
        for stem in stems:
            hit = note_lecture(notes[course][block], stem)
            if not hit:
                log.warning("%s: note %r matches no %s lecture", chart_id, stem, block)
                continue
            week, lec = hit
            placed[(course, block, lec["id"])] = fig
            if lec["id"] == lec_id:
                title, week_n, num = lec["name"], week["n"], lec.get("num", "")
        if not week_n:
            log.warning("%s: its own lecture %s does not embed it", chart_id, lec_id)
            week_n = int(re.search(r"-w(\d+)", lec_id).group(1))
        svg = re.sub(r"<\?xml[^>]*>", "", svg_path.read_text())
        out = REPO / course / "charts" / chart_id / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        page = ic.page(spec, title, stems, svg, block)
        out.write_text(page.replace('href="../chart.css"', f'href="{SHARED}chart.css"')
                           .replace('src="../chart.js"', f'src="{SHARED}chart.js"'))
        entries[course].append({"id": chart_id, "block": block, "week": week_n, "num": num, "title": title, "covers": stems})

    for course, docs in notes.items():
        order = [b for (c, b, _) in PREFIXES.values() if c == course]
        rows = sorted(entries[course], key=lambda e: (order.index(e["block"]), e["week"], e["num"]))
        if rows:
            (REPO / course / "charts/index.html").write_text(
                ic.index(rows).replace('href="chart.css"', 'href="../../pom2/charts/chart.css"')
                              .replace('<a href="../../index.html">PoM 2</a>', f'<a href="../index.html">{"FoM" if course == "fom" else "PoM 1"}</a>')
                              .replace("endocrinology, reproduction and musculoskeletal", "Foundations of Medicine" if course == "fom" else "PoM 1"))
        for block, doc in docs.items():
            n = 0
            for week in doc["weeks"]:
                for lec in week["lectures"]:
                    blocks = [b for b in lec.get("blocks", []) if not (b.get("t") == "figure" and b.get("interactive"))]
                    fig = placed.get((course, block, lec["id"]))
                    # a lecture with no note of its own points to the one that covers it,
                    # which already carries the chart
                    if lec.get("coveredBy") or str(lec.get("hasNote")) == "False":
                        fig = None
                    if fig:
                        blocks.insert(0, fig)
                        n += 1
                    if "blocks" in lec or fig:
                        lec["blocks"] = blocks
            (REPO / course / "data/notes" / f"{block}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1))
            if n:
                log.info("%s %s: %d lectures carry an overview chart", course, block, n)
    log.info("built %d FoM and %d PoM 1 chart pages", len(entries["fom"]), len(entries["pom1"]))


if __name__ == "__main__":
    main()
