# -*- coding: utf-8 -*-
"""Put an Inherited callout under every lecture-note section the slides do not teach.

Purpose: inherited_sections.py finds the body sections of a PoM 2 lecture
         note that no slide of this year's deck lands in. This tool writes a
         warning callout directly under each such heading so a reader, and
         the curriculum check, know the section is an upper year's notes and
         not this year's lecture. It marks a section only when its note
         carries no warning and the section is not flagged near-threshold;
         every other inherited section is listed as skipped, with the
         reason, for a person to read. A heading the reader finds taught on
         a slide is left out with ``--leave-out``. A section the reader
         confirms the slides do not teach is marked with ``--include``, which
         passes it through the warning and near-threshold gate. It is
         idempotent: a heading whose next non-blank line is already the
         callout is skipped.
Author:  Noor Sims
Date:    2026-10-06
Input:   the block's lecture notes and decks, as inherited_sections.py reads
         them, or the JSON it saved (``--sections``), which skips the decks
Output:  the same notes with two callout lines inserted under each inherited
         heading, then a blank line when text or another callout follows, so
         Markdown does not fold that into the warning;
         ``--dry-run`` prints what would change and writes nothing. Notes
         with no usable deck are never touched.

    python tools/mark_inherited.py --block repro --dry-run
    python tools/mark_inherited.py --block repro --sections build/inherited_sections/repro.json
    python tools/mark_inherited.py --block endo --note "09 - Introduction to Obesity"
    python tools/mark_inherited.py --block repro --leave-out "15 - Abnormal Uterine Bleeding: PALM-COEIN"
    python tools/mark_inherited.py --block repro --include "09 - Approach to Neonatal Care: Neonatal Sepsis"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import inherited_sections as isx  # noqa: E402

CALLOUT_BODY = ("> Not in this year's slides ({decks}). Kept for reference; "
                "not examinable this year unless the lecture says otherwise.")
NEAR = "near-threshold"


def callout(decks: str) -> list[str]:
    """The two callout lines for a deck label.

    Parameters
    ----------
    decks : str
        Deck filename(s), as ``NoteResult.deck_label`` gives them.

    Returns
    -------
    list of str
        ``["> [!warning] Inherited", "> Not in this year's slides (...)..."]``.
    """
    return [isx.INHERITED_MARK, CALLOUT_BODY.format(decks=decks)]


def record(result: isx.NoteResult) -> dict:
    """One live audit result in the shape ``inherited_sections.write_json`` saves.

    Parameters
    ----------
    result : NoteResult
        From ``inherited_sections.audit_note``.

    Returns
    -------
    dict
        ``note``, ``week``, ``decks``, ``deck_label``, ``warnings`` and
        ``sections`` (each with ``level``, ``heading``, ``line``,
        ``verdict``, ``flags`` and ``parent``), plus ``path``.
    """
    secs = []
    for top in result.sections:
        for s in [top] + top.children:
            secs.append({"level": s.level, "heading": s.heading, "line": s.line,
                         "verdict": s.verdict, "flags": list(s.flags),
                         "parent": None if s is top else top.heading})
    return {"note": result.note.stem, "week": result.note.parent.name,
            "decks": [p.name for p in result.decks], "deck_label": result.deck_label,
            "warnings": list(result.warnings), "sections": secs, "path": result.note}


def load_records(block: str, sections: Path | None, only: str | None) -> list[dict]:
    """The block's note records, from a saved JSON or a fresh audit.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.
    sections : Path or None
        JSON written by ``inherited_sections.py --json``; None audits the
        notes now.
    only : str or None
        Restrict to the note with this stem.

    Returns
    -------
    list of dict
        One record per note, each with a ``path`` to the note file.
    """
    if sections is None:
        files = isx.deck_files()
        index = isx.embed_index()
        return [record(isx.audit_note(note, files, index))
                for note in isx.lecture_notes(block) if not only or note.stem == only]
    folder = isx.LECTURE_NOTES / isx.BLOCKS[block][0]
    out = []
    for rec in json.loads(sections.read_text(encoding="utf-8")):
        if only and rec["note"] != only:
            continue
        rec["path"] = folder / rec["week"] / f"{rec['note']}.md"
        out.append(rec)
    return out


def targets(rec: dict) -> list[dict]:
    """The sections that would carry the callout in one note, before the gate.

    Parameters
    ----------
    rec : dict
        A note record (see ``record``).

    Returns
    -------
    list of dict
        Each top-level section with verdict ``inherited``; for a top-level
        section with any other verdict, each child with verdict
        ``inherited``. Empty when the note has no usable deck.
    """
    label = rec.get("deck_label", "")
    if not rec.get("decks") or label.startswith("no deck found"):
        return []
    secs = rec.get("sections", [])
    out = []
    for top in (s for s in secs if s.get("parent") is None):
        if top["verdict"] == "inherited":
            out.append(top)
        else:
            out.extend(c for c in secs if c.get("parent") == top["heading"]
                       and c["verdict"] == "inherited")
    return out


def section_key(rec: dict, sec: dict) -> str:
    """The ``"<note stem>: <heading>"`` name a reader gives one section."""
    return f"{rec['note']}: {sec['heading']}"


def skip_reason(rec: dict, sec: dict, leave_out: set[str] = frozenset(),
                include: set[str] = frozenset()) -> str:
    """Why a target section must be read by a person instead of marked.

    Parameters
    ----------
    rec : dict
        The note record; a missing ``warnings`` counts as none.
    sec : dict
        The section; a missing ``flags`` counts as none.
    leave_out : set of str
        Headings a reader found taught on a slide, as ``"<heading>"`` or
        ``"<note stem>: <heading>"``.
    include : set of str
        Sections a reader confirmed the slides do not teach, as
        ``"<note stem>: <heading>"``. They skip the warning and
        near-threshold gate; a leave-out still wins.

    Returns
    -------
    str
        ``""`` when the section may be marked, else the reason.
    """
    if sec["heading"] in leave_out or section_key(rec, sec) in leave_out:
        return "left out by reader"
    if section_key(rec, sec) in include:
        return ""
    if rec.get("warnings"):
        return f"note warning {','.join(rec['warnings'])}"
    if NEAR in sec.get("flags", []):
        return NEAR
    return ""


def find_heading(lines: list[str], sec: dict) -> int | None:
    """The line of a section's heading, at its saved line or the nearest match.

    Parameters
    ----------
    lines : list of str
        The note's lines.
    sec : dict
        The section, with ``level``, ``heading`` and ``line``.

    Returns
    -------
    int or None
        The 0-based heading line, None when the heading is gone. Saved line
        numbers go stale once earlier callouts are inserted, so a heading
        not at its line is looked up by its exact text.
    """
    want = "#" * sec["level"] + " " + sec["heading"]
    line = sec["line"]
    if 0 <= line < len(lines) and lines[line].rstrip() == want:
        return line
    hits = [i for i, text in enumerate(lines) if text.rstrip() == want]
    return min(hits, key=lambda i: abs(i - line)) if hits else None


def already_marked(lines: list[str], at: int) -> bool:
    """Whether the next non-blank line after ``at`` is the Inherited callout."""
    for text in lines[at + 1:]:
        if text.strip():
            return text.startswith(isx.INHERITED_MARK)
    return False


def gap(lines: list[str], after: int) -> list[str]:
    """The blank line the callout needs before the line at ``after``, if any.

    Parameters
    ----------
    lines : list of str
        The note's lines, before the callout goes in.
    after : int
        Index of the line that will follow the callout.

    Returns
    -------
    list of str
        ``[""]`` when that line is text or another callout, which Markdown
        would otherwise fold into the Inherited callout (lazy continuation);
        ``[]`` when it is blank, a heading, or the end of the note.
    """
    if after >= len(lines):
        return []
    nxt = lines[after]
    return [] if not nxt.strip() or isx.HEADING_RE.match(nxt) else [""]


def mark_note(rec: dict, dry: bool, leave_out: set[str] = frozenset(),
              include: set[str] = frozenset(), seen: set[str] | None = None) -> int:
    """Insert the callout under each markable heading of one note.

    Parameters
    ----------
    rec : dict
        A note record with ``path``.
    dry : bool
        Print instead of writing.
    leave_out : set of str
        Headings not to mark, see ``skip_reason``.
    include : set of str
        Sections a reader confirmed, see ``skip_reason``; each is printed as
        ``included:`` whether or not it is already marked.
    seen : set of str, optional
        Collects the ``include`` names this note matched.

    Returns
    -------
    int
        Insertions made (or that would be made).
    """
    todo = targets(rec)
    if not todo:
        return 0
    note = Path(rec["path"])
    lines = note.read_text(encoding="utf-8").split("\n")
    plan = []
    for sec in todo:
        if seen is not None and section_key(rec, sec) in include:
            seen.add(section_key(rec, sec))       # matched, even when a leave-out wins
        reason = skip_reason(rec, sec, leave_out, include)
        if not reason and section_key(rec, sec) in include:
            print(f"included: {section_key(rec, sec)}")
        at = None if reason else find_heading(lines, sec)
        if not reason and at is None:
            reason = "heading not found"
        if reason:
            print(f"skipped: {reason}: {rec['note']}: {sec['heading']}")
        elif not already_marked(lines, at):
            plan.append((at, sec["heading"]))
    for at, heading in sorted(plan, reverse=True):      # bottom up keeps earlier indices valid
        if dry:
            print(f"would mark {rec['note']}: {heading}")
        else:
            lines[at + 1:at + 1] = callout(rec["deck_label"]) + gap(lines, at + 1)
    if plan and not dry:
        with note.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(lines))
        print(f"marked {rec['note']}: {len(plan)}")
    return len(plan)


def mark(block: str, dry: bool, only: str | None = None, sections: Path | None = None,
         leave_out: set[str] = frozenset(), include: set[str] = frozenset()) -> int:
    """Mark every markable inherited section of a block.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.
    dry : bool
        Print what would change, write nothing.
    only : str or None
        Restrict to the note with this stem.
    sections : Path or None
        Read the verdicts from this saved JSON instead of auditing now.
    leave_out : set of str
        Headings a reader found taught on a slide, see ``skip_reason``.
    include : set of str
        Sections a reader confirmed the slides do not teach, see
        ``skip_reason``. One that names no inherited section of the block
        is printed as ``include matched nothing:``.

    Returns
    -------
    int
        Insertions made across the block.
    """
    seen: set[str] = set()
    total = sum(mark_note(rec, dry, leave_out, include, seen)
                for rec in load_records(block, sections, only))
    for name in sorted(set(include) - seen):
        print(f"include matched nothing: {name}")
    print(f"{'would insert' if dry else 'inserted'} {total} Inherited callouts in {block}")
    return total


def main() -> None:
    """Parse the command line and mark one block."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(isx.BLOCKS))
    ap.add_argument("--note", help="only the note with this stem")
    ap.add_argument("--sections", type=Path,
                    help="read verdicts from this inherited_sections.py --json output")
    ap.add_argument("--leave-out", action="append", default=[], metavar="HEADING",
                    help="a heading a slide teaches, repeatable; '<note stem>: <heading>' for one note, "
                         "a bare '<heading>' for every note of the block")
    ap.add_argument("--include", action="append", default=[], metavar="NOTE: HEADING",
                    help="'<note stem>: <heading>' a reader confirmed the slides do not teach, "
                         "repeatable; marked despite a note warning or a near-threshold flag")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    mark(args.block, args.dry_run, args.note, args.sections, set(args.leave_out), set(args.include))


if __name__ == "__main__":
    main()
