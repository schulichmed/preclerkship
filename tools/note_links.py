# -*- coding: utf-8 -*-
"""Link the terms in each explanation to the lecture note that teaches them.

Purpose: find, in every question's written explanation, the terms a lecture
         note sets in bold (GLP-1, Virchow's triad, hyperkalemia) and record
         which note each one belongs to, so the explanation can open that note
         in place, scrolled to the term.
Author:  Ashish Saragadam
Date:    2026-10-16
Input:   each course's data/notes/*.json and data/questions/*.json
Output:  the same question JSON, each question gaining `noteTerms`

Run from the repo root, before build_pages.py (the page stamps the bank's
content hash, so a rewritten bank needs a rebuild to be served).

    python tools/note_links.py            # write
    python tools/note_links.py --dry-run  # report coverage, touch nothing

`noteTerms` is a list of [text, block slug, lecture id, week, note term]:
`text` is the words exactly as the explanation has them, inside one run of
text (never across a tag), and `note term` is the bold the note has, which
the dialog scrolls to. quiz.js wraps the first occurrence of `text` in the
rendered explanation; the explanation's HTML itself is never touched, so this
can be re-run, or the field deleted, without anything else changing.

A wrong link is worse than none: it sends someone to the wrong material with
the portal's authority behind it. So a term is linked only when
  - it is bold in a note, one to four words, and four characters or more
    unless it is an acronym (GIP, DKA), which then matches case-sensitively;
  - it is not ordinary vocabulary: at least one of its words is not in
    tools/common_words.txt (so "Next step" and "Principle" stay plain), and
    it turns up in the text of no more than SPREAD of a course's notes (or
    five notes, whichever is more), since a term every lecture uses is not
    one lecture's to own;
  - its home is clear: the lecture the question already reviews, else the only
    note that bolds it, else the one that bolds it at least twice as often as
    any other. Anything else is skipped.
Each explanation links a term once, and at most MAX_LINKS terms.

The vault's own wiki-links, which arrive as <span class="wl"> and have shown
as links that go nowhere, are the exception: an author already said those are
terms, so they skip the everyday-word, label and spread tests (but not the
clear-home one), and one that names a lecture ("15 - Abnormal Uterine
Bleeding", "In-Class - Amenorrhea") opens that lecture's note.
"""

import argparse
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_WORDS = 4
MAX_LINKS = 6
SPREAD = 0.05
# Bold that is a word of the explanation's own furniture, not a term
STOP = {"answer", "correct", "incorrect", "true", "false", "none", "both",
        "neither", "always", "never", "not", "only", "most", "least", "first",
        "key", "note", "notes", "example", "examples", "mnemonic", "remember",
        "important", "high yield", "high-yield", "exception", "increased",
        "decreased", "normal", "abnormal", "yes", "no"}

TAG = re.compile(r"<[^>]+>")
STRONG = re.compile(r"<strong>(.*?)</strong>", re.S)
# A word: letters and digits, with inner hyphens, apostrophes and plus signs
# kept so GLP-1, Virchow's and CD4+ are one word each
WORD = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9+]|['’\-](?=[A-Za-z0-9]))*")
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "common_words.txt"),
          encoding="utf-8") as _f:
    COMMON = {w.strip() for w in _f if w.strip() and not w.startswith("#")}
# A stretch of words with nothing but spaces, hyphens and apostrophes between
# them: a term never reaches across a bracket, comma or quotation mark
CLAUSE = re.compile(r"[\w\s'\u2019+\-]+")
# Tags whose text is not prose to link into
SKIP_IN = {"a", "button", "code", "sup", "sub", "script", "style"}


def strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from strings(v)


def plain(s):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub(" ", s))).strip()


def is_acronym(t):
    """GIP, DKA, GLP-1, CD4+: two capitals and no lowercase word."""
    letters = re.sub(r"[^A-Za-z]", "", t)
    return (len(re.findall(r"[A-Z]", t)) >= 2 and letters == letters.upper()
            and not everyday(WORD.findall(t)))


def fold(w):
    """A word for matching: lower case, a plural s or es dropped."""
    w = w.lower().replace("’", "'")
    if len(w) > 4 and w.endswith("es") and not w.endswith("ses"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss") and not w.endswith("us"):
        return w[:-1]
    return w


def everyday(words):
    """True when every word is ordinary English (or a number)."""
    for w in words:
        for part in w.lower().replace("\u2019", "'").split("-"):
            stems = {part, fold(part), part[:-1] if part.endswith("s") else part}
            if not (stems & COMMON
                    or re.fullmatch(r"[0-9]+(?:st|nd|rd|th)?", part)):
                return False
    return True


def key_of(words, acr):
    return ("A",) + tuple(w.replace("’", "'") for w in words) if acr \
        else tuple(fold(w) for w in words)


def lectures(course, every=False):
    """(slug, week, lecture) for every lecture with a written note (or, with
    every, every lecture on the roster), in roster order."""
    out = []
    for slug, _n, _name, _weeks in course["blocks"]:
        p = os.path.join(ROOT, course["slug"], "data", "notes", slug + ".json")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        for w in data.get("weeks") or []:
            for lec in w.get("lectures") or []:
                if lec.get("id") and (every or lec.get("hasNote") is True):
                    out.append((slug, w.get("n"), lec))
    return out


def scan(words, index):
    """The terms in a run of words, longest first, left to right, no overlaps.
    Yields (start, end, key)."""
    i = 0
    while i < len(words):
        hit = None
        for n in range(min(MAX_WORDS, len(words) - i), 0, -1):
            span = words[i:i + n]
            for acr in (True, False):
                k = key_of(span, acr)
                if k in index:
                    hit = (i, i + n, k)
                    break
            if hit:
                break
        if hit:
            yield hit
            i = hit[1]
        else:
            i += 1


def build_index(course):
    """(index, week, loose, titles) for one course.

    index:  key -> {"surface", "homes": {(slug, id): count}, "label"}, the
            terms that pass every test below, matched anywhere in prose
    week:   lecture id -> its week
    loose:  the same shape, every bold in the notes before those tests; only
            an author's own wiki-link (a .wl span) is looked up here, since
            the author already said that word is a term
    titles: lecture name, lower case -> [(slug, id, week, num)] for every
            lecture that opens a note (its own, or the one it is covered by)
    """
    lecs = lectures(course)
    index, week, loose = {}, {}, {}
    for slug, w, lec in lecs:
        week[lec["id"]] = w
        for text in strings([lec.get("framing"), lec.get("keypoints"), lec.get("blocks")]):
            for m in STRONG.finditer(text):
                t = plain(m.group(1)).strip(" .,:;()[]-\u2013\u2014")
                words = WORD.findall(t)
                if not words or len(words) > MAX_WORDS or " ".join(words) != t:
                    continue
                acr = is_acronym(t)
                if t.lower() in STOP or (len(t) < 3 and not acr) or t.isdigit():
                    continue
                k = key_of(words, acr)
                e = loose.setdefault(k, {"surface": t, "homes": {}})
                e["homes"][(slug, lec["id"])] = e["homes"].get((slug, lec["id"]), 0) + 1
                if (len(t) < 4 and not acr) or (not acr and everyday(words)):
                    continue
                e = index.setdefault(k, {"surface": t, "homes": {}, "label": False})
                e["homes"][(slug, lec["id"])] = e["homes"].get((slug, lec["id"]), 0) + 1
                e["label"] = e["label"] or labels(text, m)
    # One word in bold mid-sentence is emphasis ("the T wave inverts"); one
    # word heading a list item or cell, or followed by a colon or a bracket,
    # is a term being defined. A single word is kept only as the latter.
    for k in [k for k, e in index.items()
              if len(k) == 1 and not e["label"]]:
        del index[k]

    # A term that is some lecture's whole title belongs to that lecture, as
    # in "From 11 - Colorectal Cancer Screening": linked there if it has a
    # note, and not at all if it has none, rather than to a neighbour's
    titles = {}
    for slug, w, lec in lectures(course, every=True):
        if lec.get("hasNote") is True or lec.get("coveredBy"):
            titles.setdefault(plain(lec.get("name") or "").lower(), []).append(
                (slug, lec["id"], w, str(lec.get("num") or "")))
            week.setdefault(lec["id"], w)
        words = WORD.findall(plain(lec.get("name") or ""))
        k = key_of(words, False) if 0 < len(words) <= MAX_WORDS else None
        if k in index:
            if lec.get("hasNote") is True:
                index[k]["homes"] = {(slug, lec["id"]): 1}
            else:
                del index[k]

    # spread: how many notes use the term anywhere in their text
    limit = max(5, int(len(lecs) * SPREAD))
    seen = {}
    for slug, w, lec in lecs:
        words = WORD.findall(plain(" ".join(strings(lec))))
        for _s, _e, k in set(scan(words, index)):
            seen[k] = seen.get(k, 0) + 1
    for k in [k for k in index if seen.get(k, 0) > limit]:
        del index[k]
    return index, week, loose, titles


def labels(text, m):
    """True when the bold at m reads as a label: it opens its element, or a
    colon, dash, bracket or equals sign follows it."""
    before = text[:m.start()].rstrip()
    after = text[m.end():].lstrip()
    return (not before or before.endswith(">") or not after
            or after[0] in ":(\u2014\u2013=<" or after.startswith("- "))


def home(entry, slug, reviewed, single, weeks=()):
    homes = entry["homes"]
    if single:
        # one plain word ("Potassium", "Squamous") means what the block it
        # is read in means by it; another block's note on it is a stretch
        homes = {h: n for h, n in homes.items() if h[0] == slug}
        # and, when the question names its lecture, what that lecture's week
        # means by it: "orthosis" in a cubital tunnel answer is not the ankle
        # lecture's orthosis two weeks on
        if weeks:
            homes = {h: n for h, n in homes.items() if h[1] in reviewed or weeks(h[1])}
        if not homes:
            return None
    mine = [h for h in homes if h[1] in reviewed]
    if len(mine) == 1:
        return mine[0]
    if mine:
        return None
    if len(homes) == 1:
        return next(iter(homes))
    ranked = sorted(homes.items(), key=lambda kv: -kv[1])
    if ranked[0][1] >= 2 * ranked[1][1]:
        return ranked[0][0]
    return None


def text_runs(answer):
    """The answer's text as (text, wl) pairs, one per stretch between tags,
    skipping the inside of links and code; wl is True for the whole text of
    a <span class="wl">, the wiki-links the vault's [[...]] became. Entities
    are decoded, as the browser would."""
    depth, runs, wl = 0, [], None
    parts = re.split(r"(<[^>]+>)", answer or "")
    for i, part in enumerate(parts):
        if part.startswith("<"):
            m = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
            if m and m.group(2).lower() in SKIP_IN and not part.endswith("/>"):
                depth += -1 if m.group(1) else 1
                depth = max(depth, 0)
            continue
        if depth == 0 and part.strip():
            # a wiki-link is one run between its own open and close tags
            whole = (i >= 1 and parts[i - 1] == '<span class="wl">'
                     and i + 1 < len(parts) and parts[i + 1] == "</span>")
            runs.append((html.unescape(part), whole))
    return runs


def reviewed_ids(q, week):
    out = set()
    for r in q.get("review") or []:
        n, w = str(r.get("n") or ""), r.get("w")
        # a split lecture's part ("07.2") is a lecture of its own
        if not re.fullmatch(r"\d+(?:\.\d+)?", n):
            continue
        for lid, lw in week.items():
            if lw == w and lid.endswith("-w%s-%s" % (w, n)):
                out.add(lid)
    return out


def title_target(text, titles):
    """The lecture a wiki-link like "15 - Abnormal Uterine Bleeding" or
    "In-Class - Amenorrhea" names, when exactly one lecture answers to it."""
    m = re.match(r"^(\d+(?:\.\d+)?)\s*[-\u2013]\s*(.+)$", text)
    num, name = (m.group(1), m.group(2)) if m else (None, text)
    found = titles.get(plain(name).lower()) or []
    if num is not None:
        found = [f for f in found if f[3] == num] or found
    return found[0] if len(found) == 1 else None


def wiki_link(text, slug, reviewed, index, loose, titles):
    """[text, block, id, week, bold] for a whole wiki-link span, or None."""
    t = text.strip()
    if titles:
        hit = title_target(t, titles)
        if hit:
            return [t, hit[0], hit[1], hit[2], ""], ("T", hit[1])
    words = WORD.findall(t)
    if not words or len(words) > MAX_WORDS:
        return None
    k = key_of(words, is_acronym(t))
    entry = index.get(k) or (loose or {}).get(k)
    h = entry and home(entry, slug, reviewed, len(k) == 1)
    if not h:
        return None
    return [t, h[0], h[1], None, entry["surface"]], k


def link_question(q, slug, index, week, loose=None, titles=None):
    reviewed = reviewed_ids(q, week)
    taught = {week.get(lid) for lid in reviewed}
    near = (lambda lid: week.get(lid) in taught) if reviewed else ()
    out, used = [], set()
    for run, wl in text_runs(q.get("answer")):
        if wl and len(out) < MAX_LINKS:
            got = wiki_link(run, slug, reviewed, index, loose, titles)
            if got and got[1] not in used:
                used.add(got[1])
                if got[0][3] is None:
                    got[0][3] = week.get(got[0][2])
                out.append(got[0])
                continue
        for clause in CLAUSE.finditer(run):
            base = clause.start()
            spans = [(base + m.start(), base + m.end(), m.group(0))
                     for m in WORD.finditer(clause.group(0))]
            for s, e, k in scan([sp[2] for sp in spans], index):
                if k in used or len(out) >= MAX_LINKS:
                    continue
                h = home(index[k], slug, reviewed, len(k) == 1, near)
                if not h:
                    continue
                used.add(k)
                text = run[spans[s][0]:spans[e - 1][1]]
                out.append([text, h[0], h[1], week.get(h[1]), index[k]["surface"]])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    for course in portal.COURSES:
        index, week, loose, titles = build_index(course)
        if not index:
            continue
        total = linked = links = 0
        for slug, _n, _name, _weeks in course["blocks"]:
            p = os.path.join(ROOT, course["slug"], "data", "questions", slug + ".json")
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as f:
                qs = json.load(f)
            for q in qs:
                terms = link_question(q, slug, index, week, loose, titles)
                total += 1
                if terms:
                    q["noteTerms"] = terms
                    linked += 1
                    links += len(terms)
                else:
                    q.pop("noteTerms", None)
            if not args.dry_run:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(json.dumps(qs, ensure_ascii=False))
        print("%s: %d terms; %d of %d explanations linked, %d links"
              % (course["slug"], len(index), linked, total, links))


if __name__ == "__main__":
    main()
