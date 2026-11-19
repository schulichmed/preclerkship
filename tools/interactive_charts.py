"""
Purpose: Build the portal's interactive overview charts (Look / Walk / Test): one page per drawn
         overview chart whose source is a column_pathway content file, an index page, and
         the svg-name -> page map that points each lecture's chart figure at its page.
Author: nsimsam (with Claude Code)
Date: 2026-10-18
Input: <preclerkship>/tools/pathways/src/*.content.json (endo, repro, msk, neuro), the portal's
       pom2/data/notes/<block>.json for lecture names, and the vault's rendered
       "<name>.svg" for the "compare with the chart" panel. Every other drawn chart in those
       notes (a pathway_svg flow or a class_tree_svg drug tree, matched to its spec in
       tools/pathways/*.json or tools/class_trees/*.json by rendering it) gets a page too,
       with the modes laid over the drawing itself (pom2/charts/flow.js).
Output: pom2/charts/<chart id>/index.html, pom2/charts/index.html, pom2/charts/charts.json,
        and an "interactive" link on each matching figure block in pom2/data/notes/<block>.json
        (tools/charts_from_vault.py adds the same link on every rebuild, from charts.json).
        A content-file chart's picture in the notes is redrawn from that same content file
        on every run (its tools/pathways/<id>.json spec, the vault's Attachments svg, a
        pom2/assets/figures file and its figures.json row, and the note's figure block), so
        the notes and the body map always show the same chart: edit the content file, run
        this, and both change together.
        The pages share pom2/charts/chart.js, flow.js and chart.css, which are hand-written.

Usage: python3 tools/interactive_charts.py [--vault /mnt/c/Users/nsims/medwiki]
"""
import argparse
import hashlib
import html
import json
import logging
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import class_tree_svg  # noqa: E402
import column_pathway  # noqa: E402
import pathway_svg  # noqa: E402
from interactive_flows import flow_model, tree_model  # noqa: E402
HERE = REPO / "pom2/charts"
BLOCKS = {"endo": "Endocrinology", "repro": "Reproduction", "msk": "Musculoskeletal", "neuro": "Neurology"}

log = logging.getLogger("charts")


def lecture_names(repo: Path) -> dict:
    """Map lecture id -> lecture name from the portal's note data."""
    names = {}
    for block in BLOCKS:
        data = json.loads((repo / "pom2/data/notes" / f"{block}.json").read_text())
        for week in data["weeks"]:
            for lec in week["lectures"]:
                names[lec["id"]] = (week["n"], lec.get("num", ""), lec["name"])
    return names


def notes_embedding(vault: Path, svg_name: str) -> list:
    """Lecture notes (file stems) that embed the chart's SVG."""
    lectures = vault / "01 - Lectures/99 - PoM 2"
    needle = f"![[{svg_name}"
    return sorted(p.stem for p in lectures.glob("0[1-4]*/Week */*.md") if needle in p.read_text(errors="ignore"))


def page(spec: dict, title: str, covers: list, svg: str, block: str, model: dict = None) -> str:
    """One chart page: the HTML grid of a content file, or (model given) the drawn chart, svg,
    with the modes laid over it."""
    if model:
        data = json.dumps({"model": model}, ensure_ascii=False).replace("</", "<\\/")
        # a wide chart keeps ~70% of its drawn width and scrolls sideways, so its text stays readable
        width = model.get("width", 920)
        script, cls, inner = "flow.js", "fmap\" style=\"--mw:%dpx" % (round(width * 0.7) if width > 1000 else 0), svg
        noun, test, svg = "a box", "one box at a time", ""
    else:
        data = json.dumps({"spec": spec}, ensure_ascii=False).replace("</", "<\\/")
        script, cls, inner, noun, test = "chart.js", "map", "", "a column", "one row at a time"
    covers_html = ""
    if len(covers) > 1:
        covers_html = "<p class=\"lead\">Covers: " + " · ".join(html.escape(c) for c in covers) + "</p>"
    compare = ""
    if svg:
        compare = ("<details class=\"orig\"><summary>Compare with the chart as it is in the notes</summary>"
                   f"<div class=\"paper\">{svg}</div></details>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="referrer" content="no-referrer">
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../chart.css">
</head>
<body>
<div class="wrap">
<header>
<p class="eyebrow"><a href="../../{block}.html">{BLOCKS[block]}</a> · <a href="../">All interactive charts</a></p>
<h1>{html.escape(title)}</h1>
{covers_html}
{compare}
</header>
<section class="v" id="chart" style="margin-top:28px">
<div class="chips modes" id="modes" role="tablist" aria-label="Mode">
<button class="chip" data-mode="look" aria-pressed="true">Look: click {noun} to focus it</button>
<button class="chip" data-mode="walk" aria-pressed="false">Walk: answer its questions</button>
<button class="chip" data-mode="test" aria-pressed="false">Test: tap to reveal, {test}</button>
</div>
<div class="walkbar" id="bar"></div>
<div class="{cls}" id="map">{inner}</div>
</section>
<footer>The content is the overview chart from the notes, unchanged; only what you can do with it is new.</footer>
</div>
<script>var D = {data};</script>
<script src="../{script}"></script>
</body>
</html>
"""


def index(entries: list) -> str:
    """The list of every chart, by block and week."""
    parts, block, week = [], None, None
    for e in entries:
        if e["block"] != block:
            if block:
                parts.append("</ul>")
            block, week = e["block"], None
            parts.append(f"<h2>{BLOCKS[block]}</h2>")
        if e["week"] != week:
            if week is not None:
                parts.append("</ul>")
            week = e["week"]
            parts.append(f"<h3>Week {week}</h3><ul class=\"list\">")
        covers = f"<span>{html.escape(' · '.join(e['covers']))}</span>" if len(e["covers"]) > 1 else ""
        parts.append(f"<li><a href=\"{e['id']}/\">{html.escape(e['title'])}</a>{covers}</li>")
    parts.append("</ul>")
    body = "\n".join(parts)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive">
<title>Interactive charts</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="chart.css">
</head>
<body>
<div class="wrap">
<header>
<p class="eyebrow"><a href="../../index.html">PoM 2</a></p>
<h1>Interactive overview charts</h1>
<p class="lead">Every overview chart from the endocrinology, reproduction, musculoskeletal and neurology notes, with three ways to use it: Look (focus one column), Walk (answer the chart's questions from the top), and Test (each column starts as its name; tap to reveal the next row).</p>
</header>
{body}
</div>
</body>
</html>
"""


SVG_SIZE = re.compile(r'<svg\b[^>]*?\bwidth="([\d.]+)"[^>]*?\bheight="([\d.]+)"')


def draw(repo: Path, chart_id: str, content: dict, vault: Path) -> tuple:
    """Draw the notes' picture of a content-file chart from the same content its page is
    built from, so the picture in the notes and the chart the body map pops up cannot
    disagree. Writes the layout spec (tools/pathways/<id>.json), the vault's
    Attachments/<name>.svg when the vault is reachable (figures.py copies from there on a
    full rebuild), and the portal's content-hashed asset with its figures.json row.
    Returns (svg text, figure row)."""
    spec = column_pathway.build(content)
    spec_path = repo / "tools/pathways" / f"{chart_id}.json"
    spec_text = json.dumps(spec, indent=1, ensure_ascii=False)
    if not spec_path.exists() or spec_path.read_text(encoding="utf-8") != spec_text:
        spec_path.write_text(spec_text, encoding="utf-8")
    chart = pathway_svg.Chart(spec)
    svg = chart.build()
    for e in chart.errors:
        log.error("%s: %s", chart_id, e)
    name = content["name"] + ".svg"
    attach = vault / "Attachments"
    if attach.is_dir():
        target = attach / name
        if not target.exists() or target.read_text(encoding="utf-8") != svg:
            target.write_text(svg, encoding="utf-8", newline="\n")
            log.info("%s: redrew %s in the vault", chart_id, name)
    raw = svg.encode("utf-8")
    digest = hashlib.md5(raw).hexdigest()[:12]
    asset = repo / "pom2/assets/figures" / f"{digest}.svg"
    if not asset.exists():
        asset.write_bytes(raw)
        log.info("%s: new picture %s", chart_id, asset.name)
    w, h = SVG_SIZE.search(svg).groups()
    row = {"src": f"assets/figures/{digest}.svg", "w": int(float(w)), "h": int(float(h))}
    hot = hotspots(content, spec)
    if hot:
        row["hot"] = hot
    return svg, row


def hotspots(content: dict, spec: dict) -> list:
    """The boxes of a drawn chart that open another lecture's note: each pointer column's
    arrow box ("home": the chart that holds the condition in full). [x, y, w, h, lecture id,
    label] in the picture's own pixels; portal.js lays a link over each, so the picture stays
    a picture (it prints) and the box still takes you there."""
    boxes = {n["id"]: n for n in spec["nodes"]}
    first = content["sections"][1] if len(content["sections"]) > 1 else None
    out = []
    for col in content["columns"]:
        home = col.get("home")
        n = boxes.get(f"{col['id']}_{first}_0_0") if home and first else None
        if n:
            out.append([n["x"], n["y"], n["w"], n["h"], re.sub(r"_\d+$", "", home["chart"]),
                        "Open " + home["name"]])
    return out


def stamp_figures(repo: Path, rows: dict) -> None:
    """Record each redrawn picture in figures.json, the manifest charts_from_vault.py reads.
    Only pictures a note already shows: figures.py adds a new one when a note embeds it."""
    path = repo / "pom2/data/figures.json"
    raw = path.read_text()
    manifest = json.loads(raw)
    rows = {k: v for k, v in rows.items() if k in manifest}
    if all(manifest.get(k) == v for k, v in rows.items()):
        return
    manifest.update(rows)
    out = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True)
    path.write_text(out + ("\n" if raw.endswith("\n") else ""))


def stamp_notes(repo: Path, links: dict, drawn: dict = None) -> int:
    """Point each lecture's overview figure at its interactive page, in place, and (drawn
    maps svg name -> figure row) at the picture drawn from the same content.

    Only those keys of matching figure blocks change, so the notes JSON diff is that and
    nothing else; a full charts_from_vault.py rebuild adds the same keys.
    """
    drawn = drawn or {}
    count = 0
    for block in BLOCKS:
        path = repo / "pom2/data/notes" / f"{block}.json"
        raw = path.read_text()
        data = json.loads(raw)
        for week in data["weeks"]:
            for lec in week["lectures"]:
                for b in lec.get("blocks", []):
                    if b.get("t") == "figure" and b.get("alt") in links:
                        b["interactive"] = links[b["alt"]]
                        b.update(drawn.get(b["alt"], {}))
                        count += 1
        compact = "\n" not in raw.strip()
        out = json.dumps(data, ensure_ascii=False, separators=(",", ":")) if compact else json.dumps(data, ensure_ascii=False, indent=1)
        path.write_text(out + ("\n" if raw.endswith("\n") else ""))
    return count


def figure_specs(repo: Path) -> dict:
    """Map each drawn chart's SVG text -> (chart id, kind, spec) for every flow and drug-tree spec."""
    out = {}
    for f in sorted((repo / "tools/pathways").glob("*.json")):
        spec = json.loads(f.read_text())
        if "nodes" not in spec:
            continue
        chart = pathway_svg.Chart(spec)
        out[chart.build().strip()] = (f.stem, "flow", spec)
    for f in sorted((repo / "tools/class_trees").glob("*.json")):
        spec = json.loads(f.read_text())
        out[class_tree_svg.build(spec)[0].strip()] = ("tree-" + f.stem.replace("_", "-"), "tree", spec)
    return out


def drawn_figures(repo: Path, skip: set) -> list:
    """(block, lecture id, svg name, svg text) for each drawn chart a note shows that has no
    content-file page (skip holds those svg names)."""
    out, seen = [], set()
    for block in BLOCKS:
        data = json.loads((repo / "pom2/data/notes" / f"{block}.json").read_text())
        for week in data["weeks"]:
            for lec in week["lectures"]:
                for b in lec.get("blocks", []):
                    alt = b.get("alt", "")
                    if b.get("t") != "figure" or not b.get("src", "").endswith(".svg") or alt in skip or alt in seen:
                        continue
                    seen.add(alt)
                    out.append((block, lec["id"], alt, (repo / "pom2" / b["src"]).read_text()))
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", type=Path, default=Path("/mnt/c/Users/nsims/medwiki"))
    args = ap.parse_args()
    args.repo = REPO
    names = lecture_names(args.repo)
    links = {}
    drawn = {}
    entries = []
    for src in sorted((args.repo / "tools/pathways/src").glob("*.content.json")):
        chart_id = src.name.replace(".content.json", "")
        block = chart_id.split("-")[0]
        if block not in BLOCKS:
            continue
        spec = json.loads(src.read_text())
        lec_id = re.sub(r"_\d+$", "", chart_id)
        week, num, name = names.get(lec_id, (int(re.search(r"-w(\d+)", lec_id).group(1)), "", lec_id))
        svg_name = spec["name"] + ".svg"
        svg, drawn[svg_name] = draw(args.repo, chart_id, spec, args.vault)
        covers = notes_embedding(args.vault, svg_name)
        if not covers:
            log.warning("%s: no note embeds %s", chart_id, svg_name)
        out = HERE / chart_id / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(page(spec, name, covers, svg, block))
        links[svg_name] = f"charts/{chart_id}/"
        entries.append({"id": chart_id, "block": block, "week": week, "num": num, "title": name, "covers": covers})
    # every other drawn chart: the modes over the drawing, matched to its spec by rendering it
    specs = figure_specs(args.repo)
    for block, lec_id, svg_name, text in drawn_figures(args.repo, set(links)):
        hit = specs.get(text.strip())
        if not hit:
            log.warning("%s: %s matches no spec (re-render it from its spec); no page", lec_id, svg_name)
            continue
        chart_id, kind, spec = hit
        svg, model = flow_model(spec) if kind == "flow" else tree_model(spec)
        model["width"] = spec.get("width", 920)
        week, num, name = names.get(lec_id, (int(re.search(r"-w(\d+)", lec_id).group(1)), "", lec_id))
        covers = notes_embedding(args.vault, svg_name)
        out = HERE / chart_id / "index.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(page(spec, name, covers, re.sub(r"<\?xml[^>]*>", "", svg), block, model))
        links[svg_name] = f"charts/{chart_id}/"
        entries.append({"id": chart_id, "block": block, "week": week, "num": num, "title": name, "covers": covers})
    order = list(BLOCKS)
    entries.sort(key=lambda e: (order.index(e["block"]), e["week"], e["num"]))
    (HERE / "index.html").write_text(index(entries))
    (HERE / "charts.json").write_text(json.dumps(links, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    stamp_figures(args.repo, drawn)
    stamped = stamp_notes(args.repo, links, drawn)
    log.info("built %d chart pages; linked %d chart figures in the notes", len(entries), stamped)


if __name__ == "__main__":
    main()
