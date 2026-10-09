# -*- coding: utf-8 -*-
"""Lift the Nicole-format chart out of the top of each PoM 2 lecture note and
fold it into pom2/data/notes/<slug>.json.
The vault calls them charts; the site calls them notes.

The chart region is everything between the note's frontmatter and the first
closing --- . Its blocks are kept in source order: the sentence that leads into
a table is part of the argument, so it travels with the table rather than being
hoisted into a separate field.
"""

import io, json, os, re, sys

VAULT = os.environ.get(
    "POM2_VAULT", u"C:/Users/nsims/medwiki/01 - Lectures/99 - PoM 2")
BLOCK_FOLDER = {
    "endo": u"01 - Endocrinology",
    "repro": u"02 - Repro",
    "msk": u"03 - MSK",
    "neuro": u"04 - Neuro",
    "psych": u"05 - Psych",
}

PIPE = u"\x00"   # stands in for an escaped \| while a table row is split

# An Obsidian embed alone on its line is a figure. Alone is the whole test: an
# embed with prose around it is a sentence that mentions a picture, not a block.
IMG_EXT = u"png|jpe?g|gif|webp|svg"
FIG_LINE = re.compile(
    r"^\s*!\[\[\s*([^\]\|]+?\.(?:%s))\s*(?:\|\s*([^\]]*?)\s*)?\]\]\s*$" % IMG_EXT, re.I)

# A section heading inside the chart. The outline notes walk a lecture in its
# own order, one concept per section; "# Overview chart:" is the title, not one.
HEAD_LINE = re.compile(r"^#{2,4}\s+\S")

# written by tools/figures.py, which owns Pillow so the rebuild scripts do not
FIGURES_PATH = "pom2/data/figures.json"
FIGURES = {}


# ---------- inline markdown -> html ----------

def inline(s):
    s = s.replace(PIPE, u"|")

    # a bare & is invalid html; the entities already in the source stay put
    s = re.sub(r"&(?!#?\w+;)", "&amp;", s)

    # [[target|alias]] and [[target]] - styled, not linked; there is nothing
    # on the public site for a vault wikilink to point at.
    # The lookbehind leaves ![[embeds]] alone: an image is a block, handled by
    # scan(), and without this the alias rule ate ![[x.png|600]] down to !600 -
    # the width hint kept as the visible text and the filename thrown away.
    s = re.sub(r"(?<!!)\[\[([^\]\|]+)\|([^\]]+)\]\]",
               lambda m: u'<span class="wl">%s</span>' % m.group(2).strip(), s)
    s = re.sub(r"(?<!!)\[\[([^\]\|]+)\]\]",
               lambda m: u'<span class="wl">%s</span>' % m.group(1).strip(), s)

    # [text](url) - the charts cite trials and guidelines and those should stay
    # reachable; every other name on the page is deliberately not a link.
    # The inner alternation is there because a Lancet PII carries its own
    # parentheses - PIIS0140-6736(98)07019-6 - and a lazy match loses the tail.
    s = re.sub(r"\[([^\]]+)\]\((https?://(?:[^()\s]|\([^()\s]*\))+)\)",
               r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', s)

    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)

    # ** has to be read before *, but a lazy ** pass swallows the opening star
    # of an inner pair: **a *b*** came out as <strong>a <em>b</strong></em>.
    # Park each strong run instead, emphasise its contents and the rest of the
    # line alike, then put the tags back.
    strong = []

    def park(m):
        strong.append(m.group(1))
        return u"\x01%d\x02" % (len(strong) - 1)

    # the lookahead keeps the closing run of **a *b*** intact: without it the
    # pass stops at the first two of those three stars and strands the third
    s = re.sub(r"\*\*(.+?)\*\*(?!\*)", park, s, flags=re.S)

    def emphasise(t):
        # ==text== is the vault's highlighter, and in a chart it means one
        # thing only: this is what the lecture's learning objectives ask for.
        # The class keeps it apart from the search's mark.hit.
        t = re.sub(r"==(.+?)==", r'<mark class="lo">\1</mark>', t, flags=re.S)
        # intraword emphasis is real in these notes - ego*dystonic* is one word
        # on the page - so only a neighbouring star disqualifies a pair, not a
        # neighbouring letter
        return re.sub(r"(?<!\*)\*([^\*\n]+)\*(?!\*)", r"<em>\1</em>", t)

    s = emphasise(s)
    for i, inner in enumerate(strong):
        s = s.replace(u"\x01%d\x02" % i, u"<strong>%s</strong>" % emphasise(inner))
    return s.strip()


def para(lines):
    return u"".join(u"<p>%s</p>" % inline(l.strip()) for l in lines if l.strip())


def bullets(lines):
    """A markdown list, nested by indent: the outline notes hang the
    indications, contraindications and complications of a procedure under it."""
    items = []                       # (depth, html)
    indents = []
    for l in lines:
        if not l.strip():
            continue
        m = re.match(r"^(\s*)[-*]\s+(.*)$", l.expandtabs(4))
        if not m:
            continue
        width = len(m.group(1))
        while indents and width < indents[-1]:
            indents.pop()
        if not indents or width > indents[-1]:
            indents.append(width)
        items.append((len(indents) - 1, inline(m.group(2))))

    out, depth = [u"<ul>"], 0
    for i, (d, h) in enumerate(items):
        d = min(d, depth + 1)        # an item cannot open two levels at once
        if i and d > depth:
            out[-1] = out[-1][:-len(u"</li>")] + u"<ul>"
        while depth > d:
            out.append(u"</ul></li>")
            depth -= 1
        depth = d
        out.append(u"<li>%s</li>" % h)
    while depth > 0:
        out.append(u"</ul></li>")
        depth -= 1
    out.append(u"</ul>")
    return u"".join(out)


# ---------- block scanner ----------

def scan(region):
    lines = region.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("```"):
                j += 1
            out.append(("fence", lines[i:j + 1]))
            i = j + 1
            continue
        if ln.lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            out.append(("table", lines[i:j]))
            i = j
            continue
        if ln.lstrip().startswith(">"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith(">"):
                j += 1
            out.append(("callout", lines[i:j]))
            i = j
            continue
        if FIG_LINE.match(ln):
            out.append(("figure", [ln]))
            i += 1
            continue
        if HEAD_LINE.match(ln):
            out.append(("heading", [ln]))
            i += 1
            continue
        if not ln.strip():
            i += 1
            continue
        j = i
        while j < len(lines):
            t = lines[j]
            if not t.strip() or t.lstrip()[:1] in ("|", ">") or t.strip().startswith("```"):
                break
            if (FIG_LINE.match(t) or HEAD_LINE.match(t)) and j > i:
                break                     # a figure or heading ends the paragraph above it
            j += 1
        out.append(("text", lines[i:j]))
        i = j
    return out


def parse_figure(line):
    """![[name.png]], ![[name.png|520]] or ![[name.png|a caption]].

    The vault already overloads the pipe both ways - "adrenal crisis card.png|300"
    is a width, "pheochromocytoma locations.png|areas in red indicate ..." is a
    caption - so the number decides which it is. That is her existing habit, not
    a new convention.
    """
    m = FIG_LINE.match(line)
    if not m:
        return None
    name = m.group(1).strip()
    hint = (m.group(2) or u"").strip()

    fig = FIGURES.get(name)
    if not fig:
        sys.stderr.write(
            "no figure asset for %r - run tools/figures.py\n" % name)
        return None

    out = {"t": "figure", "src": fig["src"], "alt": name,
           "w": fig["w"], "h": fig["h"]}
    if hint.isdigit():
        out["width"] = int(hint)
    elif hint:
        out["cap"] = inline(hint)
    return out


def parse_table(lines):
    rows = []
    for l in lines:
        raw = l.strip().replace(u"\\|", PIPE)
        cells = [c.strip() for c in raw.strip("|").split("|")]
        if cells and all(re.match(r"^:?-{2,}:?$", c or "-") and set(c) <= set("-: ")
                         for c in cells if c != ""):
            continue                      # the |---|---| separator row
        rows.append(cells)
    if not rows:
        return None
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    return {"cols": [inline(c) for c in rows[0]],
            "rows": [[inline(c) for c in r] for r in rows[1:]]}


def parse_callout(lines):
    first = re.sub(r"^\s*>\s?", "", lines[0])
    m = re.match(r"^\[!(\w+)\][-+]?\s*(.*)$", first)
    kind = (m.group(1).lower() if m else "note")
    title = inline(m.group(2).strip()) if m else ""
    body = [re.sub(r"^\s*>\s?", "", l) for l in lines[1:]]
    bl = [l for l in body if l.strip()]
    if bl and all(re.match(r"^\s*[-*]\s+", l) for l in bl):
        return {"t": "callout", "kind": kind, "title": title, "html": bullets(bl)}
    return {"t": "callout", "kind": kind, "title": title, "html": para(bl)}


# ---------- one note ----------

def chart_region(src):
    """Everything between the frontmatter and the first closing ---, or None."""
    parts = src.split("\n---")
    if len(parts) < 2 or "# Overview chart" not in parts[1]:
        return None
    return parts[1]


def chart_of(path):
    region = chart_region(io.open(path, encoding="utf-8").read())
    if region is None:
        return None

    blocks = scan(region)

    out = {}
    pending = None          # a text block waiting to see if a table follows it
    body = []

    def flush():
        """a lead-in with no table under it is a standalone note line"""
        if pending is None:
            return
        kind, lines = pending
        if kind == "list":
            body.append({"t": "list", "html": bullets(lines)})
        else:
            body.append({"t": "note", "html": para(lines)})

    for kind, lines in blocks:
        if kind == "text":
            head = lines[0].strip()
            m = re.match(r"^#\s*Overview chart:\s*(.+)$", head)
            if m:
                out["title"] = re.sub(r"</?u>", "", m.group(1)).strip()
                continue
            if head.lower().startswith("**high-yield discriminators"):
                flush(); pending = None
                # the label is drawn by the page, so it does not travel in the text
                kp = para(lines)
                kp = kp.replace("<p><strong>High-yield discriminators:</strong> ", "<p>", 1)
                kp = kp.replace("<p><strong>High-yield discriminators:</strong>", "<p>", 1)
                out["keypoints"] = kp.strip()
                continue
            # a figure above the framing line is still "on top of the chart",
            # so it must not cost the paragraph its framing slot
            if "framing" not in out and not [b for b in body if b["t"] != "figure"]:
                out["framing"] = para(lines)
                continue
            flush()
            stripped = [l for l in lines if l.strip()]
            is_list = bool(stripped) and all(re.match(r"^\s*[-*]\s+", l) for l in stripped)
            pending = ("list" if is_list else "text", lines)
            continue

        if kind == "table":
            spec = parse_table(lines)
            lead = None
            if pending is not None and pending[0] == "text":
                lead = para(pending[1])
                pending = None
            else:
                flush(); pending = None
            if spec:
                t = {"t": "table"}
                if lead:
                    t["lead"] = lead
                t.update(spec)
                body.append(t)
            continue

        flush(); pending = None
        if kind == "heading":
            # written as PoM 1's notes write a section: an <h5>, which the
            # page already styles and coverage.py already reads as a heading
            text = re.sub(r"^#+\s*", "", lines[0].strip())
            body.append({"t": "note", "html": u"<h5>%s</h5>" % inline(text)})
            continue
        if kind == "figure":
            fig = parse_figure(lines[0])
            if fig:
                body.append(fig)
            continue
        if kind == "fence":
            inner = [l for l in lines[1:-1]]
            if lines[0].strip().lower().startswith("```mermaid"):
                body.append({"t": "pathway", "mermaid": u"\n".join(inner).strip()})
            continue
        if kind == "callout":
            body.append(parse_callout(lines))
            continue

    flush()
    if body:
        out["blocks"] = body
    return out


# ---------- fold into the roster ----------

DRAFT_TEXT = ("Built from upper-year notes. "
              "Not yet checked against this year's lecture slides.")


def is_draft(chart):
    """True when the chart opens with the vault's > [!warning] Draft callout."""
    blocks = chart.get("blocks") or []
    return bool(blocks) and blocks[0].get("t") == "callout" \
        and blocks[0].get("kind") == "warning" and blocks[0].get("title") == "Draft"


def load_figures():
    """The figure manifest, or nothing - a chart with no pictures needs none."""
    if not os.path.exists(FIGURES_PATH):
        return {}
    return json.load(io.open(FIGURES_PATH, encoding="utf-8"))


def main(slugs):
    FIGURES.update(load_figures())
    for slug in slugs:
        p = "pom2/data/notes/%s.json" % slug
        doc = json.load(io.open(p, encoding="utf-8"))
        folder = os.path.join(VAULT, BLOCK_FOLDER[slug])
        found = drafts = 0
        for w in doc["weeks"]:
            wd = os.path.join(folder, "Week %d" % w["n"])
            for lec in w["lectures"]:
                stem = ("%s - %s" % (lec["num"], lec["name"])) if lec["num"] != u"\u2014" else lec["name"]
                f = os.path.join(wd, stem + ".md")
                if not os.path.exists(f):
                    sys.stderr.write("missing: %s\n" % f)
                    continue
                ch = chart_of(f)
                if not ch:
                    lec["hasNote"] = False
                    continue
                lec["hasNote"] = True
                if is_draft(ch):
                    ch["blocks"] = ch["blocks"][1:]
                    drafts += 1
                lec.update(ch)
                found += 1
        # One banner at the top of the notes tab, not a copy on every note.
        # The callouts stay in the vault, where they mark which notes still
        # need checking against this year's slides.
        if drafts:
            doc["draft"] = DRAFT_TEXT
        else:
            doc.pop("draft", None)
        io.open(p, "w", encoding="utf-8", newline="\n").write(
            json.dumps(doc, indent=1, ensure_ascii=False))
        total = sum(len(w["lectures"]) for w in doc["weeks"])
        print("%-6s %3d/%d written" % (slug, found, total))


if __name__ == "__main__":
    main(sys.argv[1:] or ["endo", "repro", "msk", "neuro", "psych"])
