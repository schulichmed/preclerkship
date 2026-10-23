"""Calcium disorders pathway (Endo Week 2, 04): high vs low calcium, sorted by PTH and phosphate.

Facts from the lecture deck (Hypercalcemia/Hyperparathyroidism, Hypocalcemia/
Hypoparathyroidism and their treatment). Presentation is shared within each side,
so it sits once in that side's box; each column carries its tests, causes and treatment.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402

COL_W, GAP, X0, LABEL_W, GROUP_GAP = 266, 12, 15, 30, 40
XS, _x = [], X0 + LABEL_W
for i in range(6):
    if i == 3:
        _x += GROUP_GAP - GAP
    XS.append(_x)
    _x += COL_W + GAP
W = XS[-1] + COL_W + X0
INK = ps.P["ink"]
COLOURS = {
    "php": ("#b5600f", "#fbe8d3", "#fdf4ea"),
    "mal": ("#a3336b", "#f8e0ec", "#fcf0f6"),
    "vdx": ("#8a5a2b", "#f3e6d8", "#faf4ee"),
    "hypo": ("#1f6f8b", "#dceef4", "#eef7fa"),
    "pseudo": ("#6a4aa8", "#ebe4f7", "#f5f1fb"),
    "vdd": ("#1f5f9e", "#dde9f7", "#eff5fc"),
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
 "php": {
  "head": [[("h", "Primary hyperparathyroidism", ["PTH-MEDIATED · PTH ↑ or inappropriately normal", "phosphate ↓ (PTH makes the kidney waste it)"])]],
  "inv": [[("w", "1 · Repeat corrected Ca + PTH", ["with phosphate and 25-OH-D", "~the case: Ca 2.73, phosphate 0.69, PTH 14 (1.6–6.9)"])],
          [("t", "2 · 24-h urine Ca + creatinine", ["fractional excretion of calcium (FE_Ca) = (urine Ca × serum Cr/1000) ÷ (serum Ca × urine Cr)"])],
          [("w", "> 0.02", ["likely PRIMARY"]), ("w", "< 0.01", ["FHH"])],
          [("w", "0.01–0.02: overlap (20% of FHH)", ["~recheck off thiazides × 3 months, normal Mg, 25-OH-D > 50"])]],
  "cause": [[("t", "Parathyroid ADENOMA 80%", ["hyperplasia · carcinoma"])],
            [("w", "Familial", ["isolated · jaw tumour syndrome · MEN"]),
             ("w", "Also PTH-mediated", ["FHH (calcium-sensing receptor) · tertiary (renal failure)"])]],
  "tx": [[("w", "Mild, asymptomatic, > 50", ["no treatment, or drugs: bisphosphonates, denosumab, estrogen, cinacalcet"])],
         [("ok", "Symptomatic → SURGERY", ["hydrate · avoid thiazides, lithium"])],
         [("warn", "Surgery if any ONE", ["Ca > 0.25 above upper limit · T-score < −2.5 (spine, femoral neck, total hip, 1/3 radius) · vertebral fracture · CrCl < 60 · 24-h urine Ca > 10 + stone risk · stones or nephrocalcinosis · age < 50"])]],
 },
 "mal": {
  "head": [[("h", "Hypercalcaemia of malignancy", ["PTH-INDEPENDENT · PTH suppressed", "with hyperparathyroidism, > 90% of cases"])]],
  "inv": [[("t", "PTH SUPPRESSED", ["so it is not the parathyroid"])],
          [("w", "Humoral cases", ["the tumour makes PTH-related peptide (PTHrP)"])]],
  "cause": [[("t", "Metastases", ["breast cancer"])],
            [("w", "PTHrP", ["solid tumours: lung, kidney · adult T-cell leukaemia"]),
             ("w", "Lymphokines", ["myeloma"])],
            [("w", "Vitamin D-like steroids", ["lymphoma"]), ("w", "Prostaglandins", [])]],
  "tx": [[("ok", "Acute treatment (below)", ["saline → furosemide → IV zoledronate → calcitonin"])],
         [("warn", "Prednisone 40–60 mg/day", ["then taper · for MYELOMA"])]],
 },
 "vdx": {
  "head": [[("h", "Vitamin D and other causes", ["PTH-INDEPENDENT · PTH suppressed", "minor causes, < 10%"])]],
  "inv": [[("t", "PTH SUPPRESSED", ["the history finds most of these"])]],
  "cause": [[("t", "Vitamin D related", ["exogenous ingestion · granulomatous: sarcoid, TB"])],
            [("w", "Immobilisation", ["on Paget's, thyrotoxicosis, adrenal insufficiency"]),
             ("w", "Drugs", ["thiazides (usually transient) · milk-alkali (absorbable antacids)"])],
            [("w", "Other", ["hyperthyroidism, acromegaly, pheochromocytoma, adrenal insufficiency, parenteral nutrition"])]],
  "tx": [[("ok", "Acute treatment (below)", ["if corrected Ca > 3"])],
         [("warn", "Prednisone 40–60 mg/day", ["then taper · for VITAMIN D INTOXICATION"])]],
 },
 "hypo": {
  "head": [[("h", "Hypoparathyroidism", ["PTH DEFICIENT: failure to SECRETE", "Ca ↓ · phosphate ↑ · PTH ↓"])]],
  "inv": [[("t", "Persistent low Ca", ["PTH LOW or inappropriately normal"])],
          [("warn", "≥ 6 months after surgery", ["before calling it permanent"])],
          [("w", "Check magnesium", ["low OR high magnesium is a functional cause"])]],
  "cause": [[("t", "POST-SURGICAL 75%", [])],
            [("w", "Non-surgical 25%", ["autoimmune · infiltrative · post-radiation · magnesium · metastatic · genetic"])]],
  "tx": [[("ok", "Chronic: calcitriol 0.25 mcg twice daily", ["+ 1–2 g elemental calcium, divided · keep 25-OH-D > 75 · monitor Ca and phosphate"])],
         [("w", "Thiazide", ["↓ urine calcium, ↓ stones"]), ("w", "Recombinant PTH", ["approved in US + Europe"])],
         [("warn", "Aim for LOW-normal calcium", ["watch for ectopic calcification: renal ultrasound, head MRI (basal ganglia) · Ca × phosphate < 4.4"])],
         [("bad", "NOT loop diuretics", ["key point: not a treatment"])]],
 },
 "pseudo": {
  "head": [[("h", "Pseudohypoparathyroidism", ["PTH RESISTANT: failure to RESPOND", "Ca ↓ · phosphate ↑ · PTH ↑"])]],
  "inv": [[("t", "Low Ca with HIGH PTH", ["the gland works, the body ignores it"])],
          [("w", "Type 1a: Albright's hereditary osteodystrophy", ["round face, short stature, short metacarpals and metatarsals"])],
          [("bad", "The trap: pseudopseudo- hypoparathyroidism", ["SAME look, NO PTH resistance: normal panel"])]],
  "cause": [[("t", "Inherited", ["types 1a, 1b and 2"])]],
  "tx": [[("ok", "Chronic hypocalcaemia treatment", ["calcitriol + elemental calcium, as for hypoparathyroidism"])]],
 },
 "vdd": {
  "head": [[("h", "Vitamin D deficiency", ["the COMMONEST of the three", "Ca ↓ · phosphate ↓ · PTH ↑"])]],
  "inv": [[("t", "Low Ca with LOW phosphate", ["more common than the PTH disorders"])],
          [("w", "Also: failure to RESPOND to vitamin D", [])]],
  "cause": [[("t", "Malabsorption", ["a fat-soluble vitamin"])],
            [("w", "Organ failure", ["renal or liver"]), ("w", "Drugs, diet", ["phenytoin · diet (rare)"])],
            [("w", "No sun", ["rickets (child), osteomalacia (adult)"])]],
  "tx": [[("ok", "Chronic: vitamin D + calcium", ["keep 25-OH-D > 75 · 1–2 g elemental calcium"])],
         [("w", "Osteomalacia", ["~see the metabolic bone disease chart"])]],
 },
}
SECTIONS = ["head", "inv", "cause", "tx"]
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


nodes, edges = [], []
mid = (XS[0] + XS[-1] + COL_W) / 2
nodes.append({"id": "root", "x": round(mid - 330), "y": 10, "w": 660, "kind": "dark",
              "title": "Calcium problem: CORRECT for albumin, then ALWAYS send a PTH",
              "lines": ["corrected Ca = measured Ca + 0.02 × (40 − albumin)",
                        "normal total 2.15–2.55 mmol/L · ionized 1.1–1.3 (50%), protein-bound 40%, complexed 10%"]})
rb = 10 + height(nodes[0]["title"], nodes[0]["lines"], 660)
G_Y = rb + 50
GROUPS = [
 ("g_hi", 0, 2, "HIGH calcium: corrected > 2.55 mmol/L",
  ["> 90% is hyperparathyroidism or malignancy · then PTH sorts it",
   "~symptoms depend on the level and how fast it rose"]),
 ("g_lo", 3, 5, "LOW calcium",
  ["PTH and PHOSPHATE sort it", "~rarely, acute complexation of calcium"]),
]
g_cx, g_bot = {}, {}
for gid, c0, c1, title, lines in GROUPS:
    gx, gw = XS[c0], XS[c1] + COL_W - XS[c0]
    nodes.append({"id": gid, "x": gx, "y": G_Y, "w": gw, "kind": "plain", "title": title, "lines": lines})
    g_cx[gid], g_bot[gid] = gx + gw / 2, G_Y + height(title, lines, gw)
    edges.append({"from": "root", "to": gid, "path": f"M{mid} {rb}V{rb + 25}H{g_cx[gid]}V{G_Y}"})
gh = max(g_bot.values()) - G_Y
for n in nodes:
    if n["id"] in g_bot:
        n["h"] = gh
# shared presentation, once per side
P_Y = G_Y + gh + 40
PRES = [
 ("p_hi", "g_hi", "Presents as: often ASYMPTOMATIC · stones, bones, groans, psychiatric overtones", [
     "GI: abdominal distress, pancreatitis, constipation, vomiting, anorexia",
     "renal: POLYURIA (nephrogenic diabetes insipidus), stones, renal insufficiency",
     "bone: pain, cystic lesions, demineralisation, spontaneous fractures",
     "heart: SHORT QT, arrhythmias, hypertension · brain: confusion, personality change, depression, apathy"]),
 ("p_lo", "g_lo", "Presents as", [
     "acute, severe: TETANY — perioral paraesthesias, carpopedal spasm, laryngeal spasm, seizures, palpitations",
     "acute, mild: CHVOSTEK's and TROUSSEAU's signs · heart: PROLONGED QT",
     "chronic: emotional instability, anxiety, brain fog, paraesthesias · cataracts, dry skin, brittle nails",
     "~over-treatment: movement disorders, kidney stones"]),
]
p_bot = {}
for pid, gid, title, lines in PRES:
    g = next(n for n in nodes if n["id"] == gid)
    nodes.append({"id": pid, "x": g["x"], "y": P_Y, "w": g["w"], "kind": "info", "title": title, "lines": lines})
    p_bot[pid] = height(title, lines, g["w"])
ph = max(p_bot.values())
for n in nodes:
    if n["id"] in p_bot:
        n["h"] = ph
for pid, gid, *_ in PRES:
    edges.append({"from": gid, "to": pid})
row_labels = [{"x": X0 + 8, "y": P_Y, "h": ph, "text": "PRESENTS AS"}]

y = top_y = P_Y + ph + 80
ROW_NAMES = {"inv": "INVESTIGATIONS", "cause": "CAUSES", "tx": "TREATMENT"}
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
                edges += link(prev, ids, dashed=(sec == "cause"))
            first = first or ids
            prev = ids
            yy += h + SUB_GAP
        first_last[(c, sec)] = (first, prev)
    y += sec_h + ROW_GAP
bottom_y = y - ROW_GAP
for c in COLS:
    for a, b in zip(SECTIONS, SECTIONS[1:]):
        edges += link(first_last[(c, a)][1], first_last[(c, b)][0])

p_cx = {"p_hi": g_cx["g_hi"], "p_lo": g_cx["g_lo"]}
for c, lab, pid in [("php", "PTH ↑ or inappropriately normal", "p_hi"), ("mal", "PTH suppressed", "p_hi"),
                    ("vdx", "PTH suppressed", "p_hi"), ("hypo", "PTH ↓ · phosphate ↑", "p_lo"),
                    ("pseudo", "PTH ↑ · phosphate ↑", "p_lo"), ("vdd", "PTH ↑ · phosphate ↓", "p_lo")]:
    col_cx = XS[COLS.index(c)] + COL_W / 2
    edges.append({"from": pid, "to": first_last[(c, "head")][0][0], "from_dx": round(col_cx - p_cx[pid]),
                  "label": lab, "label_at": [col_cx, round((P_Y + ph + top_y) / 2)]})

bands = [{"x": XS[i] - 5, "y": top_y - 8, "w": COL_W + 10, "h": bottom_y - top_y + 16,
          "fill": COLOURS[c][2], "stroke": COLOURS[c][0]} for i, c in enumerate(COLS)]
py = bottom_y + 34
hi_w = XS[2] + COL_W - XS[0]
lo_w = XS[5] + COL_W - XS[3]
spec = {
 "name": "calcium disorders pathway",
 "width": W,
 "title": ("Calcium disorders pathway: correct for albumin and always send a PTH; high calcium splits into "
           "PTH-mediated primary hyperparathyroidism (with FHH told apart by urine calcium excretion) and "
           "PTH-independent malignancy or vitamin D causes; low calcium splits by PTH and phosphate into "
           "hypoparathyroidism, pseudohypoparathyroidism and vitamin D deficiency"),
 "kinds": KINDS,
 "bands": bands,
 "row_labels": row_labels,
 "nodes": nodes,
 "edges": edges,
 "panels": [
  {"x": XS[0], "y": py, "w": hi_w, "title": "ACUTE hypercalcaemia: admit if corrected Ca > 3 mmol/L", "cols": 2, "items": [
      "1. volume: assume a 4–6 L deficit, replace with normal saline",
      "2. forced diuresis ONLY once well hydrated: 4–10 L saline + furosemide + potassium",
      "3. intravenous zoledronate (bisphosphonate)",
      "4. calcitonin",
      "5. prednisone 40–60 mg/day then taper: myeloma, vitamin D intoxication"]},
  {"x": XS[3], "y": py, "w": lo_w, "title": "ACUTE hypocalcaemia: only if corrected Ca < 1.9 AND symptoms", "cols": 2, "items": [
      "neurological (tetany, seizures, carpopedal spasm) or cardiac (prolonged QT)",
      "10% calcium gluconate 1–2 g in 50 mL 5% dextrose over 15–20 min",
      "then 1–3 mg/kg/h elemental calcium · cardiac monitor, inpatient",
      "ALWAYS treat low magnesium",
      "minor causes: low albumin · low magnesium (alcohol, malabsorption) · pancreatitis · tumour lysis, rhabdomyolysis, sepsis · massive transfusion"]}],
}
Path(sys.argv[1]).write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", sys.argv[1], len(nodes), "nodes, width", W)
