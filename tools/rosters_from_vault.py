# -*- coding: utf-8 -*-
"""Rebuild pom2/data/notes/<slug>.json as a bare lecture roster.

Every lecture in the block's vault folders lands here whether or not it has a
note, so the notes tab reads as a coverage map. charts_from_vault.py then folds
the notes that exist on top of this. The vault calls them charts; the site calls
them notes.
"""

import io, json, os, re

VAULT = os.environ.get(
    "POM2_VAULT", u"C:/Users/nsims/medwiki/01 - Lectures/99 - PoM 2")
BLOCKS = [
    ("endo",  u"01 - Endocrinology", [1, 2, 3]),
    ("repro", u"02 - Repro",         [4, 5, 6]),
    ("msk",   u"03 - MSK",           [7, 8, 9, 10, 11]),
    ("neuro", u"04 - Neuro",         [12, 13, 14, 15, 16]),
    ("psych", u"05 - Psych",         [17, 18, 19, 20]),
]


def week_labels(slug):
    """reuse the week headings the questions tab already shows, so both tabs
       name the same week the same way. A bare "Week N" (what an
       Off-curriculum question or a newly placed one carries) only counts when
       no question in that week has a fuller heading"""
    p = "pom2/data/questions/%s.json" % slug
    labels = {}
    if os.path.exists(p):
        for q in json.load(io.open(p, encoding="utf-8")):
            w, lab = q.get("week"), q.get("weekLabel")
            if not (w and lab):
                continue
            bare = re.match(r"^Week \d+$", lab) is not None
            if w not in labels or (re.match(r"^Week \d+$", labels[w]) and not bare):
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
        p = "pom2/data/notes/%s.json" % slug
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(out, indent=1, ensure_ascii=False))
        total = sum(len(w["lectures"]) for w in out["weeks"])
        print("%-6s %d weeks  %3d lectures" % (slug, len(out["weeks"]), total))


if __name__ == "__main__":
    main()
