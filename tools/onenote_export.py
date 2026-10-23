# -*- coding: utf-8 -*-
"""Turn each chart in pom2/data/notes into a OneNote-ready HTML document.

OneNote pages are created by POSTing a *whole* HTML document to the Graph API:
partial markup or plain text either fails silently or lands malformed. So this
writes one complete document per chart into build/onenote/, ready to be posted
as-is (or opened in a browser and pasted, if the Graph route is unavailable).

Two things do not survive the trip and are handled here rather than lost:

  * **CSS.** OneNote keeps a small set of inline styles and throws away
    stylesheets and class names, so every rule the site carries in pom2.css is
    re-stated inline on the element itself.
  * **Mermaid.** A pathway is a diagram on the site and OneNote cannot draw one,
    so the graph is flattened into its edges, one arrow per line. Structure is
    kept; the picture is not.

Run after charts_from_vault.py, which is what puts the charts in pom2/data/notes.
"""

import io, json, os, re, sys

OUT = os.environ.get("POM2_ONENOTE_OUT", os.path.join("build", "onenote"))

BLOCKS = ["endo", "repro", "msk", "neuro", "psych"]

# inline equivalents of the pom2.css rules a chart actually uses
S_TABLE = ("border-collapse:collapse;width:100%;"
           "font-family:Calibri,sans-serif;font-size:11pt")
S_TH = ("border:1px solid #b9c2cc;padding:5px 8px;background:#eef2f6;"
        "text-align:left;vertical-align:top")
S_TD = "border:1px solid #b9c2cc;padding:5px 8px;vertical-align:top"
S_LEAD = "font-family:Calibri,sans-serif;font-size:11pt;margin:14px 0 4px 0"
S_BODY = "font-family:Calibri,sans-serif;font-size:11pt"
S_NOTE = ("font-family:Calibri,sans-serif;font-size:11pt;"
          "background:#f5f7fa;padding:6px 10px;margin:8px 0")
S_KEYS = "font-family:Calibri,sans-serif;font-size:11pt;background:#fff8e1;padding:6px 10px"
S_WL = "color:#2f5d8a"          # what .wl looks like on the site, near enough
S_PATH = ("font-family:Consolas,monospace;font-size:10pt;"
          "background:#f5f7fa;padding:6px 10px;margin:8px 0")


def unwrap(s):
    """Class names mean nothing to OneNote; give the spans their colour back."""
    s = re.sub(r'<span class="wl">', '<span style="%s">' % S_WL, s or u"")
    s = re.sub(r'<code>', '<span style="font-family:Consolas,monospace">', s)
    s = s.replace(u"</code>", u"</span>")
    return s


# ---------- mermaid -> arrows ----------

NODE = re.compile(r'([A-Za-z0-9_]+)\s*(?:\[\"(.*?)\"\]|\{\"(.*?)\"\}|\[(.*?)\]|\{(.*?)\})')
EDGE = re.compile(r'([A-Za-z0-9_]+)\s*-->\s*(?:\|\"?(.*?)\"?\|\s*)?([A-Za-z0-9_]+)')


def flatten(mermaid):
    """A flowchart as one line per edge: source -> (label) -> target.

    Labels are read from wherever the node is first declared, since mermaid
    declares a node once and refers to it by id afterwards. A node nobody
    labelled keeps its id, which is at least a stable handle.
    """
    label = {}
    for m in NODE.finditer(mermaid):
        text = next((g for g in m.groups()[1:] if g), None)
        if text and m.group(1) not in label:
            label[m.group(1)] = re.sub(r"<br\s*/?>", u" ", text).strip()

    # a node is declared and used in the same breath - A["..."] --> B["..."] -
    # and the bracket sits between the id and the arrow, so read the labels
    # first and then reduce every declaration back to its bare id
    bare = NODE.sub(lambda m: m.group(1) + u" ", mermaid)

    lines = []
    for m in EDGE.finditer(bare):
        src, via, dst = m.group(1), (m.group(2) or u"").strip(), m.group(3)
        arrow = u" --(%s)--> " % via if via else u" --> "
        lines.append(label.get(src, src) + arrow + label.get(dst, dst))
    return lines


# ---------- blocks -> html ----------

def table(b):
    out = []
    if b.get("lead"):
        out.append(u'<div style="%s">%s</div>' % (S_LEAD, unwrap(b["lead"])))
    out.append(u'<table border="1" style="%s"><tr>' % S_TABLE)
    for c in b["cols"]:
        out.append(u'<td style="%s">%s</td>' % (S_TH, unwrap(c)))
    out.append(u"</tr>")
    # a blank first cell means the row belongs to the group named above it, the
    # same rule the site reads, so the label spans its group rather than
    # repeating. First column only.
    span, at = {}, None
    for i, row in enumerate(b["rows"]):
        if at is not None and not row[0].strip():
            span[at] += 1
        else:
            at = i
            span[i] = 1
    for i, row in enumerate(b["rows"]):
        out.append(u"<tr>")
        for j, cell in enumerate(row):
            if j == 0:
                if i not in span:
                    continue
                n = span[i]
                out.append(u'<td style="%s"%s>%s</td>' % (
                    S_TD, u' rowspan="%d"' % n if n > 1 else u"", unwrap(cell)))
                continue
            out.append(u'<td style="%s">%s</td>' % (S_TD, unwrap(cell)))
        out.append(u"</tr>")
    out.append(u"</table>")
    return u"".join(out)


def block(b):
    kind = b.get("t")
    if kind == "table":
        return table(b)
    if kind == "pathway":
        lines = flatten(b.get("mermaid", u""))
        body = u"<br>".join(lines) or u"(pathway could not be read)"
        return u'<div style="%s">%s</div>' % (S_PATH, body)
    if kind == "callout":
        title = b.get("title")
        head = u"<p><strong>%s</strong></p>" % title if title else u""
        return u'<div style="%s">%s%s</div>' % (S_NOTE, head, unwrap(b.get("html", u"")))
    if kind == "note":
        return u'<div style="%s">%s</div>' % (S_NOTE, unwrap(b.get("html", u"")))
    return u'<div style="%s">%s</div>' % (S_BODY, unwrap(b.get("html", u"")))


def document(lec, week):
    """One page: title, framing, the blocks in source order, key points last.

    Same order the site reads them in, because the sentence above a table is
    the reason the table is there.
    """
    parts = [u'<div style="%s"><strong>%s</strong> &middot; %s</div>'
             % (S_BODY, week["label"], lec["name"])]
    if lec.get("framing"):
        parts.append(u'<div style="%s">%s</div>' % (S_BODY, unwrap(lec["framing"])))
    for b in lec.get("blocks", []):
        parts.append(block(b))
    if lec.get("keypoints"):
        parts.append(u'<div style="%s"><p><strong>Key points</strong></p>%s</div>'
                     % (S_KEYS, unwrap(lec["keypoints"])))

    title = lec.get("title") or lec["name"]
    return (u"<html><head><meta http-equiv=\"Content-Type\" "
            u"content=\"text/html; charset=utf-8\"/><title>%s - %s</title></head>"
            u"<body>%s</body></html>" % (lec["num"], title, u"".join(parts)))


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    written = []
    for slug in BLOCKS:
        path = "pom2/data/notes/%s.json" % slug
        if not os.path.exists(path):
            continue
        data = json.load(io.open(path, encoding="utf-8"))
        for week in data["weeks"]:
            for lec in week["lectures"]:
                if not lec.get("hasNote"):
                    continue
                name = "%s.html" % lec["id"]
                io.open(os.path.join(OUT, name), "w", encoding="utf-8").write(
                    document(lec, week))
                written.append((lec["id"], lec["num"], lec.get("title") or lec["name"]))

    for wid, num, title in written:
        sys.stdout.write("%-14s %s - %s\n" % (wid, num, title.encode("ascii", "replace").decode()))
    sys.stdout.write("%d chart(s) -> %s\n" % (len(written), OUT))


if __name__ == "__main__":
    main()
