"""
Purpose: The boxes and arrows of a drawn chart that has no column_pathway content file (a
         pathway_svg flow or a class_tree_svg drug tree), so pom2/charts/flow.js can put
         Look / Walk / Test over the drawn chart itself.
Author: nsimsam (with Claude Code)
Date: 2026-10-18
Input: a spec from tools/pathways/*.json or tools/class_trees/*.json
Output: (svg, model) from flow_model() / tree_model(); the svg is the renderer's own output,
        byte for byte the figure in the note, and model = {"kind", "nodes", "edges"} in its
        coordinates. Each node is {id, x, y, w, h, title, hide, req}: hide = covered at the
        start of Test, req = the nodes that must be uncovered before it can be.
"""
import re

import class_tree_svg
import pathway_svg


def flow_model(spec: dict) -> tuple:
    """A pathway_svg flow: every box, and every arrow with its drawn path."""
    chart = pathway_svg.Chart(spec)
    edges = []
    draw_edge = chart.edge

    def edge(e: dict) -> None:
        before, labels = len(chart.parts), len(chart.label_boxes)
        draw_edge(e)
        d = ""
        if len(chart.parts) > before:   # the path is inserted at the front, under the boxes
            m = re.search(r' d="([^"]+)"', chart.parts[0])
            d = m.group(1) if m else ""
        edge = {"from": e["from"], "to": e["to"], "label": e.get("label", ""), "d": d}
        if len(chart.label_boxes) > labels:   # where its label sits, to keep it lit with the arrow
            edge["lb"] = [round(v, 1) for v in chart.label_boxes[-1][1:]]
        edges.append(edge)

    chart.edge = edge
    svg = chart.build()
    titles = {n["id"]: n["title"] for n in spec["nodes"] if "id" in n}
    for i, it in enumerate((spec.get("any_of") or {}).get("items", [])):
        titles["_any%d" % i] = it["title"]
    parents = {}
    for e in edges:
        parents.setdefault(e["to"], []).append(e["from"])
    nodes = []
    for nid, (x, y, w, h) in chart.boxes.items():
        title = titles.get(nid) or nid.replace("_panel_", "")
        nodes.append({"id": nid, "x": x, "y": y, "w": w, "h": h, "title": title,
                      "hide": nid in parents or nid.startswith("_panel_"), "req": parents.get(nid, [])})
    return svg, {"kind": "flow", "nodes": nodes, "edges": edges}


def tree_model(spec: dict) -> tuple:
    """A class_tree_svg drug tree: root, the question chain if any, class headers, drug cards."""
    rects, cards, groups, asks = [], [], [], []
    rect, card, group, ask = (class_tree_svg.Svg.rect, class_tree_svg.draw_card,
                              class_tree_svg.draw_group, class_tree_svg.draw_ask)

    def log_rect(self, x, y, w, h, fill, *a, **k):
        rects.append((x, y, w, h, fill))
        return rect(self, x, y, w, h, fill, *a, **k)

    def log_card(svg, x, y, w, drug, dry=False):
        h = card(svg, x, y, w, drug, dry)
        if not dry:
            cards.append((len(groups), x, y, w, h, drug["name"]))
        return h

    def log_group(svg, x, y, w, g):
        at = len(rects)
        bottom = group(svg, x, y, w, g)
        hx, hy, hw, hh, _ = rects[at]
        groups.append((hx, hy, hw, hh, g["title"]))
        return bottom

    def log_ask(svg, x, y, w, h, a):
        asks.append((x, y, w, h, a))
        return ask(svg, x, y, w, h, a)

    class_tree_svg.Svg.rect, class_tree_svg.draw_card = log_rect, log_card
    class_tree_svg.draw_group, class_tree_svg.draw_ask = log_group, log_ask
    try:
        svg, _ = class_tree_svg.build(spec)
    finally:
        class_tree_svg.Svg.rect, class_tree_svg.draw_card = rect, card
        class_tree_svg.draw_group, class_tree_svg.draw_ask = group, ask

    ink = class_tree_svg.PALETTE["ink"]
    root = [r for r in rects if r[4] == ink and r[3] == 40][0]
    nodes = [{"id": "root", "x": root[0], "y": root[1], "w": root[2], "h": root[3],
              "title": spec["root"], "hide": False, "req": []}]
    edges = []
    gs = spec["groups"]
    ask_of = {}                      # group index -> ask node id
    it = iter(asks)
    for i, g in enumerate(gs):
        if g.get("ask"):
            x, y, w, h, a = next(it)
            ask_of[i] = "a%d" % i
            nodes.append({"id": "a%d" % i, "x": x, "y": y, "w": w, "h": h, "title": a["q"],
                          "hide": False, "req": []})
    for i, (x, y, w, h, title) in enumerate(groups):
        nodes.append({"id": "g%d" % i, "x": x, "y": y, "w": w, "h": h, "title": title,
                      "hide": False, "req": []})
    if ask_of:
        order = sorted(ask_of)
        edges.append({"from": "root", "to": ask_of[order[0]], "label": ""})
        for i in range(len(gs)):
            if i not in ask_of:
                continue
            a = gs[i]["ask"]
            edges.append({"from": ask_of[i], "to": "g%d" % i, "label": a.get("yes", "yes")})
            if i + 1 < len(gs):
                nxt = ask_of.get(i + 1, "g%d" % (i + 1))
                edges.append({"from": ask_of[i], "to": nxt, "label": a.get("no", "no")})
    else:
        for i in range(len(gs)):
            edges.append({"from": "root", "to": "g%d" % i, "label": ""})
    prev = {}
    for n, (gi, x, y, w, h, name) in enumerate(cards):
        cid = "c%d" % n
        nodes.append({"id": cid, "x": x, "y": y, "w": w, "h": h, "title": name,
                      "hide": True, "req": [prev.get(gi, "g%d" % gi)]})
        edges.append({"from": "g%d" % gi, "to": cid, "label": ""})
        prev[gi] = cid
    return svg, {"kind": "tree", "nodes": nodes, "edges": edges}
