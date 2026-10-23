# -*- coding: utf-8 -*-
"""Apply hand-checked answer-key repairs to a course's question bank.

Purpose: a "The key looks wrong" flag tells the reader the source key is wrong,
         but the bank kept scoring against that key, so a reader who picked the
         lecture's answer was marked wrong. This applies the repairs listed in
         tools/key_fixes/<course>.json so the bank scores what the flag says.
Author:  Ella Boone (FoM class rep)
Date:    2026-10-14
Input:   <course>/data/questions/*.json and tools/key_fixes/<course>.json
Output:  the question files, rewritten in place

    python tools/key_fixes.py fom            # apply
    python tools/key_fixes.py fom --dry-run  # say what would change

Run it after the extractors, with the other repair passes
(question_figures.py, roman_items.py). It is idempotent: the source key is
saved once as "sourceKey", and a repaired question is recognised and left
alone on the next run.

WHAT AN ENTRY MAY SAY
---------------------
    "qid": {
      "correct":    ["A", "C"],   the key to score against
      "multi":      true,         answer it as select-all
      "convert":    "mcq",        make a self-marked question a scored one
      "unscorable": true,         no defensible key: show it, don't score it
                    false,        the lecture supplies the key the source left out
      "option":     {"B": "..."}, repair an option's text
      "options":    ["...", ...], replace every option, lettered A, B, C... in
                                  order (when the extractor split one option
                                  that wrapped onto a second line into two)
      "stem":       "<p>...</p>", replaces the stem (when its wording, not its key, was wrong)
      "lead":       "<p>...</p>", replaces the first paragraph of the answer
      "answer":     "<p>...</p>", replaces the whole answer (when the extractor glued
                                  another question's explanation onto this one)
      "why":        "..."         required: the lecture evidence, shown to readers
    }

Every repaired question keeps the source's key in view: its "The key looks
wrong" flag becomes a "Key corrected" note that names what the source said and
why it changed, so nothing is silently rewritten.
"""

import glob, html, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DONE = ("Key corrected", "Key repaired", "Not scored: no defensible key")


def letters(xs):
    return ", ".join(xs) if xs else "none"


def apply(q, fix):
    """Repair one question in place. Returns a list of what changed."""
    changed = []
    if "sourceKey" not in q:
        q["sourceKey"] = list(q.get("correct") or [])
    src = q["sourceKey"]

    if fix.get("convert") == "mcq" and (q.get("kind") != "mcq" or q.get("free")):
        q["kind"], q["free"] = "mcq", False
        changed.append("now scored")
    if "correct" in fix and q.get("correct") != fix["correct"]:
        q["correct"] = list(fix["correct"])
        changed.append("key %s -> %s" % (letters(src), letters(q["correct"])))
    if "multi" in fix and q.get("multi") != fix["multi"]:
        q["multi"] = fix["multi"]
        changed.append("select-all" if fix["multi"] else "single answer")
    if len(q.get("correct") or []) > 1 and not q.get("multi"):
        q["multi"] = True
        changed.append("select-all")
    if fix.get("unscorable") and not q.get("unscorable"):
        q["unscorable"] = True
        changed.append("not scored")
    if fix.get("unscorable") is False and q.get("unscorable"):
        q["unscorable"], q["keyed"] = False, True
        changed.append("now scored")
    if "options" in fix:
        want = [{"letter": chr(ord("A") + i), "html": html.escape(t, quote=False)}
                for i, t in enumerate(fix["options"])]
        if q.get("options") != want:
            q["options"] = want
            changed.append("options rebuilt")
    for letter, text in (fix.get("option") or {}).items():
        for o in q.get("options") or []:
            if o["letter"] == letter and o["html"] != html.escape(text, quote=False):
                o["html"] = html.escape(text, quote=False)
                changed.append("option %s text" % letter)
    stem = fix.get("stem")
    if stem and q.get("stem") != stem:
        q["stem"] = stem
        changed.append("stem")
    answer = fix.get("answer")
    if answer and q.get("answer") != answer:
        q["answer"] = answer
        changed.append("answer")
    lead = fix.get("lead")
    if lead:
        a = q.get("answer") or ""
        end = a.find("</p>")
        first = a[: end + 4] if a.startswith("<p>") and end != -1 else ""
        if first != lead:
            q["answer"] = lead + a[len(first):]
            changed.append("answer line")

    flags = q.get("flags") or []
    if not any(f.get("title") in DONE for f in flags):
        why = "<p>%s</p>" % html.escape(fix["why"], quote=False)
        if fix.get("unscorable"):
            title = "Not scored: no defensible key"
            body = why
        elif "correct" in fix and fix["correct"] != src and src:
            title = "Key corrected"
            body = "<p>The source keyed <strong>%s</strong>; the bank now scores <strong>%s</strong>.</p>%s" % (
                letters(src), letters(q["correct"]), why)
        else:
            title = "Key repaired"
            body = why
        kept = [f for f in flags if not (f.get("type") == "red" and
                                         (f.get("title") or "").startswith("The key looks"))]
        q["flags"] = kept + [{"type": "warning" if fix.get("unscorable") else "note",
                              "title": title, "html": body}]
        changed.append("flag")
    return changed


def main(argv):
    if not argv or argv[0].startswith("-"):
        sys.exit(__doc__)
    course, dry = argv[0], "--dry-run" in argv
    with io.open(os.path.join(HERE, "key_fixes", course + ".json"), encoding="utf-8") as f:
        fixes = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
    for qid, fix in fixes.items():
        if not fix.get("why"):
            sys.exit("%s: every repair needs a 'why'" % qid)
    seen = set()
    for path in sorted(glob.glob(os.path.join(ROOT, course, "data", "questions", "*.json"))):
        with io.open(path, encoding="utf-8") as f:
            bank = json.load(f)
        touched = False
        for q in bank:
            fix = fixes.get(q.get("qid"))
            if not fix:
                continue
            seen.add(q["qid"])
            changed = apply(q, fix)
            if changed:
                touched = True
                print("%-28s %s" % (q["qid"], "; ".join(changed)))
        if touched and not dry:
            with io.open(path, "w", encoding="utf-8") as f:
                json.dump(bank, f, ensure_ascii=False)
    missing = sorted(set(fixes) - seen)
    if missing:
        print("not found in the bank (skipped): " + ", ".join(missing))


if __name__ == "__main__":
    main(sys.argv[1:])
