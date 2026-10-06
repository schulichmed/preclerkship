# -*- coding: utf-8 -*-
"""Keep PoM 2's question banks to what this year's lectures teach.

Purpose: act on a curriculum audit. Each audit row says whether a question is
         current to this year's lecture notes, outdated by them, or not covered
         by them at all. This tool moves the outdated and not-covered ones into
         the Off-curriculum set, marks them in the vault, reports where things
         stand, and lists the questions most worth a human read next time.
Author:  Noor Sims
Date:    2026-10-05
Input:   pom2/data/questions/<block>.json, audit verdict files
         (build/curriculum_audit/<block>_<chunk>.json, rows of
         {qid, verdict, against, week, evidence, note}), and the medwiki vault
         (``$MEDWIKI``, default the author's path)
Output:  the same question JSON with moved questions re-filed, a marker and a
         callout under each moved question's heading in the vault, and plain
         tables on stdout

    python tools/curriculum_audit.py candidates --course pom2 --block endo [--week 2]
    python tools/curriculum_audit.py apply build/curriculum_audit/endo_w*.json
    python tools/curriculum_audit.py report
    python tools/curriculum_audit.py mark-vault [--dry-run] build/curriculum_audit/*_w*.json

A moved question keeps its qid, so progress and Anki cards still join on it.
It gains family "offcurriculum", a week that is never null, a first flag
saying what was checked, and an ``offCurriculum`` record of where it came
from. Applying the same verdicts twice changes nothing the second time.

A row may carry ``"slides": "<deck filename>"`` when the check was made against
the lecture's slide deck rather than the whole note. The Off-curriculum flag
then says the slides do not teach it and names the deck, and ``offCurriculum``
keeps the deck name. Rows without ``slides`` render as before.

A `misfiled` verdict re-files a live question under the lecture that teaches
it this year: `week`, `weekLabel` and `lecture` are rewritten from the lecture
named in `against`, `review` is set to that lecture, and a `refiled` record
keeps where it came from. A question whose lecture's week lies outside its
bank's span moves to the bank that owns that week. The portal's week filter and
its week and lecture headings read `week` and `lecture`, not `review`, which is
why a right `review` on a wrong `week` still shows under the wrong week.
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("MEDWIKI", "/mnt/c/Users/nsims/medwiki"))
QUESTION_NOTES = VAULT / "00 - Practice Questions"
LECTURE_NOTES = VAULT / "01 - Lectures" / "99 - PoM 2"

OFF = "offcurriculum"
MOVING_VERDICTS = ("outdated", "not-covered", "retired")

# block slug -> (vault lecture folder, vault topic name in question note titles)
BLOCKS = {
    "endo": ("01 - Endocrinology", "Endocrinology"),
    "repro": ("02 - Repro", "Reproduction"),
    "msk": ("03 - MSK", "Musculoskeletal"),
    "neuro": ("04 - Neuro", "Neurology"),
    "psych": ("05 - Psych", "Psychiatry"),
}

# families written in the vault and exported from it; the rest are backed up
# from the JSON by vault_backup.py
VAULT_FAMILIES = ("module", "weekly", "workbook", "meds2029")

# a qid's first word names the vault note its `# N` heading lives in
QID_NOTE = {
    "module": "Module Questions",
    "weekly": "Weekly Quizzes",
    "workbook": "Preclerkship Workbook",
    "new": "New Questions",
}

# the handed-down banks, and anything with no lecture yet, are the ones worth a read
READ_FAMILIES = ("workbook", "hipponotes", "reviews")

REFILING_VERDICT = "misfiled"

# block slug -> the course weeks it spans, as tools/portal.py's roster states them
BLOCK_WEEKS = {"endo": range(1, 4), "repro": range(4, 7), "msk": range(7, 12),
               "neuro": range(12, 17), "psych": range(17, 21)}


def block_for_week(week: int) -> str | None:
    """The block slug whose span holds a course week, or None."""
    for slug, span in BLOCK_WEEKS.items():
        if week in span:
            return slug
    return None


def week_labels(course: str = "pom2") -> dict[int, str]:
    """{week: canonical weekLabel} read off data/notes/<block>.json."""
    out: dict[int, str] = {}
    for block in BLOCKS:
        p = ROOT / course / "data" / "notes" / f"{block}.json"
        if not p.exists():
            continue
        for wk in json.loads(p.read_text(encoding="utf-8")).get("weeks", []):
            label = wk.get("label") or ""
            m = re.match(r"^Week (\d+)", label)
            if m:
                out.setdefault(int(m.group(1)), label)
    return out


def vault_lecture(block: str, week: int, against: str) -> dict | None:
    """The `review` record for a lecture note's exact on-disk name, if the vault has it.

    Parameters
    ----------
    block : str
        Block slug that owns `week`.
    week : int
        Course week.
    against : str
        The note's exact on-disk stem: ``"11 - Approach to First Trimester
        Bleeding & Ultrasound"``, or an unnumbered one such as
        ``"In-Class - Amenorrhea"``.

    Returns
    -------
    dict or None
        ``{"w": week, "n": "11", "t": "Approach to ..."}`` for a numbered note,
        ``{"w": week, "n": "", "t": "In-Class - Amenorrhea"}`` for an unnumbered
        one (the shape review_lectures.roster() gives it), or None when no note
        of exactly that name exists under that week's folder.

    Notes
    -----
    The name is matched against the folder listing, not with ``exists()``: the
    vault sits on a case-insensitive drive, where a wrong-case title would pass
    and then fail every exact-spelling join downstream.
    """
    stem = (against or "").strip()
    week_dir = LECTURE_NOTES / BLOCKS[block][0] / f"Week {week}"
    if not stem or stem == f"Week {week}" or not week_dir.is_dir():
        return None
    if f"{stem}.md" not in {p.name for p in week_dir.iterdir()}:
        return None
    m = re.match(r"^([\d.]+)\s*[-–]\s*(.+?)$", stem)
    if not m:
        return {"w": week, "n": "", "t": stem}
    return {"w": week, "n": m.group(1), "t": m.group(2)}


def bank_path(block: str, course: str = "pom2") -> Path:
    """Path of one block's question bank.

    Parameters
    ----------
    block : str
        Block slug, e.g. ``"endo"``.
    course : str
        Course directory, ``"pom2"`` by default.

    Returns
    -------
    Path
        ``<repo>/<course>/data/questions/<block>.json``.
    """
    return ROOT / course / "data" / "questions" / f"{block}.json"


def load_bank(path: Path) -> list[dict]:
    """Read a question bank.

    Parameters
    ----------
    path : Path
        A ``data/questions/*.json`` file.

    Returns
    -------
    list of dict
        The questions, in file order.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def save_bank(path: Path, questions: list[dict]) -> None:
    """Write a question bank in the shipped compact form.

    Default separators, UTF-8, LF and no trailing newline, which is what every
    bank in the repo already is, so an untouched question diffs as nothing.

    Parameters
    ----------
    path : Path
        The bank to overwrite.
    questions : list of dict
        Its questions.
    """
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(questions, ensure_ascii=False))


def load_rows(paths: Iterable[str]) -> list[dict]:
    """Read audit verdict rows from one or more files.

    Parameters
    ----------
    paths : iterable of str
        Verdict files. ``*.qids.json`` files are qid lists, not verdicts, and
        are skipped.

    Returns
    -------
    list of dict
        Every row, in file order.
    """
    rows = []
    for p in paths:
        if p.endswith(".qids.json"):
            continue
        rows.extend(json.loads(Path(p).read_text(encoding="utf-8")))
    return rows


def week_label(week: int) -> str:
    """The plain week label a re-filed question carries.

    Parameters
    ----------
    week : int
        Course week number.

    Returns
    -------
    str
        ``"Week N"``.
    """
    return f"Week {week}"


def off_sentence(reason: str, against: str, evidence: str, bold: str, slides: str = "") -> str:
    """The plain sentence that says why a question is off-curriculum.

    Parameters
    ----------
    reason : str
        ``"outdated"``, ``"not-covered"`` or ``"retired"``.
    against : str
        The lecture note it was checked against.
    evidence : str
        A quote from that note or deck, possibly empty. Already escaped for
        the target format by the caller. For a not-covered verdict checked
        against the slides it is a reader's summary of what the deck covers,
        so it is written without quote marks; everywhere else it is quoted.
    bold : str
        A format string with one ``%s`` that emphasises the lecture name,
        e.g. ``"<strong>%s</strong>"`` or ``"**%s**"``.
    slides : str
        The deck filename when the check was against the slides, else empty.
        Already escaped by the caller.

    Returns
    -------
    str
        One or two sentences, no em dashes of its own.
    """
    lecture = bold % against
    if reason == "retired":
        lead = ("Its own source retired this question, so it is kept here rather than in "
                "the set it came from.")
        tail = f" Nearest lecture: {lecture}." if against else ""
        return lead + tail
    if slides:
        where = f"the slides of {lecture} ({slides})"
        if reason == "outdated":
            lead = ("This year's lecture teaches this differently, so the key here may not "
                    "match what you are examined on.")
            tail = (f" Checked against {where}, which say: “{evidence}”." if evidence
                    else f" Checked against {where}.")
        else:
            lead = "This year's lecture slides do not teach this."
            # a reader's summary of the deck, not a slide quote, so no quote marks
            summary = evidence.rstrip(" .")
            tail = (f" Checked against {where}, which cover: {summary}." if summary
                    else f" Checked against {where}, which do not mention it.")
        return lead + tail
    if reason == "outdated":
        lead = ("This year's lecture teaches this differently, so the key here may not "
                "match what you are examined on.")
        tail = f" Checked against {lecture}, which says: “{evidence}”." if evidence else \
            f" Checked against {lecture}."
    else:
        lead = "This year's lectures do not teach this."
        tail = (f" Checked against {lecture}, the nearest lecture, which says: "
                f"“{evidence}”." if evidence else
                f" Checked against {lecture}, the nearest lecture, which does not mention it.")
    return lead + tail


def off_flag_html(row: dict) -> str:
    """The Off-curriculum flag body for the portal.

    Parameters
    ----------
    row : dict
        An audit row.

    Returns
    -------
    str
        ``<p>...</p>``.
    """
    text = off_sentence(row["verdict"], html.escape(row["against"]),
                        html.escape(row.get("evidence") or "").strip(), "<strong>%s</strong>",
                        html.escape(row.get("slides") or ""))
    return f"<p>{text}</p>"


def all_banks(course: str = "pom2") -> dict[str, tuple[Path, list[dict]]]:
    """Load every block bank of a course.

    Parameters
    ----------
    course : str
        Course directory.

    Returns
    -------
    dict
        Block slug -> (path, questions), for the blocks whose bank exists.
    """
    out = {}
    for block in BLOCKS:
        p = bank_path(block, course)
        if p.exists():
            out[block] = (p, load_bank(p))
    return out


def apply_rows(rows: list[dict], checked: str | None = None) -> None:
    """Re-file every outdated, not-covered or misfiled question, and fill null weeks.

    Parameters
    ----------
    rows : list of dict
        Audit rows. Current rows only give a week to a question that has none.
    """
    banks = all_banks()
    where = {q["qid"]: (block, q) for block, (_p, qs) in banks.items() for q in qs}
    moved = {b: 0 for b in banks}
    weeked = {b: 0 for b in banks}
    already = {b: 0 for b in banks}
    refiled = {b: 0 for b in banks}
    rerefiled = {b: 0 for b in banks}
    refused = []
    labels = week_labels()
    today = checked or datetime.date.today().isoformat()
    missing = []
    touched = set()
    for row in rows:
        hit = where.get(row["qid"])
        if hit is None:
            missing.append(row["qid"])
            continue
        block, q = hit
        week = int(row["week"])
        if row["verdict"] == REFILING_VERDICT:
            if q.get("family") == OFF or q.get("offCurriculum"):
                continue
            target = block_for_week(week)
            rec = vault_lecture(target, week, row["against"]) if target else None
            if rec is None:
                refused.append(f"{row['qid']}: no vault note '{row['against']}' under week {week}")
                continue
            # already filed here: by an earlier refile, or by its source all along
            if q.get("week") == week and q.get("lecture") == rec["t"] and (
                    q.get("refiled") or q.get("review") == [rec]):
                if q.get("refiled"):
                    q["weekLabel"] = family_label(banks[block][1], q.get("family"), week,
                                                  q["qid"]) or q["weekLabel"]
                rerefiled[block] += 1
                touched.add(block)
                continue
            # `from` is where the question was first filed; a later refile keeps it
            origin = (q.get("refiled") or {}).get("from") or {
                "block": block, "week": q.get("week"), "lecture": q.get("lecture")}
            q["refiled"] = {"from": origin, "on": today}
            q["week"] = week
            q["lecture"] = rec["t"]
            q["review"] = [rec]
            if target != block:
                banks[block][1].remove(q)
                banks[target][1].append(q)
                where[q["qid"]] = (target, q)
                touched.add(target)
            q["weekLabel"] = (family_label(banks[target][1], q.get("family"), week, q["qid"])
                              or labels.get(week, week_label(week)))
            refiled[block] += 1
            touched.add(block)
            continue
        if row["verdict"] in MOVING_VERDICTS:
            if q.get("offCurriculum") or q.get("restored"):
                already[block] += 1
                continue
            previous = q.get("family")
            q["family"] = OFF
            q["week"] = week
            q["weekLabel"] = week_label(week)
            flag = {"type": "note", "title": "Off-curriculum", "html": off_flag_html(row)}
            q["flags"] = [flag] + list(q.get("flags") or [])
            q["offCurriculum"] = {"reason": row["verdict"], "from": previous,
                                  "against": row["against"],
                                  "checked": checked or datetime.date.today().isoformat()}
            if row.get("slides"):
                q["offCurriculum"]["slides"] = row["slides"]
            moved[block] += 1
            touched.add(block)
        elif row["verdict"] == "current" and q.get("week") is None:
            q["week"] = week
            q["weekLabel"] = week_label(week)
            weeked[block] += 1
            touched.add(block)
    for block in touched:
        path, qs = banks[block]
        save_bank(path, in_week_order(qs))
    for block in banks:
        if moved[block] or weeked[block] or already[block] or refiled[block] or rerefiled[block]:
            print(f"{block:6s} moved {moved[block]:3d}  week filled {weeked[block]:3d}  "
                  f"already moved {already[block]:3d}  refiled {refiled[block]:3d}  "
                  f"already refiled {rerefiled[block]:3d}")
    for line in refused:
        print(f"refused: {line}", file=sys.stderr)
    if missing:
        print(f"not in any bank: {', '.join(missing)}", file=sys.stderr)


def in_week_order(questions: list[dict]) -> list[dict]:
    """A bank put back in week order, each lecture's questions together.

    The portal draws a week heading whenever `weekLabel` changes and a lecture
    heading whenever `lecture` changes, in bank order. A question refiled in
    place, or appended after a move between banks, would open a second heading
    for a week or lecture already shown. The sort is by week, then by where
    that week's lecture first appears in the bank; it is stable, so questions
    keep their order within a lecture and a sorted bank comes back unchanged.
    A week that carries two labels (endo Week 1's CBL and DSSG cases) keeps
    each label's questions together. Questions with no week go last.

    Parameters
    ----------
    questions : list of dict
        A bank, in file order.

    Returns
    -------
    list of dict
        The same questions, reordered.
    """
    first: dict[tuple, int] = {}
    for i, q in enumerate(questions):
        first.setdefault((q.get("week"), q.get("weekLabel")), i)
        first.setdefault((q.get("week"), q.get("weekLabel"), q.get("lecture")), i)

    def key(q: dict) -> tuple:
        week, label = q.get("week"), q.get("weekLabel")
        return (week is None, week if week is not None else 0,
                first[(week, label)], first[(week, label, q.get("lecture"))])

    return sorted(questions, key=key)


def family_label(questions: list[dict], family: str, week: int, qid: str) -> str | None:
    """The `weekLabel` a family's other questions in a week already carry, if any.

    A refiled question takes its neighbours' label, so it sits under their
    week heading rather than opening a second one with different wording.

    Parameters
    ----------
    questions : list of dict
        The bank the question is filed in.
    family : str
        The question's family.
    week : int
        The week it is filed under.
    qid : str
        The question itself, which does not count as its own neighbour.

    Returns
    -------
    str or None
        The most common such label, or None when the family has nothing else
        in that week.
    """
    counts: dict[str, int] = {}
    for q in questions:
        if q.get("family") == family and q.get("week") == week and q["qid"] != qid \
                and q.get("weekLabel"):
            counts[q["weekLabel"]] = counts.get(q["weekLabel"], 0) + 1
    return max(counts, key=counts.get) if counts else None


def restore(qids: list[str], note: str) -> None:
    """Put a moved question back in the set it came from.

    Her call outranks the audit: a question she says is fair game returns to
    its original family, keeps the week it was given, and loses the
    Off-curriculum flag and record. A `restored` record stays on the question
    so a later `apply` leaves it alone.

    Parameters
    ----------
    qids : list of str
        Questions to restore.
    note : str
        Why, in one sentence; stored on the question.
    """
    banks = all_banks()
    where = {q["qid"]: (block, q) for block, (_p, qs) in banks.items() for q in qs}
    touched = set()
    for qid in qids:
        hit = where.get(qid)
        if hit is None or not hit[1].get("offCurriculum"):
            print(f"not off-curriculum: {qid}")
            continue
        block, q = hit
        off = q.pop("offCurriculum")
        q["family"] = off["from"]
        q["flags"] = [f for f in (q.get("flags") or []) if f.get("title") != "Off-curriculum"]
        q["restored"] = {"from": off["reason"], "on": datetime.date.today().isoformat(), "note": note}
        touched.add(block)
        print(f"restored {qid} to {off['from']}")
    for block in touched:
        path, qs = banks[block]
        save_bank(path, qs)


def review_week_disagrees(q: dict) -> bool:
    """True when every resolved lecture sits in a week other than the filed one.

    Off-curriculum questions are skipped: their week is the nearest lecture's
    by construction and their review is informational.
    """
    if q.get("family") == OFF or not q.get("review") or q.get("week") is None:
        return False
    return all(r.get("w") != q.get("week") for r in q["review"])


def lecture_is_week_title(q: dict) -> bool:
    """True when `lecture` merely repeats the week label, so no lecture is named."""
    if q.get("family") == OFF:
        return False
    label = q.get("weekLabel") or ""
    lecture = (q.get("lecture") or "").strip()
    tail = re.sub(r"^Week \d+\s*[-–]\s*", "", label).strip()
    return bool(lecture) and bool(tail) and lecture.lower() == tail.lower()


def report() -> None:
    """Print, per block, the questions per family, the null weeks, and the
    off-curriculum qids grouped by reason."""
    for block, (_p, qs) in all_banks().items():
        fams: dict[str, int] = {}
        for q in qs:
            fams[q.get("family") or "?"] = fams.get(q.get("family") or "?", 0) + 1
        nulls = sum(1 for q in qs if q.get("week") is None)
        print(f"== {block}: {len(qs)} questions, null week {nulls}")
        for fam, n in fams.items():
            print(f"   {fam:14s} {n:4d}")
        bad = [q["qid"] for q in qs if review_week_disagrees(q)]
        print(f"   misfiled {len(bad)}: {', '.join(bad)}")
        titled = [q["qid"] for q in qs if lecture_is_week_title(q)]
        print(f"   lecture is the week title {len(titled)}: {', '.join(titled)}")
        by_reason: dict[str, list[str]] = {}
        for q in qs:
            oc = q.get("offCurriculum")
            if oc:
                by_reason.setdefault(oc.get("reason", "?"), []).append(q["qid"])
        for reason, qids in sorted(by_reason.items()):
            print(f"   off-curriculum, {reason} ({len(qids)}): {', '.join(qids)}")


def lecture_note(block: str, entry: dict) -> Path | None:
    """Find the vault lecture note a `review` entry points at.

    Parameters
    ----------
    block : str
        Block slug.
    entry : dict
        One ``review`` item, ``{"w": week, "n": "NN", "t": title}``.

    Returns
    -------
    Path or None
        The note, or None if it is not in the vault.
    """
    week_dir = LECTURE_NOTES / BLOCKS[block][0] / f"Week {entry.get('w')}"
    exact = week_dir / f"{entry.get('n')} - {entry.get('t')}.md"
    if exact.exists():
        return exact
    if not week_dir.is_dir():
        return None
    for f in week_dir.glob(f"{entry.get('n')} - *.md"):
        return f
    return None


def candidates(course: str, block: str, week: int | None) -> None:
    """Print the questions most likely to need a human read.

    Those with no `review`, no week, from a handed-down bank, whose resolved
    lecture sits in another week, whose `lecture` is only the week's title, or
    whose review note was edited after the bank was last written.

    Parameters
    ----------
    course : str
        Course directory.
    block : str
        Block slug.
    week : int or None
        Restrict to one week.
    """
    path = bank_path(block, course)
    bank_mtime = path.stat().st_mtime
    rows = []
    for q in load_bank(path):
        if week is not None and q.get("week") != week:
            continue
        why = []
        if not q.get("review"):
            why.append("no review")
        if q.get("week") is None:
            why.append("no week")
        if q.get("family") in READ_FAMILIES:
            why.append(q["family"])
        if review_week_disagrees(q):
            why.append(f"review week {q['review'][0]['w']} != filed week {q['week']}")
        if lecture_is_week_title(q):
            why.append("lecture is the week title")
        for entry in q.get("review") or []:
            note = lecture_note(block, entry)
            if note is not None and note.stat().st_mtime > bank_mtime:
                why.append(f"note newer: {note.stem}")
                break
        if why:
            rows.append((q["qid"], q.get("family") or "", str(q.get("week")), "; ".join(why)))
    width = max([len(r[0]) for r in rows] + [3])
    print(f"{'qid':{width}s}  {'family':12s} {'week':5s} why")
    for qid, fam, wk, why in rows:
        print(f"{qid:{width}s}  {fam:12s} {wk:5s} {why}")
    print(f"{len(rows)} candidates")


def vault_note(qid: str) -> Path | None:
    """The vault question note a vault-authored qid's heading lives in.

    Parameters
    ----------
    qid : str
        E.g. ``"workbook-repro-Q83"``.

    Returns
    -------
    Path or None
        The note, searching the flat folder and its ``Preclerkship Workbook``
        subfolder, or None.
    """
    m = re.match(r"^([a-z]+)-([a-z]+)-Q", qid)
    if not m or m.group(1) not in QID_NOTE or m.group(2) not in BLOCKS:
        return None
    name = f"{QID_NOTE[m.group(1)]} - {BLOCKS[m.group(2)][1]}.md"
    for folder in (QUESTION_NOTES, QUESTION_NOTES / "Preclerkship Workbook"):
        if (folder / name).exists():
            return folder / name
    return None


def find_heading(lines: list[str], qid: str) -> int | None:
    """Index of the ``# N`` heading for a qid, or None when not exactly one.

    Parameters
    ----------
    lines : list of str
        The note's lines.
    qid : str
        The qid; what follows ``-Q`` is the heading's number (``E2`` included).

    Returns
    -------
    int or None
        Line index, or None if absent or ambiguous.
    """
    num = qid.rsplit("-Q", 1)[1]
    hits = [i for i, line in enumerate(lines) if line.rstrip() == f"# {num}"]
    if len(hits) > 1:
        # a qid comment under one of them settles which
        hits = [i for i in hits
                if any(f"qid: {qid} " in lines[j] or lines[j].rstrip().endswith(f"qid: {qid} -->")
                       for j in range(i + 1, min(i + 4, len(lines))))]
    return hits[0] if len(hits) == 1 else None


def mark_vault(rows: list[dict], dry: bool) -> None:
    """Mark moved and re-filed vault-authored questions under their ``# N`` heading.

    Parameters
    ----------
    rows : list of dict
        Audit rows; only moving and misfiled ones are marked.
    dry : bool
        Report what would change, write nothing.
    """
    where = {q["qid"]: q for _b, (_p, qs) in all_banks().items() for q in qs}
    edits: dict[Path, list[tuple[str, list[str], str]]] = {}
    not_found = []
    skipped = 0
    for row in rows:
        if row["verdict"] not in MOVING_VERDICTS + (REFILING_VERDICT,):
            continue
        q = where.get(row["qid"], {})
        source = (q.get("offCurriculum") or {}).get("from") or q.get("family")
        if source not in VAULT_FAMILIES:
            skipped += 1
            continue
        note = vault_note(row["qid"])
        if note is None:
            not_found.append(f"{row['qid']} (no note)")
            continue
        if row["verdict"] == REFILING_VERDICT:
            # not a `set:` marker: that one names a family, and an export reads it
            block = [f"<!-- refiled | week: {int(row['week'])} | lecture: {row['against']} "
                     f"| qid: {row['qid']} -->", ""]
            marker = "<!-- refiled "
        else:
            sentence = off_sentence(row["verdict"], row["against"],
                                    (row.get("evidence") or "").strip(), "**%s**",
                                    row.get("slides") or "")
            block = [f"<!-- set: offcurriculum | reason: {row['verdict']} | qid: {row['qid']} -->",
                     "> [!warning] Off-curriculum", f"> {sentence}", ""]
            marker = "<!-- set: offcurriculum "
        edits.setdefault(note, []).append((row["qid"], block, marker))
    marked = present = 0
    for note, items in edits.items():
        lines = note.read_text(encoding="utf-8").split("\n")
        changed = False
        for qid, block, marker in items:
            if any(line.startswith(marker) and line.endswith(f"qid: {qid} -->")
                   for line in lines):
                present += 1
                continue
            i = find_heading(lines, qid)
            if i is None:
                not_found.append(f"{qid} (no unique heading in {note.name})")
                continue
            lines[i + 1:i + 1] = block
            marked += 1
            changed = True
        if changed and not dry:
            with note.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write("\n".join(lines))
    verb = "would mark" if dry else "marked"
    print(f"{verb} {marked}, already marked {present}, not vault-authored {skipped}, "
          f"notes {len(edits)}")
    for nf in not_found:
        print(f"  not found: {nf}")


def main() -> None:
    """Parse the command line and run one subcommand."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("candidates", help="questions most worth a human read")
    c.add_argument("--course", default="pom2")
    c.add_argument("--block", required=True, choices=sorted(BLOCKS))
    c.add_argument("--week", type=int)
    a = sub.add_parser("apply", help="move outdated, not-covered and retired questions; re-file misfiled ones")
    a.add_argument("--checked", help="date stamped on offCurriculum.checked (default: today)")
    a.add_argument("verdicts", nargs="+")
    sub.add_parser("report", help="counts per family and the off-curriculum qids")
    r = sub.add_parser("restore", help="put a moved question back in its original set")
    r.add_argument("--note", required=True, help="why, in one sentence")
    r.add_argument("qids", nargs="+")
    m = sub.add_parser("mark-vault", help="mark moved questions in the vault notes")
    m.add_argument("verdicts", nargs="+")
    m.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.cmd == "candidates":
        candidates(args.course, args.block, args.week)
    elif args.cmd == "apply":
        apply_rows(load_rows(args.verdicts), args.checked)
    elif args.cmd == "report":
        report()
    elif args.cmd == "restore":
        restore(args.qids, args.note)
    else:
        mark_vault(load_rows(args.verdicts), args.dry_run)


if __name__ == "__main__":
    main()
