"""Thyroid function pathway (Endo Week 2, 03): hypothyroid vs thyrotoxic, then the cause.

Facts from Dr. Morrison's thyroid dysfunction deck (and the iodine slides of the
clinical approach deck). Presentation is shared on each side, so it sits once per
side; thyrotoxicosis then splits on radioactive iodine (RAI) uptake.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402

COL_W, GAP, X0, LABEL_W, GROUP_GAP = 252, 12, 15, 30, 40
N, SPLIT = 7, 3  # hypothyroid columns 0-2, thyrotoxic 3-6
XS, _x = [], X0 + LABEL_W
for i in range(N):
    if i == SPLIT:
        _x += GROUP_GAP - GAP
    XS.append(_x)
    _x += COL_W + GAP
W = XS[-1] + COL_W + X0
INK = ps.P["ink"]
COLOURS = {
    "prim": ("#1f6f8b", "#dceef4", "#eef7fa"),
    "sub": ("#4f6d1f", "#e7eed9", "#f4f7ee"),
    "cen": ("#6a4aa8", "#ebe4f7", "#f5f1fb"),
    "gr": ("#b5600f", "#fbe8d3", "#fdf4ea"),
    "nod": ("#8a5a2b", "#f3e6d8", "#faf4ee"),
    "thy": ("#a3336b", "#f8e0ec", "#fcf0f6"),
    "subh": ("#1f5f9e", "#dde9f7", "#eff5fc"),
}
KINDS = {}
for c, (strong, soft, _) in COLOURS.items():
    KINDS[c + "_h"] = [strong, strong, "#ffffff", "#ffffff"]
    KINDS[c + "_t"] = [soft, strong, strong, INK]
    KINDS[c + "_w"] = ["#ffffff", strong, strong, INK]
for k, v in KINDS.items():
    ps.KIND[k] = tuple(v)
COLS = list(COLOURS)

COLUMN = {
 "prim": {
  "head": [[("h", "Primary hypothyroidism", ["TSH ↑ · FT4 ↓", "commonest: HASHIMOTO's"])]],
  "clue": [[("t", "Hashimoto's thyroiditis", ["female · family history of autoimmune disease · iodine load", "~symptoms variable, signs not sensitive"])],
           [("w", "Other causes", ["drugs: lithium, amiodarone · surgery or radioactive iodine"])],
           [("w", "No treatment history, no pituitary risk", ["→ you may simply ASSUME Hashimoto's"])]],
  "inv": [[("t", "CONFIRM: repeat ↑TSH + ↓FT4", ["free T3 not needed"])],
          [("warn", "Leave these alone", ["anti-TPO, anti-thyroglobulin: rarely change decisions · ultrasound: only for a nodule felt on exam"])]],
  "tx": [[("ok", "Levothyroxine once daily", ["about 1.5 mcg/kg/day, titrated to a normal TSH", "start LOW if elderly or heart disease"])],
         [("w", "Half-life 1 WEEK", ["TSH every 4–6 weeks until normal · don't follow FT4/FT3 on replacement"])],
         [("w", "How to take it", ["≥ 1 h before, ≥ 2 h after food · 4 h from calcium, iron, magnesium, multivitamin · e.g. at bedtime"])],
         [("bad", "Myxedema coma: very rare", ["obtundation, hypothermia · low BP, HR, Na, glucose · hypoventilation"])]],
 },
 "sub": {
  "head": [[("h", "Subclinical hypothyroidism", ["TSH ↑ · FT4 + FT3 normal", "up to 10% · TSH usually < 10–20"])]],
  "clue": [[("t", "Often resolves on its own", ["especially TSH < 10 in the elderly"])]],
  "inv": [[("t", "Repeat TSH + FT4", ["TSH ↑ with normal free hormone"])],
          [("w", "Higher risk of progression", ["TSH > 10 · anti-TPO positive"])]],
  "tx": [[("warn", "No evidence treatment helps", ["EXCEPT in pregnancy"])],
         [("ok", "Consider treating if", ["TSH > 10 · anti-TPO positive · a therapeutic trial for possible symptoms"])]],
 },
 "cen": {
  "head": [[("h", "Central hypothyroidism", ["TSH ↔ or ↓ · FT4 ↓", "PITUITARY or hypothalamus"])]],
  "clue": [[("t", "Suspect it with", ["other pituitary deficiencies or a known pituitary mass"])],
           [("w", "Causes", ["↓ stimulation: trauma, surgery, tumour, infiltrative disease"])]],
  "inv": [[("bad", "Order TSH + FT4 TOGETHER", ["here TSH moves WITH the hormone, or not at all: a normal TSH does NOT reassure"])]],
  "tx": [[("ok", "Levothyroxine, dosed on FREE T4", ["~pituitary lecture: replace the adrenal axis first"])]],
 },
 "gr": {
  "head": [[("h", "Graves disease", ["the COMMONEST cause", "TSH-receptor antibodies drive it"])]],
  "clue": [[("t", "Risk factors", ["female · age ~30–50 · family history of autoimmune (esp. thyroid) · iodine load"])],
           [("w", "Acute or subacute", ["new neck mass"]), ("w", "SYMMETRIC goiter", [])],
           [("w", "Graves only: orbitopathy, dermopathy", ["proptosis, periorbital edema, diplopia · VISUAL LOSS = ocular emergency · SMOKING the major risk"])]],
  "inv": [[("t", "TSH receptor antibody (TRAb)", ["sensitive AND specific · a blood test · not covered by OHIP"])],
          [("w", "RAI uptake + scan", ["DIFFUSE high uptake"])]],
  "tx": [[("ok", "Methimazole FIRST line", ["Graves can REMIT · ~4–6 weeks to euthyroid · favoured over PTU"])],
         [("warn", "Methimazole risks (rare)", ["agranulocytosis · liver dysfunction · drug-induced lupus · birth defects"])],
         [("w", "No remission → RAI", ["may worsen eye disease"]), ("w", "Surgery", ["total thyroid-ectomy, rarely"])]],
 },
 "nod": {
  "head": [[("h", "Toxic adenoma / multinodular goiter", ["autonomous nodule(s)", "TMNG = toxic multinodular goiter"])]],
  "clue": [[("t", "Risk factors", ["iodine deficiency moving to sufficiency, or an iodine load"])],
           [("w", "Gradually progressive", ["MILDLY thyrotoxic · neck mass(es)"]), ("w", "ASYMMETRIC goiter", [])]],
  "inv": [[("t", "RAI uptake + scan", ["ONE hot nodule (adenoma) · SEVERAL (TMNG)"])]],
  "tx": [[("ok", "RAI FIRST line", ["permanent cure · ~6–12 weeks · ~10% need a 2nd dose"])],
         [("warn", "High risk of permanent hypothyroidism", ["RAI NEVER in pregnancy"])],
         [("w", "Surgery", ["hemithyroidectomy (adenoma) · total (TMNG)"])]],
 },
 "thy": {
  "head": [[("h", "Thyroiditis or exogenous", ["LOW uptake: hormone LEAKING", "out of a damaged gland, or from a bottle"])]],
  "clue": [[("t", "Subacute (post-viral)", ["recent upper respiratory infection · tender, PAIN, odynophagia"])],
           [("w", "Post-partum or autoimmune", ["also radiation, trauma"]), ("w", "Exogenous", ["over-treatment, factitious"])],
           [("w", "Goiter", ["asymmetric, symmetric or NONE"])]],
  "inv": [[("t", "RAI uptake LOW", ["almost none on the scan"])]],
  "tx": [[("ok", "SUPPORTIVE only", ["beta-blocker · NSAIDs, then glucocorticoids for the pain"])],
         [("warn", "Watch for the HYPOthyroid phase", ["thyroiditis burns out"])],
         [("w", "Exogenous", ["remove the excess"])]],
 },
 "subh": {
  "head": [[("h", "Subclinical hyperthyroidism", ["TSH ↓ · FT4 + FT3 normal", "same causes as overt"])]],
  "clue": [[("t", "Linked to", ["bone loss · atrial fibrillation"])],
           [("w", "Rarely assay interference", ["look up interfering substances, repeat TSH + FT4/FT3"])]],
  "inv": [[("t", "Repeat TSH + FT4/FT3", [])]],
  "tx": [[("ok", "TREAT if older and/or TSH lower", [])],
         [("w", "MONITOR if younger and/or borderline low", [])]],
 },
}
SECTIONS = ["head", "clue", "inv", "tx"]
ROW_NAMES = {"clue": "CAUSES & CLUES", "inv": "INVESTIGATIONS", "tx": "TREATMENT"}
SUB_GAP, ROW_GAP, SIDE_GAP = 22, 40, 10
OFF = round(((COL_W - SIDE_GAP) / 2 + SIDE_GAP) / 2, 1)

ch = ps.Chart({"title": "", "nodes": [], "edges": [], "width": W})


def height(title, lines, w):
    r = ch.layout_text({"title": title, "lines": lines, "id": title}, w)
    block = sum(x[3] for x in r) - r[-1][3] + (ps.TITLE_SIZE if r[-1][1] == "bold" else ps.BODY_SIZE)
    return round(block + 2 * ps.PAD_Y + 4)


def box_w(row):
    return COL_W if len(row) == 1 else (COL_W - SIDE_GAP) / 2


def resolve(c, kind):
    return f"{c}_{kind}" if kind in ("h", "t", "w") else kind


def row_h(row):
    return max(height(t, ls, box_w(row)) for _, t, ls in row)


def section_h(rows):
    return sum(row_h(r) for r in rows) + SUB_GAP * (len(rows) - 1)


def link(prev_ids, ids, dashed=False):
    if len(prev_ids) == len(ids):
        out = [{"from": a, "to": b} for a, b in zip(prev_ids, ids)]
    elif len(prev_ids) == 1:
        out = [{"from": prev_ids[0], "to": b, "from_dx": (-OFF if k == 0 else OFF)} for k, b in enumerate(ids)]
    else:
        out = [{"from": a, "to": ids[0], "to_dx": (-OFF if k == 0 else OFF)} for k, a in enumerate(prev_ids)]
    if dashed:
        for e in out:
            e["dashed"] = True
    return out


def span(c0, c1):
    return XS[c0], XS[c1] + COL_W - XS[c0]


nodes, edges = [], []
mid = (XS[0] + XS[-1] + COL_W) / 2
nodes.append({"id": "root", "x": round(mid - 360), "y": 10, "w": 720, "kind": "dark",
              "title": "Thyroid function: TSH case-finds, free T4 (± T3) confirms",
              "lines": ["primary disease is commonest: TSH moves OPPOSITE the hormone",
                        "central disease is the trap: TSH moves WITH it, or not at all"]})
rb = 10 + height(nodes[0]["title"], nodes[0]["lines"], 720)
G_Y = rb + 50
GROUPS = [("g_lo", 0, 2, "HYPOTHYROID: too little thyroid hormone", ["TSH ↑ (primary) · up to 2% · female 5–8 : 1"]),
          ("g_hi", 3, 6, "THYROTOXIC: too much thyroid hormone, from any cause", ["TSH ↓ · up to 1.5% · female 5 : 1 · hyperthyroidism = from PRODUCTION"])]
g_cx = {}
for gid, c0, c1, title, lines in GROUPS:
    gx, gw = span(c0, c1)
    nodes.append({"id": gid, "x": gx, "y": G_Y, "w": gw, "kind": "plain", "title": title, "lines": lines})
    g_cx[gid] = gx + gw / 2
    edges.append({"from": "root", "to": gid, "path": f"M{mid} {rb}V{rb + 25}H{g_cx[gid]}V{G_Y}"})
gh = max(height(t, ls, span(c0, c1)[1]) for _, c0, c1, t, ls in GROUPS)
for n in nodes:
    if n["id"] in g_cx:
        n["h"] = gh

P_Y = G_Y + gh + 40
PRES = [
 ("p_lo", "g_lo", 0, 2, "Presents as", [
     "COLD intolerance · weight GAIN despite ↓ appetite",
     "fatigue, slow mentation, apathy, depression · constipation · cool, pale skin",
     "bradycardia · diastolic hypertension, NARROW pulse pressure · ↓ cardiac output",
     "slow RELAXATION of the reflexes · short of breath, heart failure"]),
 ("p_hi", "g_hi", 3, 6, "Presents as", [
     "HEAT intolerance, sweating · weight LOSS despite ↑ appetite",
     "hyperactivity, insomnia, anxiety, emotional lability · hyperdefecation · soft, warm skin · TREMOR",
     "tachycardia · WIDE pulse pressure · ↑ cardiac output · palpitations · heart failure",
     "eyes in ANY thyrotoxicosis: stare, lid retraction, lid lag",
     "urgent: storm / instability (Graves) · high-output failure · visual loss · mental health crisis"]),
]
for pid, gid, c0, c1, title, lines in PRES:
    px, pw = span(c0, c1)
    nodes.append({"id": pid, "x": px, "y": P_Y, "w": pw, "kind": "info", "title": title, "lines": lines})
    edges.append({"from": gid, "to": pid})
ph = max(height(t, ls, span(c0, c1)[1]) for *_, c0, c1, t, ls in [(p[0], p[1], p[2], p[3], p[4], p[5]) for p in PRES])
for n in nodes:
    if n["id"] in ("p_lo", "p_hi"):
        n["h"] = ph
row_labels = [{"x": X0 + 8, "y": P_Y, "h": ph, "text": "PRESENTS AS"}]

# thyrotoxic: confirm, then making or leaking?
R_Y = P_Y + ph + 40
rx, rw = span(3, 5)
nodes.append({"id": "rai", "x": rx, "y": R_Y, "w": rw, "kind": "plain",
              "title": "Confirm (repeat ↓TSH + ↑FT4 + ↑FT3), then: is the gland MAKING it or LEAKING it?",
              "lines": ["RAI uptake + scan: the best single test for the cause · 2-day test · expensive · NOT in pregnancy",
                        "~TRAb blood test is sensitive and specific for Graves"]})
rh = height(nodes[-1]["title"], nodes[-1]["lines"], rw)
p_hi_cx = g_cx["g_hi"]
edges.append({"from": "p_hi", "to": "rai", "from_dx": round(rx + rw / 2 - p_hi_cx)})

top_y = R_Y + rh + 80
y = top_y
first_last = {}
for sec in SECTIONS:
    sec_h = max(section_h(COLUMN[c][sec]) for c in COLS)
    if sec in ROW_NAMES:
        row_labels.append({"x": X0 + 8, "y": y, "h": sec_h, "text": ROW_NAMES[sec]})
    for i, c in enumerate(COLS):
        rows = COLUMN[c][sec]
        pad = (sec_h - section_h(rows)) / len(rows)
        yy, prev, first = y, None, None
        for r_i, row in enumerate(rows):
            h = round(row_h(row) + pad)
            bw = box_w(row)
            ids = []
            for b_i, (kind, title, lines) in enumerate(row):
                nid = f"{c}_{sec}_{r_i}_{b_i}"
                nodes.append({"id": nid, "x": round(XS[i] + b_i * (bw + SIDE_GAP), 1), "y": round(yy),
                              "w": round(bw, 1), "h": h, "kind": resolve(c, kind), "title": title, "lines": lines})
                ids.append(nid)
            if prev:
                edges += link(prev, ids, dashed=(sec == "clue"))
            first = first or ids
            prev = ids
            yy += h + SUB_GAP
        first_last[(c, sec)] = (first, prev)
    y += sec_h + ROW_GAP
bottom_y = y - ROW_GAP
for c in COLS:
    for a, b in zip(SECTIONS, SECTIONS[1:]):
        edges += link(first_last[(c, a)][1], first_last[(c, b)][0])

lo_cx = g_cx["g_lo"]
rai_cx = rx + rw / 2
drops = [("prim", "p_lo", lo_cx, P_Y + ph, "TSH ↑ · FT4 ↓"), ("sub", "p_lo", lo_cx, P_Y + ph, "TSH ↑ · FT4 normal"),
         ("cen", "p_lo", lo_cx, P_Y + ph, "TSH ↔/↓ · FT4 ↓"),
         ("gr", "rai", rai_cx, R_Y + rh, "HIGH, diffuse"), ("nod", "rai", rai_cx, R_Y + rh, "HIGH, hot nodule(s)"),
         ("thy", "rai", rai_cx, R_Y + rh, "LOW"), ("subh", "p_hi", p_hi_cx, P_Y + ph, "TSH ↓ · FT4/FT3 normal")]
for c, src, scx, sb, lab in drops:
    col_cx = XS[COLS.index(c)] + COL_W / 2
    edges.append({"from": src, "to": first_last[(c, "head")][0][0], "from_dx": round(col_cx - scx),
                  "label": lab, "label_at": [col_cx, round((R_Y + rh + top_y) / 2)]})

bands = [{"x": XS[i] - 5, "y": top_y - 8, "w": COL_W + 10, "h": bottom_y - top_y + 16,
          "fill": COLOURS[c][2], "stroke": COLOURS[c][0]} for i, c in enumerate(COLS)]
py = bottom_y + 34
third = (W - X0 - XS[0] - 2 * 14) / 3
spec = {
 "name": "thyroid function pathway",
 "width": W,
 "title": ("Thyroid function pathway: TSH case-finds and free T4 confirms; hypothyroidism splits into primary "
           "(Hashimoto's), subclinical and central by TSH and free T4; thyrotoxicosis splits on radioactive iodine "
           "uptake into Graves, toxic nodules and thyroiditis or exogenous hormone, plus subclinical "
           "hyperthyroidism; each column gives causes and clues, tests and treatment"),
 "kinds": KINDS, "bands": bands, "row_labels": row_labels, "nodes": nodes, "edges": edges,
 "panels": [
  {"x": XS[0], "y": py, "w": round(third), "title": "Screen with a TSH when", "items": [
      "compatible symptoms · dyslipidemia · anemia · hyponatremia",
      "personal or family autoimmune disease · Down or Turner syndrome",
      "previous thyroid disease or therapy · drugs · pregnancy",
      "suspected pituitary or hypothalamic disease: add FT4",
      "rare: central HYPERthyroidism, TSH ↔/↑ with FT4 ↑"]},
  {"x": round(XS[0] + third + 14), "y": py, "w": round(third), "title": "Lowering production: which first?", "items": [
      "methimazole first for GRAVES: it can remit",
      "RAI first for toxic ADENOMA or TMNG, and Graves without remission",
      "surgery rarely: large symptomatic goiter · suspected cancer · can't take drugs in pregnancy · storm refractory to treatment",
      "supportive care for everyone: beta-blocker for palpitations, tachycardia, tremor"]},
  {"x": round(XS[0] + 2 * third + 28), "y": py, "w": round(third), "title": "Iodine cuts both ways", "items": [
      "Wolff-Chaikoff: a normal gland CUTS production under an iodine load, then escapes",
      "subclinical Hashimoto's may not escape → HYPOthyroid",
      "Jod-Basedow: autonomous nodules or mild Graves use the iodine → HYPERthyroid"]}],
}
Path(sys.argv[1]).write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", sys.argv[1], len(nodes), "nodes, width", W)
