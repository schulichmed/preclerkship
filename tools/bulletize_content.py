"""Turn list-like lines in a column-chart content file into bullet items.

Purpose: charts list things as bullets (user, 2026-10-13: "wherever possible, use bullet points
         in the charts when listing things"). A box line "a · b · c" becomes three "• " lines;
         a labelled group "HIGH: a · b" stays one bullet ("HIGH: a, b"); a numbered step
         "2 · x" keeps its number as its marker; a box left with one item is not touched.
         pathway_svg.py draws "• " and "N · " lines left-aligned with a hanging indent.
Input:   one or more tools/pathways/src/*.content.json (edited in place; header boxes, the
         root, groups and panels are left alone)
Output:  the same files; regenerate the spec with column_pathway.py afterwards
Usage:   python3 tools/bulletize_content.py tools/pathways/src/<id>.content.json
"""
import json
import re
import sys

NUM = re.compile(r"^\d+ · ")
GOVERNS = re.compile(r"^(NOT|NO|not|no|Avoid|AVOID|avoid|never|NEVER|only|ONLY)\s+(if|when|for|in|with|after|before)\b")


def split_top(text: str) -> list:
    """Split on ' · ' outside parentheses."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(text):
        ch = text[i]
        depth += ch == "("
        depth -= ch == ")"
        if depth == 0 and text.startswith(" · ", i):
            out.append(cur)
            cur, i = "", i + 3
            continue
        cur += ch
        i += 1
    out.append(cur)
    return [p.strip() for p in out if p.strip()]


def convert(lines: list) -> list:
    if any(l.lstrip("~").startswith("• ") for l in lines):
        return lines                                   # already done
    items = []                                         # (muted, text, is_numbered)
    for line in lines:
        muted, t = line.startswith("~"), line.lstrip("~")
        if NUM.match(t):
            items.append((muted, t, True))
            continue
        pieces = split_top(t)
        if len(pieces) > 1 and GOVERNS.match(pieces[0]):
            # "NOT if a · b · c": the lead-in governs every item, so splitting would drop it
            print(f"  left whole (lead-in governs the list): {t}")
            items.append((muted, t, False))
            continue
        if len(pieces) > 1 and any(0 < p.find(": ") <= 30 for p in pieces):
            # labelled groups: each "label: ..." piece starts an item, unlabelled pieces join it
            group = []
            for p in pieces:
                if 0 < p.find(": ") <= 30 and group:
                    items.append((muted, ", ".join(group), False))
                    group = []
                group.append(p)
            items.append((muted, ", ".join(group), False))
        else:
            items += [(muted, p, False) for p in pieces]
    if len(items) < 2:
        return lines
    return [("~" if m else "") + (t if num else "• " + t) for m, t, num in items]


def main(path: str) -> None:
    c = json.load(open(path, encoding="utf-8"))
    n = 0
    for col in c.get("columns", []):
        for sec, rows in col.items():
            if sec in ("id", "colour", "drop_from", "drop_label", "head") or not isinstance(rows, list):
                continue
            for row in rows:
                for box in row:
                    new = convert(box[2])
                    n += new != box[2]
                    box[2] = new
    for key in ("pres", "tiers"):
        for b in c.get(key, []):
            new = convert(b.get("lines", []))
            n += new != b.get("lines", [])
            b["lines"] = new
    json.dump(c, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{path}: {n} boxes bulleted")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
