# -*- coding: utf-8 -*-
"""Export a block's Anki deck out of the live collection and into the repo.

Purpose: publish one block's cards as a downloadable .apkg, plus the manifest
         the block page renders its Anki tab from, so what is on the site and
         what is in the collection cannot drift.
Author:  Noor Sims
Date:    2026-09-25
Input:   a running Anki with AnkiConnect on 127.0.0.1:8765, and a deck name
Output:  <course>/anki/<block>.apkg and <course>/data/anki/<block>.json

Run from the repo root, with Anki open:

    python3 tools/build_anki.py pom2 endo "PoM2::Block 1"

A fourth argument marks the deck as a draft, and the Anki tab shows it as a
warning above the download - for a deck filed by lecture but not yet brought
up to date against this year's slides:

    python3 tools/build_anki.py pom2 msk "PoM2::Block 3" "Built from ..."

Scheduling is stripped on the way out. The due dates in the collection are one
person's review history; what is published is the cards, and whoever imports
them starts their own. Re-running overwrites both outputs, which is the point -
the deck on the site is whatever the collection said the last time this ran.
"""

import io, json, os, platform, subprocess, sys, tempfile, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strip_anki_pills import strip_apkg

ANKICONNECT = "http://127.0.0.1:8765"
EXPORT_NAME = "_anki_export.apkg"


def export_paths():
    """(path Anki writes the package to, path this script reads it back from).

    AnkiConnect writes the package itself, so the first path is a path on the
    machine Anki runs on. On Windows or a Mac running this script natively the
    two are the same temp file. Under WSL, Anki runs on Windows: the package
    goes to the Windows temp folder and is read back through /mnt/c, and the two
    spellings of the same file are not interchangeable.
    """
    if "microsoft" not in platform.uname().release.lower():
        local = os.path.join(tempfile.gettempdir(), EXPORT_NAME)
        return local, local
    win_tmp = subprocess.check_output(
        ["cmd.exe", "/c", "echo %TEMP%"], stderr=subprocess.DEVNULL
    ).decode("utf-8", "replace").strip()
    win_path = win_tmp + "\\" + EXPORT_NAME
    wsl_path = subprocess.check_output(["wslpath", "-u", win_path]).decode("utf-8").strip()
    return win_path, wsl_path


def ac(action, **params):
    """Call one AnkiConnect action, raising on the error field it returns."""
    req = urllib.request.Request(
        ANKICONNECT,
        json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8"),
        {"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=900))
    if r.get("error"):
        raise RuntimeError("AnkiConnect %s: %s" % (action, r["error"]))
    return r["result"]


def subdecks(root):
    """Every '<root>::Week n::NN - Lecture' deck, in collection order."""
    out = []
    for name in sorted(ac("deckNames")):
        if not name.startswith(root + "::"):
            continue
        tail = name[len(root) + 2:].split("::")
        if len(tail) == 2:
            out.append((name, tail[0], tail[1]))
    return out


def counts(deck):
    """Notes and cards in one deck."""
    return (len(ac("findNotes", query='deck:"%s"' % deck)),
            len(ac("findCards", query='deck:"%s"' % deck)))


def export(root, dest):
    """Export root and its subdecks to dest, without scheduling."""
    anki_path, local_path = export_paths()
    if not ac("exportPackage", deck=root, path=anki_path, includeSched=False):
        raise RuntimeError("exportPackage returned false for %r" % root)
    d = os.path.dirname(dest)
    if not os.path.isdir(d):
        os.makedirs(d)
    with open(local_path, "rb") as src, open(dest, "wb") as dst:
        dst.write(src.read())
    os.remove(local_path)
    # The collection's own High-yield / Exam Q pills and #HighYield tags are
    # personal study marks; the published copy goes out without them.
    strip_apkg(dest)
    return os.path.getsize(dest)


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit("usage: build_anki.py <course> <block> <deck name> [draft note]")
    course, block, root = sys.argv[1], sys.argv[2], sys.argv[3]
    draft = sys.argv[4] if len(sys.argv) == 5 else None

    apkg = os.path.join(course, "anki", "%s.apkg" % block)
    size = export(root, apkg)

    weeks, seen = [], {}
    for deck, week, lecture in subdecks(root):
        n, c = counts(deck)
        if week not in seen:
            seen[week] = {"week": week, "lectures": []}
            weeks.append(seen[week])
        seen[week]["lectures"].append(
            {"name": lecture, "notes": n, "cards": c})

    tn, tc = counts(root)
    man = {
        "deck": root,
        "file": "anki/%s.apkg" % block,
        "bytes": size,
        "notes": tn, "cards": tc,
        "weeks": weeks,
    }
    if draft:
        man["draft"] = draft

    out = os.path.join(course, "data", "anki", "%s.json" % block)
    d = os.path.dirname(out)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(man, ensure_ascii=False, indent=1, sort_keys=True) + u"\n")

    print("%s/%s  %d notes  %d cards  %.1f MB"
          % (course, block, tn, tc, size / 1048576.0))


if __name__ == "__main__":
    main()
