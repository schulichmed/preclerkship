#!/usr/bin/env python3
"""Ask every matching question as a dropdown grid, from hand-checked specs.

Purpose: turn matching questions that were flattened into an MCQ over complete
         mappings ("1-W, 2-X, 3-Y"), split one item per question, or left as a
         self-marked "(matching)" stub, into the gradable dropdown pairing the
         portal already renders.
Author:  Noor Sims
Date:    2026-10-05
Input:   tools/pairings/*.json - one spec per question, written by hand from
         that question's own key - and <course>/data/questions/*.json
Output:  the same question files, rewritten in place, and a report on stdout

Why specs and not a parser
--------------------------
pairs_from_tables.py lifts a key out of an answer table, which is the one
shape regular enough to read mechanically. The rest come in a dozen shapes -
a mapping MCQ, a prose key ("A = ii, B = iii"), a series of one-row questions
sharing the same options - and each has to be read by a person to be sure the
key is right. A spec records that reading once, and this pass re-applies it
after any extractor run, so a FoM or PoM 1 re-parse cannot quietly undo it.

Spec fields
-----------
    qid       the question that becomes the pairing
    bank      its JSON file, relative to the repo root
    stem      the new stem HTML (figures kept, the mapping list removed)
    pairs     {"leftLabel", "rightLabel", "items": [{"left", "right"}, ...]}
    answer    optional replacement answer HTML, when the old one named
              options that no longer exist
    preamble  optional replacement preamble (null clears it), for a series
              lead-in that no longer describes the merged question
    absorbs   optional qids folded into this one; they leave the bank
    flags     optional flags to append (deduplicated by title)
    drop_flags  optional flag titles the conversion makes untrue (e.g. "the
              diagram is not in the bank" once the diagram is in the stem)

Idempotent - a question already carrying the spec's pairs is left alone.
"""

import json
from pathlib import Path

SPEC_DIR = Path("tools/pairings")


def load_specs() -> list[dict]:
    """Every spec, in file order."""
    specs = []
    for path in sorted(SPEC_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as fh:
            specs.extend(s for s in json.load(fh) if "pairs" in s)
    return specs


def apply(q: dict, spec: dict) -> bool:
    """Rewrite one question from its spec. True if it changed."""
    before = json.dumps(q, sort_keys=True)
    q["kind"] = "pairing"
    q["pairs"] = spec["pairs"]
    q["stem"] = spec["stem"]
    if spec.get("answer"):
        q["answer"] = spec["answer"]
    if "preamble" in spec:
        q["preamble"] = spec["preamble"]
    # the key lives in pairs.items now, so nothing is self-marked or optioned
    q["options"], q["correct"] = [], []
    q["multi"] = q["free"] = q["unscorable"] = False
    q["keyed"] = True
    stale = set(spec.get("drop_flags") or [])
    if stale:
        q["flags"] = [f for f in q.get("flags") or [] if f.get("title") not in stale]
    have = {f.get("title") for f in q.get("flags") or []}
    for f in spec.get("flags") or []:
        if f["title"] not in have:
            q.setdefault("flags", []).append(f)
    return json.dumps(q, sort_keys=True) != before


def main() -> None:
    specs = load_specs()
    by_bank: dict[str, list[dict]] = {}
    for s in specs:
        by_bank.setdefault(s["bank"], []).append(s)

    for bank_path, bank_specs in sorted(by_bank.items()):
        with open(bank_path, encoding="utf-8") as fh:
            bank = json.load(fh)
        index = {q["qid"]: q for q in bank}
        absorbed = {a for s in bank_specs for a in s.get("absorbs") or []}
        changed = 0
        for s in bank_specs:
            q = index.get(s["qid"])
            if q is None:
                print(f"  MISSING {s['qid']} in {bank_path}")
                continue
            changed += apply(q, s)
        kept = [q for q in bank if q["qid"] not in absorbed]
        dropped = len(bank) - len(kept)
        if changed or dropped:
            # the banks are kept on one line, as the extractors write them
            with open(bank_path, "w", encoding="utf-8") as fh:
                json.dump(kept, fh, ensure_ascii=False)
        print(f"{bank_path:34} {changed:3d} converted  {dropped:2d} absorbed")


if __name__ == "__main__":
    main()
