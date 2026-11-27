"""Take the High-yield and Exam Q pills out of exported Anki decks.

The decks are exported from a personal collection whose card templates carry a
"hy-badge" block: a gold "High-yield" pill (and on some note types a blue
"Exam Q" pill) that shows on any card tagged #HighYield. Those labels are one
student's own study marks, so they are not published. This removes the block
from every card template and drops every #HighYield tag, leaving the cards
themselves unchanged.

    python tools/strip_anki_pills.py pom2/anki/*.apkg

tools/build_anki.py runs it on every deck it exports, so a re-export cannot
bring the pills back.
"""
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import zipfile

BADGE = re.compile(r"<!-- hy-badge -->.*?<!-- /hy-badge -->\n?", re.S)
COLLECTIONS = ("collection.anki21", "collection.anki2")


def is_label(tag):
    return "#highyield" in tag.lower()


def strip_collection(path):
    """Strip one collection file in place; return (templates, notes) changed."""
    db = sqlite3.connect(path)
    now = int(time.time())
    row = db.execute("select models from col").fetchone()
    models = json.loads(row[0]) if row and row[0] else {}
    tchanged = 0
    for m in models.values():
        hit = False
        for t in m.get("tmpls", []):
            for side in ("qfmt", "afmt", "bqfmt", "bafmt"):
                if t.get(side) and BADGE.search(t[side]):
                    t[side] = BADGE.sub("", t[side])
                    hit = True
        if hit:
            m["mod"] = now
            tchanged += 1
    if tchanged:
        db.execute("update col set models = ?", (json.dumps(models),))
    nchanged = 0
    rows = db.execute("select id, tags from notes where lower(tags) like '%#highyield%'").fetchall()
    for nid, tags in rows:
        kept = [t for t in tags.split() if not is_label(t)]
        db.execute("update notes set tags = ?, mod = ? where id = ?",
                   ((" %s " % " ".join(kept)) if kept else "", now, nid))
        nchanged += 1
    # Tags registered on the collection itself, so the tag list carries no trace.
    try:
        reg = json.loads(db.execute("select tags from col").fetchone()[0] or "{}")
        reg = {k: v for k, v in reg.items() if not is_label(k)}
        db.execute("update col set tags = ?", (json.dumps(reg),))
    except (sqlite3.Error, TypeError, ValueError):
        pass
    db.commit()
    db.execute("vacuum")
    db.close()
    return tchanged, nchanged


def strip_apkg(apkg):
    """Rewrite one .apkg with its pills removed; return (templates, notes)."""
    with zipfile.ZipFile(apkg) as z:
        members = [(i, z.read(i.filename)) for i in z.infolist()]
    total_t = total_n = 0
    out = []
    for info, data in members:
        if info.filename in COLLECTIONS:
            fd, tmp = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            with open(tmp, "wb") as f:
                f.write(data)
            t, n = strip_collection(tmp)
            total_t, total_n = total_t + t, total_n + n
            with open(tmp, "rb") as f:
                data = f.read()
            os.remove(tmp)
        out.append((info, data))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for info, data in out:
            z.writestr(info, data, compress_type=info.compress_type)
    with open(apkg, "wb") as f:
        f.write(buf.getvalue())
    return total_t, total_n


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: strip_anki_pills.py <deck.apkg> [...]")
    for p in sys.argv[1:]:
        t, n = strip_apkg(p)
        print("%s  %d templates, %d notes untagged" % (p, t, n))


if __name__ == "__main__":
    main()
