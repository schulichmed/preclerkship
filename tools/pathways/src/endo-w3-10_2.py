"""PMOS as an osteoporosis-style flow: the triad as an AND row, then exclude, read, treat.

Same facts as the column chart (the PMOS column version, retired); only the drawing changes.
Boxes are stacked with measured heights so nothing overlaps.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402

W = 1000
ch = ps.Chart({"title": "", "nodes": [], "edges": [], "width": W})


def H(title, lines, w):
    r = ch.layout_text({"title": title, "lines": lines, "id": title}, w)
    block = sum(t[3] for t in r) - r[-1][3] + (ps.TITLE_SIZE if r[-1][1] == "bold" else ps.BODY_SIZE)
    return round(block + 2 * ps.PAD_Y + 4)


nodes, edges = [], []
geo = {}


def rail(src, dst, label=None, label_dx=0):
    """Straight down from src's bottom to a bus, across, straight down into dst's top centre."""
    sx, sy, sw, sh = geo[src]
    dx, dy, dw, dh = geo[dst]
    x0, y0, x1 = sx + sw / 2, sy + sh, dx + dw / 2
    bus = round(y0 + (dy - y0) / 2)
    e = {"from": src, "to": dst, "path": f"M{x0} {y0}V{bus}H{x1}V{dy}"}
    if label:
        e["label"], e["label_at"] = label, [x1 + label_dx, round(bus + (dy - bus) / 2)]
    return e


def node(nid, x, y, w, kind, title, lines=(), h=None):
    n = {"id": nid, "x": x, "y": y, "w": w, "kind": kind, "title": title, "lines": list(lines)}
    if h:
        n["h"] = h
    nodes.append(n)
    geo[nid] = (x, y, w, h or H(title, list(lines), w))
    return y + (h or H(title, list(lines), w))


# spine
y = node("start", 310, 10, 380, "plain", "Oligomenorrhoea and/or hyperandrogenism",
         ["~renamed from polycystic ovary syndrome (PCOS) in 2026: the follicles are arrested antral follicles, not cysts"])
y = node("labs", 290, y + 36, 420, "plain", "History, exam + first-line labs",
         ["beta-hCG (human chorionic gonadotropin) · prolactin · TSH (thyroid-stimulating hormone) · total testosterone",
          "~pelvic ultrasound is NOT required"])
q_y = y + 40
edges += [{"from": "_any1", "to": "start"}, {"from": "start", "to": "labs"}]
q_bottom = node("mimic", 360, q_y, 280, "plain", "A mimic?", ["~the lecture's 7: exclude them first"])
edges.append({"from": "labs", "to": "mimic"})
# the two mimic families either side of the question
oligo = ["pregnancy: ↑ beta-hCG", "hyperprolactinaemia: GALACTORRHOEA, ↑ prolactin (normal < 20 nmol/L)",
         "hyperthyroidism: ↓ TSH, ↑ free T4", "early menarche or menopause: menstrual history"]
andro = ["exogenous testosterone, incl. a PARTNER's topical gel: medication + social history",
         "tumour, ovary or adrenal: RAPID onset, ↑↑↑ testosterone → imaging",
         "non-classic congenital adrenal hyperplasia (CAH): ↑ 17-hydroxyprogesterone"]
side_h = max(H("NOT PMOS: mimics of oligomenorrhoea", oligo, 300), H("NOT PMOS: mimics of hyperandrogenism", andro, 300))
side_y = q_y
node("m_oligo", 15, side_y, 300, "bad", "NOT PMOS: mimics of oligomenorrhoea", oligo, h=side_h)
node("m_andro", 685, side_y, 300, "bad", "NOT PMOS: mimics of hyperandrogenism", andro, h=side_h)
mq = geo["mimic"]
my = round(mq[1] + mq[3] / 2)
edges += [{"from": "mimic", "to": "m_oligo", "path": f"M{mq[0]} {my}H315", "label": "yes", "label_at": [337, my - 9]},
          {"from": "mimic", "to": "m_andro", "path": f"M{mq[0] + mq[2]} {my}H685", "label": "yes", "label_at": [663, my - 9]}]

t_y = max(q_bottom, side_y + side_h) + 40
y = node("testo", 330, t_y, 340, "plain", "Read the total testosterone",
         ["~the only androgen used (not DHEAS or androstenedione) · female normal < 2 nmol/L"])
edges.append({"from": "mimic", "to": "testo", "label": "no", "label_at": [500, round((q_bottom + t_y) / 2)]})

o_y = y + 50
outs = [("t_norm", 15, "warn", "Normal (< 2 nmol/L)", ["does NOT exclude PMOS: the exam (terminal male-pattern hair, acne, alopecia) can meet this limb"]),
        ("t_fit", 350, "ok", "~2.1–2.5 nmol/L", ["slightly raised: fits PMOS"]),
        ("t_tum", 685, "bad", "~10 nmol/L: the male range", ["NOT PMOS: think TUMOUR → imaging"])]
oh = max(H(t, ls, 300) for *_, t, ls in outs)
for nid, x, kind, title, lines in outs:
    node(nid, x, o_y, 300, kind, title, lines, h=oh)
edges += [rail("testo", "t_norm"), rail("testo", "t_fit"), rail("testo", "t_tum")]

p_y = o_y + oh + 40
p_bottom = node("pmos", 330, p_y, 340, "plain", "PMOS: treat what distresses her",
                ["~and watch metabolic + endometrial risk in everyone"])
tn, pm = geo["t_norm"], geo["pmos"]
pm_mid = round(pm[1] + pm[3] / 2)
edges += [{"from": "t_norm", "to": "pmos", "path": f"M{tn[0] + tn[2] / 2} {tn[1] + tn[3]}V{pm_mid}H{pm[0]}"},
          {"from": "t_fit", "to": "pmos"}]

# four treatment arms
a_y = p_bottom + 60
aw, ax = 230, [15, 262, 509, 756]
arms = [
 ("hair", "anti", "Hirsutism + hair", ["surface: epilation, shaving, sugaring, waxing, laser",
   "oral: antiandrogens (spironolactone, cyproterone) · birth control pill",
   "topical: EFLORNITHINE", "alopecia: MINOXIDIL 5%, antiandrogens, pill, transplant",
   "~hirsutism is defined by her DISTRESS, not a score"], "hirsutism"),
 ("cyc", "ana", "Irregular cycles + endometrium", ["birth control pill or cyclical progesterone · weight loss, exercise",
   "WITHDRAWAL BLEEDS ≥ 4× a year: endometrial cancer is more common",
   "ultrasound surveillance for endometrial hypertrophy"], "cycles"),
 ("fert", "info", "Subfertility", ["lifestyle · induce ovulation with AROMATASE INHIBITORS",
   "metformin (arguably) for early miscarriage",
   "ovarian stroma surgery: RARE now"], "fertility"),
 ("meta", "ok", "Metabolic risk", ["hemoglobin A1c + lipid panel · monitor diabetes, hypertension, cardiovascular disease",
   "lifestyle: high fibre, low fat · 150 min vigorous exercise a week · MODEST weight loss",
   "consider BARIATRIC surgery"], "metabolic"),
]
ah = max(H(t, ls, aw) for _, _, t, ls, _ in arms)
for (nid, kind, title, lines, lab), x in zip(arms, ax):
    node(nid, x, a_y, aw, kind, title, lines, h=ah)
for nid, *_, lab in arms:
    edges.append(rail("pmos", nid))
b_y = a_y + ah + 34
extra = [("hair", "x_hair", "bad", "NOT topical testosterone", ["the one wrong treatment"]),
         ("fert", "x_fert", "warn", "She CAN conceive spontaneously", ["→ effective contraception if pregnancy is not wanted"]),
         ("meta", "x_meta", "warn", "NO body shaming", ["NOT all with PMOS are overweight · a GENTLE weight history"])]
eh = max(H(t, ls, aw) for *_, t, ls in extra)
for src, nid, kind, title, lines in extra:
    x = ax[[a[0] for a in arms].index(src)]
    node(nid, x, b_y, aw, kind, title, lines, h=eh)
    edges.append({"from": src, "to": nid})

panel_y = b_y + eh + 34
spec = {
 "name": "polyendocrine metabolic ovarian syndrome overview",
 "width": W,
 "title": ("PMOS pathway: oligomenorrhoea or hyperandrogenism; exclude the seven mimics, read the total testosterone, "
           "and treat the symptom that distresses her, with the diagnostic triad (all three needed) across the top"),
 "any_of": {"heading": "PMOS is diagnosed when ALL THREE are met:", "joiner": "AND", "items": [
     {"title": "Hyperandrogenism", "lines": ["~clinical exam OR labs (↑ testosterone)"]},
     {"title": "Ovulatory dysfunction", "lines": ["~oligomenorrhoea OR cystic ovaries on ultrasound"]},
     {"title": "Other disorders excluded", "lines": ["~the 7 mimics below"]}]},
 "nodes": nodes,
 "edges": edges,
 "panels": [
  {"x": 15, "y": panel_y, "w": 480, "title": "History + exam clues", "items": [
      "menstrual history: how often at first, in the later teens, after 20",
      "just stopped the pill, now irregular? the pill MASKED it",
      "TERMINAL male-pattern hair: sides of face, chin, chest, upper arms",
      "Ferriman-Gallwey score: 9 sites graded 1–4; ignores ethnicity + hair removal",
      "acanthosis nigricans · skin tags · central adiposity (waist ÷ hip > 0.85)",
      "PMOS is GRADUAL and has NO galactorrhoea"]},
  {"x": 505, "y": panel_y, "w": 480, "title": "Myths to dispel", "items": [
      "TRUE: subfertility + early miscarriage · type 2 diabetes, hypertension, high lipids · endometrial cancer · mood disorders",
      "FALSE: cannot lose weight · always hungry · an organic or vegan diet helps · cannot conceive",
      "more common: gestational diabetes · frontal alopecia · NOT adrenal hypertrophy",
      "no gold-standard test · insulin resistance is ASSOCIATED, not a 4th criterion",
      "over 170 million women, up to 20% of reproductive age"]}],
}
Path(sys.argv[1]).write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", sys.argv[1])
