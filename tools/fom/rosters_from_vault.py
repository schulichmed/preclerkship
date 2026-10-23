# -*- coding: utf-8 -*-
"""Rebuild fom/data/notes/<slug>.json as a bare lecture roster.

Purpose: list every FoM lecture so the notes tab reads as a coverage map of
         the course rather than a list of whatever happens to be written up.
Author:  Noor Sims
Date:    2026-09-20
Input:   the vault's "99 - FoM" tree (dir via $FOM_VAULT)
Output:  fom/data/notes/b1.json .. b4.json

Every lecture in the block's vault folders lands here whether or not a note has
been written for it, with hasNote false throughout. No FoM lecture carries an
"# Overview chart" region yet, which is what the PoM 2 portal folds into this
roster to turn a placeholder into a note, so for now the whole roster is
placeholders - 178 lectures waiting on 178 charts.
"""

import io, json, os, re

VAULT = os.environ.get(
    "FOM_VAULT", u"/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - FoM")
BLOCKS = [
    ("b1", u"Block 1", [1, 2, 3, 4]),
    ("b2", u"Block 2", [5, 6, 7, 8]),
    ("b3", u"Block 3", [9, 10, 11, 12]),
    ("b4", u"Block 4", [13, 14, 15]),
]


def week_labels(slug):
    """reuse the week headings the questions tab already shows, so both tabs
       name the same week the same way"""
    p = "fom/data/questions/%s.json" % slug
    labels = {}
    if os.path.exists(p):
        for q in json.load(io.open(p, encoding="utf-8")):
            w, lab = q.get("week"), q.get("weekLabel")
            if w and lab and w not in labels:
                labels[w] = lab
    return labels


def sortkey(name):
    m = re.match(r"^(\d+)(?:\.(\d+))?\s*-\s*", name)
    if m:
        return (0, int(m.group(1)), int(m.group(2) or 0), name)
    return (1, 0, 0, name)          # In-Class notes carry no number and sort last


def main():
    for slug, folder, weeks in BLOCKS:
        labels = week_labels(slug)
        out = {"block": slug, "weeks": []}
        for n in weeks:
            d = os.path.join(VAULT, folder, "Week %d" % n)
            files = [f for f in os.listdir(d)
                     if f.endswith(".md") and f != ("Week %d.md" % n)]
            files.sort(key=sortkey)
            lects = []
            for f in files:
                stem = f[:-3]
                m = re.match(r"^([\d.]+)\s*-\s*(.+)$", stem)
                num, name = (m.group(1), m.group(2)) if m else ("", stem)
                key = num or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
                lects.append({
                    "id": "%s-w%d-%s" % (slug, n, key),
                    "num": num or u"\u2014",
                    "name": name,
                    "hasNote": False,
                })
            out["weeks"].append({"n": n, "label": labels.get(n, "Week %d" % n),
                                 "lectures": lects})
        p = "fom/data/notes/%s.json" % slug
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(out, indent=1, ensure_ascii=False))
        total = sum(len(w["lectures"]) for w in out["weeks"])
        print("%-6s %d weeks  %3d lectures" % (slug, len(out["weeks"]), total))


if __name__ == "__main__":
    main()
