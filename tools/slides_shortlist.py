# -*- coding: utf-8 -*-
"""List the handed-down questions whose earlier audit evidence is not on the slides.

Purpose: the 2026-10-05 audit read questions against whole lecture notes, and
         a note body is often an upper year's. For every live workbook and
         HippoNotes question this tool names the lecture it resolves to, that
         lecture's deck on disk, the earlier audit's evidence quote(s), whether
         the quote's terms are on the slides, and which note section the quote
         falls in and that section's verdict from inherited_sections.py.
         Questions whose evidence is off the slides, reaches any inherited
         section (a child as well as its parent), or sits in no section and
         not in the chart region either, are the shortlist a reader works
         against the deck and the chart region.
Author:  Noor Sims
Date:    2026-10-06
Input:   pom2/data/questions/<block>.json; the earlier verdict rows
         (``*_w*.json``, ``*_refile*.json``) in the audit directory; the saved
         section verdicts of ``inherited_sections.py --json`` (default
         build/inherited_sections/<block>.json); the vault notes and the decks
         inherited_sections.py reads
Output:  one line per question on stdout; <audit dir>/<block>_slides.prefill.json
         (a verdict row per question, shortlisted ones with an empty verdict)
         and <audit dir>/<block>_slides.txt (the shortlist dumped for
         reading). Reads the vault, never writes it.

    python tools/slides_shortlist.py --block repro
    python tools/slides_shortlist.py --block endo --sections build/inherited_sections/endo.json --out build/curriculum_audit

The saved section records spare a rescoring of every note (10 to 20 minutes a
block over /mnt/c); the notes are still split into sections to place each
quote, and each deck is still read once for the evidence check. Without the
records file every note is rescored with ``inherited_sections.audit_note``.
A lecture with no deck on disk cannot be judged against its slides: its
questions stay `current` with note "NO-DECK" and are listed for export.
"""

import argparse
import glob
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import curriculum_audit as ca  # noqa: E402
import inherited_sections as isx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

EVIDENCE_AT = 0.5    # fraction of an evidence quote's terms that must be on the slides
SECTION_AT = 0.6     # fraction of the quote's terms a section must hold to be where it falls
CHART_AT = 0.6       # a quote no section holds passes only if this share of its terms is in the chart region

# the handed-down families this pass reads; Schulich Reviews is left for a later pass
FAMILIES = ("hipponotes", "workbook")

PREFILL = "{block}_slides.prefill.json"
DUMP = "{block}_slides.txt"
# verdict files the earlier reads wrote; the slides files this tool writes match neither
EVIDENCE_GLOBS = ("*_w*.json", "*_refile*.json")


def audit_dir() -> Path:
    """The default curriculum_audit directory of this repo."""
    return ROOT / "build" / "curriculum_audit"


def strip_html(text: str | None) -> str:
    """Plain text of an HTML fragment."""
    return html.unescape(re.sub(r"<[^>]+>", " ", text or "")).strip()


def evidence_by_qid(folder: Path | None = None) -> dict[str, list[str]]:
    """Every earlier evidence quote per qid.

    Parameters
    ----------
    folder : Path, optional
        The curriculum_audit directory; ``audit_dir()`` by default.

    Returns
    -------
    dict
        qid -> distinct non-empty quotes, in file order.
    """
    folder = folder or audit_dir()
    paths = sorted({p for g in EVIDENCE_GLOBS for p in glob.glob(str(folder / g))
                    if not p.endswith(".qids.json")})
    out: dict[str, list[str]] = {}
    for row in ca.load_rows(paths):
        ev = (row.get("evidence") or "").strip()
        if ev and ev not in out.setdefault(row["qid"], []):
            out[row["qid"]].append(ev)
    return out


def load_records(path: Path) -> list[dict] | None:
    """The per-note records ``inherited_sections.py --json`` saved.

    Parameters
    ----------
    path : Path

    Returns
    -------
    list of dict or None
        The records, or None when the file does not exist.
    """
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_note(q: dict) -> tuple[Path | None, str, int | None]:
    """The lecture note a question resolves to.

    Parameters
    ----------
    q : dict
        A question with ``review`` or ``lecture``.

    Returns
    -------
    tuple
        (note path or None, against stem, week). The stem comes from
        ``review[0]`` when it exists, else from ``lecture`` and ``week``. An
        entry with no number (``"In-Class - Amenorrhea"``) names the note
        file outright.
    """
    rev = (q.get("review") or [None])[0]
    if rev:
        block = ca.block_for_week(int(rev["w"]))
        note = ca.lecture_note(block, rev) if block else None
        if note is None and block and not rev.get("n"):
            bare = ca.LECTURE_NOTES / ca.BLOCKS[block][0] / f"Week {rev['w']}" / f"{rev['t']}.md"
            note = bare if bare.exists() else None
        stem = note.stem if note else (f"{rev['n']} - {rev['t']}" if rev.get("n") else rev["t"])
        return note, stem, int(rev["w"])
    return None, q.get("lecture") or "", q.get("week")


def note_from_record(note: Path, record: dict, files: list[Path],
                     index: dict[str, Path]) -> isx.NoteResult:
    """Rebuild a note's result from its saved record without reading a deck.

    Parameters
    ----------
    note : Path
        The lecture note; it is split into sections again so each section
        has its text.
    record : dict
        One record of ``inherited_sections.write_json``.
    files : list of Path
        From ``inherited_sections.deck_files``.
    index : dict
        From ``inherited_sections.embed_index``.

    Returns
    -------
    NoteResult
        Sections carry the record's score and verdict, matched by heading
        line and text, else by heading text alone; a section the record does
        not name has an empty verdict. Decks are the record's filenames found
        in the note's week folder or ``files``.
    """
    parts = isx.split_note(note.read_text(encoding="utf-8", errors="replace"))
    secs = isx.sections(parts.body, parts.body_start, lambda n: isx.embed_text(n, index))
    saved = record.get("sections") or []
    by_line = {(s["line"], s["heading"]): s for s in saved}
    by_heading: dict[str, dict] = {}
    for s in saved:
        by_heading.setdefault(s["heading"], s)
    result = isx.NoteResult(note, [], record.get("deck_label", ""), secs, record.get("skipped", ""))
    for s in result.flat():
        hit = by_line.get((s.line, s.heading)) or by_heading.get(s.heading)
        s.score, s.verdict = (hit["score"], hit["verdict"]) if hit else (None, "")
        if not hit:
            print(f"   heading not in the saved records, no verdict: {note.stem} / {s.heading}",
                  file=sys.stderr)
    local = [p for p in note.parent.iterdir() if p.suffix.lower() in isx.DECK_SUFFIXES]
    pool = {p.name: p for p in files + local}
    for n in record.get("decks") or []:
        if n not in pool:
            print(f"   deck in the saved records not on disk: {note.stem} / {n}", file=sys.stderr)
    result.decks = [pool[n] for n in record.get("decks") or [] if n in pool]
    return result


def section_of(quote_terms: set[str], result: isx.NoteResult) -> tuple[str, str, list[str]]:
    """The note section an evidence quote falls in.

    Parameters
    ----------
    quote_terms : set of str
    result : NoteResult
        Sections with their text and verdict.

    Returns
    -------
    tuple
        (heading, verdict, verdicts). ``verdicts`` lists the verdict of every
        section holding at least SECTION_AT of the quote's terms. The heading
        and verdict are the deepest such section's (a child over its parent,
        whose text includes the child's), the larger share breaking a tie;
        ("", "", []) when no section reaches SECTION_AT.
    """
    if not quote_terms:
        return "", "", []
    reach = []
    for s in result.flat():
        share = len(quote_terms & isx.terms(s.text)) / len(quote_terms)
        if share >= SECTION_AT:
            reach.append((s.level, share, s))
    if not reach:
        return "", "", []
    best = max(reach, key=lambda t: (t[0], t[1]))[2]
    return best.heading, best.verdict, [s.verdict for _level, _share, s in reach]


def chart_share(quote_terms: set[str], chart: str) -> float:
    """The share of a quote's terms found in a note's chart region."""
    return len(quote_terms & isx.terms(chart)) / len(quote_terms) if quote_terms else 0.0


def shortlist(block: str, records: list[dict] | None = None,
              evidence_dir: Path | None = None) -> list[dict]:
    """Score every live handed-down question of a block against its deck.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.
    records : list of dict, optional
        Saved ``inherited_sections`` records. A note they cover is not
        rescored; a note they miss, or every note when None, goes through
        ``inherited_sections.audit_note``.
    evidence_dir : Path, optional
        Where the earlier verdict files are; ``audit_dir()`` by default.

    Returns
    -------
    list of dict
        One per question, in bank order: qid, family, against, week, deck,
        chart, evidence (list), evidence_score, section, section_verdict,
        status (``ok`` / ``SHORTLIST`` / ``NO-DECK`` / ``NO-NOTE``), stem,
        options, key, answer.
    """
    files = isx.deck_files()
    index = isx.embed_index()
    evidence = evidence_by_qid(evidence_dir)
    saved = {(r["week"], r["note"]): r for r in records or []}
    notes: dict[Path, isx.NoteResult] = {}
    pages: dict[Path, list[set[str]]] = {}     # each deck read once per run
    out = []
    for q in ca.load_bank(ca.bank_path(block)):
        if q.get("family") not in FAMILIES or q.get("family") == ca.OFF or q.get("retired"):
            continue
        note, against, week = resolve_note(q)
        quotes = evidence.get(q["qid"], [])
        row = {"qid": q["qid"], "family": q["family"], "against": against, "week": week,
               "deck": "", "chart": "", "evidence": quotes, "evidence_score": None, "chart_share": None,
               "section": "", "section_verdict": "", "status": "NO-DECK",
               "stem": strip_html(q.get("stem")),
               "options": [f"{o['letter']}. {strip_html(o.get('html'))}" for o in q.get("options") or []],
               "key": ", ".join(q.get("correct") or []), "answer": strip_html(q.get("answer"))[:400]}
        if note is None or not note.exists():
            row["status"] = "NO-NOTE"
            out.append(row)
            continue
        if note not in notes:
            record = saved.get((note.parent.name, note.stem))
            if record is not None:
                notes[note] = note_from_record(note, record, files, index)
            else:
                if records is not None:
                    print(f"   not in the saved records, rescoring: {note.stem}", file=sys.stderr)
                notes[note] = isx.audit_note(note, files, index)
        res = notes[note]
        row["chart"] = isx.split_note(note.read_text(encoding="utf-8", errors="replace")).chart
        if not res.decks:          # ``decks`` lists only the usable, scored decks
            out.append(row)
            continue
        try:
            for p in res.decks:
                if p not in pages:
                    pages[p] = [isx.terms(pg) for pg in isx.deck_pages(p)]
        except RuntimeError as exc:
            print(f"   unreadable deck, NO-DECK: {exc}", file=sys.stderr)
            out.append(row)
            continue
        row["deck"] = ", ".join(p.name for p in res.decks)
        slide_terms = set().union(*[t for p in res.decks for t in pages[p]])
        scores = []
        for quote in quotes:
            qt = isx.terms(quote)
            scores.append(len(qt & slide_terms) / len(qt) if qt else 0.0)
        row["evidence_score"] = max(scores) if scores else 0.0
        quote_terms = isx.terms(" ".join(quotes))
        heading, verdict, verdicts = section_of(quote_terms, res)
        row["section"], row["section_verdict"] = heading, verdict
        row["chart_share"] = chart_share(quote_terms, row["chart"])
        off_slides = row["evidence_score"] < EVIDENCE_AT
        # a section the quote reaches that is inherited, or has no saved verdict, needs a read
        doubtful = any(v in ("inherited", "") for v in verdicts)
        # a quote no section holds is a paraphrase unless the slide-derived chart holds it
        unplaced = not verdicts and row["chart_share"] < CHART_AT
        row["status"] = "SHORTLIST" if (off_slides or doubtful or unplaced) else "ok"
        out.append(row)
    return out


def prefill(rows: list[dict]) -> list[dict]:
    """Verdict rows for every question, shortlisted ones left for the reader.

    Parameters
    ----------
    rows : list of dict
        From ``shortlist``.

    Returns
    -------
    list of dict
        Rows in the audit's shape plus ``slides``. ``ok`` rows are
        ``current`` with the first earlier evidence quote; ``NO-DECK`` and
        ``NO-NOTE`` rows are ``current`` with note ``NO-DECK`` (a lecture
        with no note cannot be checked against a deck either);
        ``SHORTLIST`` rows have an empty verdict and evidence for the reader
        to fill.
    """
    out = []
    for r in rows:
        first = (r["evidence"] or [""])[0][:200]
        base = {"qid": r["qid"], "against": r["against"], "week": r["week"]}
        if r["status"] == "SHORTLIST":
            out.append({**base, "verdict": "", "slides": r["deck"], "evidence": "", "note": ""})
        elif r["status"] == "ok":
            out.append({**base, "verdict": "current", "slides": r["deck"], "evidence": first, "note": ""})
        else:
            out.append({**base, "verdict": "current", "slides": "", "evidence": first, "note": "NO-DECK"})
    return [{k: row[k] for k in ("qid", "verdict", "against", "week", "slides", "evidence", "note")}
            for row in out]


def dump(rows: list[dict]) -> str:
    """The shortlist as plain text for reading in slices.

    Parameters
    ----------
    rows : list of dict
        From ``shortlist``; only ``SHORTLIST`` rows are written.

    Returns
    -------
    str
        One block per question: qid, lecture, deck, the earlier evidence and
        where it fell, the stem, the options, the key and the answer.
    """
    parts = []
    for r in rows:
        if r["status"] != "SHORTLIST":
            continue
        parts.append("\n".join([
            f"### {r['qid']}  [{r['family']}]  week {r['week']}  {r['against']}",
            f"deck: {r['deck']}",
            f"earlier evidence (score {r['evidence_score']:.2f}; section: {r['section'] or '?'} "
            f"{r['section_verdict']}; chart {r['chart_share']:.2f}):",
            *[f"  - {e}" for e in r["evidence"]],
            f"stem: {r['stem']}",
            *[f"  {o}" for o in r["options"]],
            f"key: {r['key']}",
            f"answer: {r['answer']}",
            ""]))
    return "\n".join(parts)


def main() -> None:
    """Print the table and write the prefill and the dump."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(isx.BLOCKS))
    ap.add_argument("--sections", type=Path,
                    help="saved inherited_sections records (default build/inherited_sections/<block>.json)")
    ap.add_argument("--out", type=Path, default=None,
                    help="curriculum_audit directory: earlier verdicts are read from it, "
                         "the prefill and dump written to it (default build/curriculum_audit)")
    args = ap.parse_args()
    out = args.out or audit_dir()
    if isx.VAULT.resolve() in out.resolve().parents or out.resolve() == isx.VAULT.resolve():
        raise SystemExit("refusing to write inside the vault")
    sections_path = args.sections or ROOT / "build" / "inherited_sections" / f"{args.block}.json"
    records = load_records(sections_path)
    if records is None:
        print(f"no saved section records at {sections_path}: rescoring every note with audit_note",
              file=sys.stderr)
    else:
        print(f"section verdicts from the saved records {sections_path}", file=sys.stderr)
    rows = shortlist(args.block, records, out)
    width = max([len(r["qid"]) for r in rows] + [3])
    print(f"{'qid':{width}s}  {'status':9s} {'evid':>5s} {'lecture':45s} {'section':35s} deck")
    for r in rows:
        score = "-" if r["evidence_score"] is None else f"{r['evidence_score']:.2f}"
        sec = f"{r['section'][:22]} [{r['section_verdict']}]" if r["section"] else ""
        print(f"{r['qid']:{width}s}  {r['status']:9s} {score:>5s} {r['against'][:45]:45s} "
              f"{sec:35s} {r['deck'] or 'NO-DECK'}")
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(f"\n{len(rows)} live handed-down questions: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for stem in sorted({r["against"] for r in rows if r["status"] in ("NO-DECK", "NO-NOTE")}):
        print(f"   NO-DECK lecture: {stem}", file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    (out / PREFILL.format(block=args.block)).write_text(
        json.dumps(prefill(rows), ensure_ascii=False, indent=1), encoding="utf-8")
    (out / DUMP.format(block=args.block)).write_text(dump(rows), encoding="utf-8")
    print(f"wrote {out / PREFILL.format(block=args.block)} and {out / DUMP.format(block=args.block)}")


if __name__ == "__main__":
    main()
