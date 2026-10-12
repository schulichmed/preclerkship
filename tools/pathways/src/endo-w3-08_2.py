"""Transgender medicine as an osteoporosis-style flow: assess, then the reversibility ladder.

Same facts as the column chart (the transgender column version, retired); only the drawing changes.
Boxes are stacked with measured heights; arrows run on right angles.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pathway_svg as ps  # noqa: E402

W = 1000
ch = ps.Chart({"title": "", "nodes": [], "edges": [], "width": W})
nodes, edges, geo = [], [], {}


def H(title, lines, w):
    r = ch.layout_text({"title": title, "lines": lines, "id": title}, w)
    block = sum(t[3] for t in r) - r[-1][3] + (ps.TITLE_SIZE if r[-1][1] == "bold" else ps.BODY_SIZE)
    return round(block + 2 * ps.PAD_Y + 4)


def node(nid, x, y, w, kind, title, lines=(), h=None):
    h = h or H(title, list(lines), w)
    nodes.append({"id": nid, "x": x, "y": y, "w": w, "h": h, "kind": kind, "title": title, "lines": list(lines)})
    geo[nid] = (x, y, w, h)
    return y + h


def down(src, dst, label=None):
    """Right-angled: down from src's bottom centre to a rail, across, down into dst's top centre."""
    sx, sy, sw, sh = geo[src]
    dx, dy, dw, _ = geo[dst]
    x0, y0, x1 = sx + sw / 2, sy + sh, dx + dw / 2
    if abs(x0 - x1) < 1:
        e = {"from": src, "to": dst, "path": f"M{x0} {y0}V{dy}"}
        mid = (y0 + dy) / 2
    else:
        bus = round(y0 + (dy - y0) / 2)
        e = {"from": src, "to": dst, "path": f"M{x0} {y0}V{bus}H{x1}V{dy}"}
        mid = bus + (dy - bus) / 2
    if label:
        e["label"], e["label_at"] = label, [x1 + 4, round(mid)]
    edges.append(e)


def side(src, dst, label=None, dashed=False):
    """Horizontal from src's side at its middle into dst's facing side."""
    sx, sy, sw, sh = geo[src]
    dx, dy, dw, dh = geo[dst]
    y = round(sy + sh / 2)
    x0, x1 = (sx, dx + dw) if dx < sx else (sx + sw, dx)
    e = {"from": src, "to": dst, "path": f"M{x0} {y}H{x1}"}
    if label:
        e["label"], e["label_at"] = label, [round((x0 + x1) / 2), y - 9]
    if dashed:
        e["dashed"] = True
    edges.append(e)


C = 500  # spine centre
y = node("start", C - 220, 10, 440, "plain", "Gender dysphoria?",
         ["DISCONTENT: body or assigned gender INCONGRUENT with gender identity, with stigma, isolation, rejection",
          "~Canada 2022: 1 in 300 aged 15+ trans or non-binary · adolescents 1.2–4.1%"])
a_y = y + 40
edges.append({"from": "_any1", "to": "start"})
a_bot = node("assess", C - 220, a_y, 440, "plain", "Assess: four questions",
             ["1 · gender identity: \"born in the wrong body?\"",
              "2 · persistence: \"how long have you felt a girl/boy?\" · \"how did puberty affect you?\"",
              "3 · gender non-conforming behaviour: toys, underwear, swimwear, fantasy characters",
              "4 · source of distress: \"what do you think about your body?\""])
down("start", "assess")
risk = ["Ontario trans youth: 47% thought about suicide, 19% attempted",
        "suicide risk 4% with FAMILY SUPPORT vs 60% without"]
node("risk", 15, a_y, 230, "bad", "SUICIDALITY 2–3× more frequent", risk)
side("assess", "risk", dashed=True)
node("team", 755, a_y, 230, "ok", "Multidisciplinary care",
     ["youth treated with hormones, surgery + a team with mental health clinicians: outcomes like the general population"])
side("assess", "team", dashed=True)

q_y = max(a_bot, geo["risk"][1] + geo["risk"][3], geo["team"][1] + geo["team"][3]) + 40
q_bot = node("tanner", C - 150, q_y, 300, "plain", "Young person: TANNER 2 reached?", ["~puberty has started"])
down("assess", "tanner")
node("wait", 15, q_y, 250, "warn", "Not yet", ["NO hormonal therapy until puberty has STARTED"])
side("tanner", "wait", "no")

b_y = q_bot + 50
b_bot = node("block", C - 230, b_y, 460, "ok", "1 · PUBERTY BLOCKERS: FULLY reversible",
             ["hit the PAUSE button: buys time to assess PERSISTENCE before the physical changes of puberty",
              "criteria: long-lasting nonconformity or dysphoria · WORSENED with puberty · other problems addressed · informed consent",
              "slows growth, breast or testicular/penile growth, periods, androgen-dependent hair, voice deepening",
              "improves behaviour, emotional + depressive symptoms",
              "~gonadotropin-releasing hormone (GnRH) agonist, e.g. leuprolide †"])
down("tanner", "block", "yes")
node("fert", 760, b_y, 225, "warn", "FERTILITY: discuss BEFORE hormones",
     ["oocyte preservation: EXPENSIVE, no provincial plan covers it · may be traumatizing · must be OFF hormones with 1–2 normal periods"])
side("block", "fert", dashed=True)

c_y = max(b_bot, geo["fert"][1] + geo["fert"][3]) + 50
c_bot = node("crit", C - 260, c_y, 520, "plain", "Criteria for hormones",
             ["ADULTS (WPATH): persistent, well-documented dysphoria · capacity to consent · age of majority · medical or mental health concerns reasonably well-CONTROLLED",
              "ADOLESCENTS: confirmed persistence · able to consent · preferably parental support · usually ~16 y · decided by the team, adolescent + family",
              "~after a psychosocial assessment + informed consent, with a referral from the assessing mental health professional"])
down("block", "crit")
node("adult", 15, c_y, 200, "plain", "Adult", ["~starts here"])
side("adult", "crit")

# two hormone families
h_y = c_bot + 60
hw, hx = 480, [15, 505]
mas = ["two goals: SUPPRESS the designated sex hormones, then REPLACE, as for a hypogonadal patient",
       "enanthate or cypionate 100–200 mg IM every 2 wk (or SC 50% weekly) · undecanoate 1000 mg every 12 wk · gel 1.6% 50–100 mg/d · patch 2.5–7.5 mg/d",
       "~injection: \"roller coaster\" levels · oral: 2–3× daily with fatty food, CANNOT be monitored"]
fem = ["two goals: SUPPRESS the designated sex hormones, then REPLACE, as for a hypogonadal patient",
       "estradiol: oral 2–6 mg/d · patch 0.025–0.2 mg/d every 3–5 d · IM valerate or cypionate 5–30 mg every 2 wk",
       "anti-androgen: spironolactone 100–300 mg/d · cyproterone acetate 25–50 mg/d · or GnRH agonist 3.75 mg SC monthly"]
hh = max(H("2 · MASCULINIZING: TESTOSTERONE", mas, hw), H("2 · FEMINIZING: ESTROGEN ± anti-androgen", fem, hw))
node("mas", hx[0], h_y, hw, "anti", "2 · MASCULINIZING: TESTOSTERONE", mas, h=hh)
node("fem", hx[1], h_y, hw, "ana", "2 · FEMINIZING: ESTROGEN ± anti-androgen", fem, h=hh)
down("crit", "mas", "transgender males (FTM)")
down("crit", "fem", "transgender females (MTF)")

e_y = h_y + hh + 34
mas_e = ["1–6 months: oily skin, acne · fat redistribution · periods STOP · clitoral enlargement · vaginal atrophy",
         "6–12 months: facial/body hair · scalp hair loss · muscle (max 2–5 y) · voice DEEPENS (max 1–2 y)",
         "PERMANENT: hair growth · deeper voice · clitoris · male-pattern balding · height + bone mineral ↑",
         "not permanent: muscle · libido · no periods · acne · UNKNOWN: fertility"]
fem_e = ["1–3 months: ↓ sexual desire · ↓ spontaneous erections",
         "3–6 months: fat redistribution · ↓ muscle · softer skin · BREAST growth (max 2–3 y) · ↓ testicular volume",
         "slow or none: terminal hair ↓ (max > 3 y) · scalp hair variable · VOICE: no change",
         "PERMANENT: breast development · bone mineral ↑ · not permanent: skin, muscle, fat pattern, body hair"]
eh = max(H("Effects (partially reversible)", mas_e, hw), H("Effects (partially reversible)", fem_e, hw))
node("mas_e", hx[0], e_y, hw, "plain", "Effects (partially reversible)", mas_e, h=eh)
node("fem_e", hx[1], e_y, hw, "plain", "Effects (partially reversible)", fem_e, h=eh)
down("mas", "mas_e")
down("fem", "fem_e")

r_y = e_y + eh + 34
mas_r = ["likely: POLYCYTHEMIA · weight gain · acne · balding · SLEEP APNEA",
         "possible: liver enzymes ↑ · HYPERLIPIDEMIA · with risk factors: psychiatric destabilization, CVD, hypertension, type 2 diabetes",
         "monitor every 3 mo in year 1, then 1–2×/yr: T 400–700 ng/dL (midway between injections) · hematocrit · weight, BP, lipids"]
fem_r = ["likely: VENOUS THROMBOEMBOLISM (more with ORAL estrogen) · gallstones · liver enzymes ↑ · weight gain · hypertriglyceridemia",
         "possible: hypertension · PROLACTINOMA · type 2 diabetes with risk factors",
         "monitor every 3 mo in year 1, then 1–2×/yr: T < 50 ng/dL · estradiol ≤ 100–200 pg/mL · POTASSIUM on spironolactone"]
rh = max(H("Risks + monitoring", mas_r, hw), H("Risks + monitoring", fem_r, hw))
node("mas_r", hx[0], r_y, hw, "warn", "Risks + monitoring", mas_r, h=rh)
node("fem_r", hx[1], r_y, hw, "warn", "Risks + monitoring", fem_r, h=rh)
down("mas_e", "mas_r")
down("fem_e", "fem_r")

s_y = r_y + rh + 60
s_bot = node("surg", C - 250, s_y, 500, "bad", "3 · SURGERY: IRREVERSIBLE",
             ["referral (WPATH): 1 or 2 letters from a qualified mental health professional · ONTARIO: TWO providers must support it",
              "GENITAL surgery not until the age of MAJORITY + ≥ 1 year living in the intended gender role",
              "TOP surgery can be earlier: age 16 · hormones × 1 year",
              "~those who recommend surgery share ETHICAL + LEGAL responsibility with the surgeon"])
# both hormone columns join into surgery
mr, fr, sg = geo["mas_r"], geo["fem_r"], geo["surg"]
bus = round(r_y + rh + 30)
edges.append({"from": "mas_r", "to": "surg", "path": f"M{mr[0] + mr[2] / 2} {r_y + rh}V{bus}H{C}V{s_y}"})
edges.append({"from": "fem_r", "to": "surg", "path": f"M{fr[0] + fr[2] / 2} {r_y + rh}V{bus}H{C}"})

p_y = s_bot + 34
spec = {
 "name": "transgender medicine overview",
 "width": W,
 "title": ("Transgender medicine pathway: assess gender dysphoria, then climb the reversibility ladder from puberty "
           "blockers (fully reversible) through masculinizing or feminizing hormones (partially reversible) to surgery "
           "(irreversible), with the criteria, regimens, effects, risks and monitoring at each step"),
 "any_of": {"heading": "Gender dysphoria is supported by:", "joiner": "AND", "items": [
     {"title": "INSISTENCE", "lines": ["how FIRM: \"I AM a boy\", not \"I wish I were\""]},
    {"title": "PERSISTENCE", "lines": ["how LONG: months to years, often stronger at puberty"]},
    {"title": "CONSISTENCE", "lines": ["how WIDE: the same at home, school, with friends"]}]},
 "nodes": nodes,
 "edges": edges,
 "panels": [
  {"x": 15, "y": p_y, "w": 480, "title": "Before starting hormones (WPATH)", "items": [
      "evaluate goals, history, exam, risks, relevant labs",
      "discuss effects + side effects, incl. ↓ FERTILITY: options BEFORE starting",
      "confirm capacity to understand risks + benefits",
      "ongoing monitoring · communicate with primary care, mental health, surgeon",
      "after transition: ovariectomy can be considered · breast exams or mammograms as tissue remains"]},
  {"x": 505, "y": p_y, "w": 480, "title": "Terms + screening", "items": [
      "SEX: biological · GENDER: psychological · GENDER IDENTITY: the person's own · SEXUAL ORIENTATION: who one is attracted to",
      "breast cancer on estrogen: Stein ↑ risk · WPATH no ↑ or inconclusive",
      "bone density: transgender females at baseline · transgender males if T stopped or not taken",
      "cancer screening as usual for tissues present (cervix, breasts)"]}],
}
Path(sys.argv[1]).write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")
print("wrote", sys.argv[1])
