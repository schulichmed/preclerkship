"""Lay out a disease-by-column pathway from a content file, as a spec for tools/pathway_svg.py.

Purpose: the adrenal, calcium and thyroid charts share one layout (a dark root box,
         group boxes, optional shared "presents as" boxes and decision tiers, then one
         colour column per disease with stepped sub-boxes, row labels down the left and
         panels along the bottom). This builds that layout from content alone.
Input:   content JSON (see CONTENT SHAPE below)
Output:  a pathway spec JSON; render it with
         python tools/pathway_svg.py <spec> --out x.svg --png x.png

CONTENT SHAPE
{
 "name": "disorders of puberty overview",       # the svg file name in the vault: always "<topic> overview"
 "title": "one sentence for screen readers",
 "col_w": 252,                                  # optional, px per column
 "root": {"title": "...", "lines": ["..."]},
 "groups": [{"id": "g1", "cols": [0, 2], "title": "...", "lines": ["..."]}],
     # every column belongs to exactly one group; groups are left to right and
     # adjacent; a wider gap separates groups
 "pres": [{"id": "p1", "group": "g1", "title": "Presents as", "lines": ["..."]}],
     # optional: one shared box under a group, spanning it (kind info)
 "tiers": [{"id": "t1", "cols": [0, 1], "title": "...", "lines": ["..."]}],
     # optional: decision boxes between the group/pres row and the columns;
     # its parent is the pres box of its group, or the group box
 "sections": ["head", "clue", "inv", "tx"],     # head first; the rest are row names
 "row_names": {"clue": "CAUSES & CLUES", "inv": "INVESTIGATIONS", "tx": "TREATMENT"},
     # "pres" here renames the shared-box row (default PRESENTS AS)
 "dashed_sections": ["clue"],                   # sub-box links drawn dashed (more features)
 "columns": [
   {"id": "cpp", "colour": "teal",
    "drop_from": "t1", "drop_label": "LH ↑",   # which box feeds this column, label on the arrow
    "head": [[["h", "Central precocious puberty", ["line", "line"]]]],
    "clue": [[["t", "Title", ["line"]]], [["w", "Left", []], ["w", "Right", []]]],
    ...}],
 "spans": [{"section": "tx", "cols": [0, 2], "rows": [[["plain", "Which kind?", []]],
                                                     [["ok", "A", ["..."]], ["ok", "B", ["..."]]]]}],
     # optional: one block of a section shared by adjacent columns, drawn across them
     # (same rows-of-boxes shape, fixed kinds only); those columns leave that section out
     # and each one's last box above feeds the span's first box
 "panels": [{"title": "...", "items": ["..."], "cols": 1}]   # laid out evenly along the bottom
}
A section is a list of rows; a row holds one box or two side by side. A box is
[kind, title, lines]. kind "h" = solid header, "t" = tinted, "w" = white with the
column's colour; or a fixed kind: ok (treatment), warn, bad (danger), info, plain.
A line starting with "~" is drawn muted and italic (a qualifier, not a fact).
Colours: teal purple orange blue magenta brown olive slate red-free only.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pathway_svg as ps  # noqa: E402

PALETTE = {  # name -> (strong, soft, band)
    "teal": ("#1f6f8b", "#dceef4", "#eef7fa"),
    "purple": ("#6a4aa8", "#ebe4f7", "#f5f1fb"),
    "orange": ("#b5600f", "#fbe8d3", "#fdf4ea"),
    "blue": ("#1f5f9e", "#dde9f7", "#eff5fc"),
    "magenta": ("#a3336b", "#f8e0ec", "#fcf0f6"),
    "brown": ("#8a5a2b", "#f3e6d8", "#faf4ee"),
    "olive": ("#4f6d1f", "#e7eed9", "#f4f7ee"),
    "slate": ("#46607a", "#e2e8ee", "#f2f5f8"),
}
GAP, X0, LABEL_W, GROUP_GAP = 12, 15, 30, 40
SUB_GAP, ROW_GAP, SIDE_GAP = 22, 40, 10


def build(c: dict) -> dict:
    col_w = c.get("col_w", 252)
    cols = c["columns"]
    n = len(cols)
    group_of = {}
    for g in c["groups"]:
        for i in range(g["cols"][0], g["cols"][1] + 1):
            group_of[i] = g["id"]
    if sorted(group_of) != list(range(n)):
        raise SystemExit("every column must belong to exactly one group")
    xs, x = [], X0 + LABEL_W
    for i in range(n):
        if i > 0 and group_of[i] != group_of[i - 1]:
            x += GROUP_GAP - GAP
        xs.append(x)
        x += col_w + GAP
    width = xs[-1] + col_w + X0

    kinds = {}
    for col in cols:
        strong, soft, _ = PALETTE[col["colour"]]
        kinds[col["id"] + "_h"] = [strong, strong, "#ffffff", "#ffffff"]
        kinds[col["id"] + "_t"] = [soft, strong, strong, ps.P["ink"]]
        kinds[col["id"] + "_w"] = ["#ffffff", strong, strong, ps.P["ink"]]
    for k, v in kinds.items():
        ps.KIND[k] = tuple(v)
    chart = ps.Chart({"title": "", "nodes": [], "edges": [], "width": width})

    def height(title, lines, w):
        r = chart.layout_text({"title": title, "lines": lines, "id": title}, w)
        block = sum(t[3] for t in r) - r[-1][3] + (ps.TITLE_SIZE if r[-1][1] == "bold" else ps.BODY_SIZE)
        return round(block + 2 * ps.PAD_Y + 4)

    def span(c0, c1):
        return xs[c0], xs[c1] + col_w - xs[c0]

    def box_w(row, w=col_w):
        return w if len(row) == 1 else (w - SIDE_GAP) / 2

    def row_h(row, w=col_w):
        return max(height(t, ls, box_w(row, w)) for _, t, ls in row)

    def section_h(rows, w=col_w):
        return sum(row_h(r, w) for r in rows) + SUB_GAP * (len(rows) - 1)

    def link(a, b, dashed=False, w=col_w):
        off = round(((w - SIDE_GAP) / 2 + SIDE_GAP) / 2, 1)
        if len(a) == len(b):
            out = [{"from": p, "to": q} for p, q in zip(a, b)]
        elif len(a) == 1:
            out = [{"from": a[0], "to": q, "from_dx": (-off if k == 0 else off)} for k, q in enumerate(b)]
        else:
            out = [{"from": p, "to": b[0], "to_dx": (-off if k == 0 else off)} for k, p in enumerate(a)]
        if dashed:
            for e in out:
                e["dashed"] = True
        return out

    nodes, edges, row_labels = [], [], []
    geo = {}  # id -> (centre x, bottom y)
    mid = (xs[0] + xs[-1] + col_w) / 2
    rw = min(760, width - 2 * (X0 + LABEL_W))
    root = dict(c["root"])
    root["lines"] = [ln.lstrip("~") for ln in root.get("lines", [])]  # muted grey is unreadable on the dark fill
    nodes.append({"id": "root", "x": round(mid - rw / 2), "y": 10, "w": rw, "kind": "dark",
                  "title": root["title"], "lines": root["lines"]})
    rb = 10 + height(root["title"], root.get("lines", []), rw)

    g_y = rb + 50
    gh = max(height(g["title"], g.get("lines", []), span(*g["cols"])[1]) for g in c["groups"])
    for g in c["groups"]:
        gx, gw = span(*g["cols"])
        nodes.append({"id": g["id"], "x": gx, "y": g_y, "w": gw, "h": gh, "kind": "plain",
                      "title": g["title"], "lines": g.get("lines", [])})
        geo[g["id"]] = (gx + gw / 2, g_y + gh)
        edges.append({"from": "root", "to": g["id"], "path": f"M{mid} {rb}V{rb + 25}H{gx + gw / 2}V{g_y}"})
    y = g_y + gh + 40
    parent_of_group = {g["id"]: g["id"] for g in c["groups"]}

    pres = c.get("pres", [])
    if pres:
        gmap = {g["id"]: g for g in c["groups"]}
        ph = max(height(p["title"], p["lines"], span(*gmap[p["group"]]["cols"])[1]) for p in pres)
        for p in pres:
            px, pw = span(*gmap[p["group"]]["cols"])
            nodes.append({"id": p["id"], "x": px, "y": y, "w": pw, "h": ph, "kind": "info",
                          "title": p["title"], "lines": p["lines"]})
            geo[p["id"]] = (px + pw / 2, y + ph)
            edges.append({"from": p["group"], "to": p["id"]})
            parent_of_group[p["group"]] = p["id"]
        row_labels.append({"x": X0 + 8, "y": y, "h": ph, "text": c.get("row_names", {}).get("pres", "PRESENTS AS")})
        y += ph + 40

    tiers = c.get("tiers", [])
    if tiers:
        th = max(height(t["title"], t.get("lines", []), span(*t["cols"])[1]) for t in tiers)
        for t in tiers:
            tx, tw = span(*t["cols"])
            nodes.append({"id": t["id"], "x": tx, "y": y, "w": tw, "h": th, "kind": "plain",
                          "title": t["title"], "lines": t.get("lines", [])})
            par = parent_of_group[group_of[t["cols"][0]]]
            edges.append({"from": par, "to": t["id"], "from_dx": round(tx + tw / 2 - geo[par][0])})
            geo[t["id"]] = (tx + tw / 2, y + th)
        y += th + 40
    label_y_top = y - 40
    top_y = y + 40

    sections = c["sections"]
    spans = c.get("spans", [])
    span_of = {}  # (column index, section) -> span index
    for s_i, sp in enumerate(spans):
        if sp["section"] == sections[0]:
            raise SystemExit("a span cannot replace the head section")
        for i in range(sp["cols"][0], sp["cols"][1] + 1):
            span_of[(i, sp["section"])] = s_i
    first_last, sec_top = {}, {}
    y = top_y

    def lay(rows, x0, w, y, sec_h, prefix, kind_of, dashed):
        """Place a stack of rows in one column (or span) and link it top to bottom."""
        nonlocal edges
        pad = (sec_h - section_h(rows, w)) / len(rows)
        yy, prev, first = y, None, None
        for r_i, row in enumerate(rows):
            h = round(row_h(row, w) + pad)
            bw = box_w(row, w)
            ids = []
            for b_i, (kind, title, lines) in enumerate(row):
                nid = f"{prefix}_{r_i}_{b_i}"
                nodes.append({"id": nid, "x": round(x0 + b_i * (bw + SIDE_GAP), 1), "y": round(yy),
                              "w": round(bw, 1), "h": h, "kind": kind_of(kind), "title": title, "lines": lines})
                ids.append(nid)
            if prev:
                edges += link(prev, ids, dashed=dashed, w=w)
            first = first or ids
            prev = ids
            yy += h + SUB_GAP
        return first, prev

    for sec in sections:
        sec_top[sec] = y
        own = [col[sec] for i, col in enumerate(cols) if (i, sec) not in span_of]
        sec_h = max([section_h(r) for r in own]
                    + [section_h(sp["rows"], span(*sp["cols"])[1]) for sp in spans if sp["section"] == sec])
        if sec in c.get("row_names", {}):
            row_labels.append({"x": X0 + 8, "y": y, "h": sec_h, "text": c["row_names"][sec]})
        dashed = sec in c.get("dashed_sections", [])
        for i, col in enumerate(cols):
            if (i, sec) in span_of:
                continue
            first_last[(col["id"], sec)] = lay(
                col[sec], xs[i], col_w, y, sec_h, f"{col['id']}_{sec}",
                lambda k, cid=col["id"]: f"{cid}_{k}" if k in ("h", "t", "w") else k, dashed)
        for s_i, sp in enumerate(spans):
            if sp["section"] == sec:
                sx, sw = span(*sp["cols"])
                first_last[("span", s_i)] = lay(sp["rows"], sx, sw, y, sec_h, f"span{s_i}_{sec}",
                                                lambda k: k, dashed)
        y += sec_h + ROW_GAP
    bottom_y = y - ROW_GAP
    for ci, col in enumerate(cols):
        for a, b in zip(sections, sections[1:]):
            if (ci, a) in span_of:
                if (ci, b) not in span_of:
                    raise SystemExit("a column cannot leave a span for a section of its own")
                continue
            if (ci, b) in span_of:
                s_i = span_of[(ci, b)]
                sx, sw = span(*spans[s_i]["cols"])
                target = first_last[("span", s_i)][0]
                cx = xs[ci] + col_w / 2
                for p_id in first_last[(col["id"], a)][1]:
                    # land straight below this column, or on the nearer half of a two-box first row
                    t = target[0] if len(target) == 1 or cx < sx + sw / 2 else target[1]
                    tx = sx + sw / 2 if len(target) == 1 else (sx + box_w(target, sw) / 2 if t == target[0]
                                                                else sx + sw - box_w(target, sw) / 2)
                    edges.append({"from": p_id, "to": t, "to_dx": round(cx - tx, 1)})
                continue
            edges += link(first_last[(col["id"], a)][1], first_last[(col["id"], b)][0])
        src = col.get("drop_from") or parent_of_group[group_of[cols.index(col)]]
        cx = xs[cols.index(col)] + col_w / 2
        e = {"from": src, "to": first_last[(col["id"], sections[0])][0][0], "from_dx": round(cx - geo[src][0])}
        if col.get("drop_label"):
            e["label"], e["label_at"] = col["drop_label"], [cx, round((label_y_top + top_y) / 2)]
        edges.append(e)

    def band_bottom(i):
        spanned = [sec_top[s] for s in sections if (i, s) in span_of]
        return min(spanned) - ROW_GAP if spanned else bottom_y

    bands = [{"x": xs[i] - 5, "y": top_y - 8, "w": col_w + 10, "h": band_bottom(i) - top_y + 16,
              "fill": PALETTE[col["colour"]][2], "stroke": PALETTE[col["colour"]][0]} for i, col in enumerate(cols)]
    panels = []
    if c.get("panels"):
        k = len(c["panels"])
        pw = (width - X0 - xs[0] - 14 * (k - 1)) / k
        for j, p in enumerate(c["panels"]):
            panels.append({"x": round(xs[0] + j * (pw + 14)), "y": bottom_y + 34, "w": round(pw),
                           "title": p["title"], "items": p["items"], "cols": p.get("cols", 1)})
    return {"name": c["name"], "width": width, "title": c["title"], "kinds": kinds, "bands": bands,
            "row_labels": row_labels, "nodes": nodes, "edges": edges, "panels": panels}


if __name__ == "__main__":
    content = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    Path(sys.argv[2]).write_text(json.dumps(build(content), indent=1, ensure_ascii=False), encoding="utf-8")
    print("wrote", sys.argv[2])
