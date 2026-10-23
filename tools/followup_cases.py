#!/usr/bin/env python3
"""Give every follow-up question the case it continues, from hand-checked specs.

Purpose: a follow-up ("What would you recommend to improve Loki's glycemic
         control?") only makes sense after the question that introduced the
         case. Shuffled, it arrives alone and cannot be answered. Each spec
         sets that question's preamble to the parent's case, copied from the
         parent's stem with its question sentence removed, so the case shows
         in the box above the stem wherever the question lands.
Author:  Noor Sims
Date:    2026-10-06
Input:   tools/followup_cases/*.json - one spec per follow-up - and
         <course>/data/questions/*.json
Output:  the same question files, rewritten in place, and a report on stdout

Why specs and not a parser
--------------------------
Telling a follow-up from a self-contained vignette that happens to say "he"
took a reading of each question, and so did choosing which earlier stem holds
its case. A spec records that reading once, and this pass re-applies it after
any extractor run, so a FoM or PoM 1 re-parse cannot quietly undo it. The
same preambles are in the vault notes for PoM 2's vault-written families.

Spec fields
-----------
    qid       the follow-up question
    bank      its JSON file, relative to the repo root
    preamble  {"title", "html"} - "The case" or "The case - <name>", or the
              parent's own shared preamble copied exactly

Only an empty preamble is filled: a question that has gained one of its own
since the spec was written is reported and left alone.
"""

import json
from pathlib import Path

SPEC_DIR = Path("tools/followup_cases")


def load_specs() -> list[dict]:
    """Every spec, in file order."""
    specs = []
    for path in sorted(SPEC_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as fh:
            specs.extend(json.load(fh))
    return specs


def main() -> None:
    by_bank: dict[str, list[dict]] = {}
    for s in load_specs():
        by_bank.setdefault(s["bank"], []).append(s)

    for bank_path, bank_specs in sorted(by_bank.items()):
        with open(bank_path, encoding="utf-8") as fh:
            bank = json.load(fh)
        index = {q["qid"]: q for q in bank}
        changed = 0
        for s in bank_specs:
            q = index.get(s["qid"])
            if q is None:
                print(f"  MISSING {s['qid']} in {bank_path}")
                continue
            if q.get("preamble") == s["preamble"]:
                continue
            if q.get("preamble"):
                print(f"  KEPT    {s['qid']}: it has a preamble of its own now")
                continue
            q["preamble"] = s["preamble"]
            changed += 1
        if changed:
            # the banks are kept on one line, as the extractors write them
            with open(bank_path, "w", encoding="utf-8") as fh:
                json.dump(bank, fh, ensure_ascii=False)
        print(f"{bank_path:34} {changed:3d} given their case")


if __name__ == "__main__":
    main()
