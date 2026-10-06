# Refile Misfiled Questions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every live PoM 2 endocrinology and reproduction question sits under the week and lecture that teach it this year, the three open misfiling reports (#29, #31, #33) are resolved, and the weekly pipeline gains a check that stops this recurring.

**Architecture:** The portal's week filter and the bank's week/lecture headings read `week`, `weekLabel` and `lecture` off each question. The `review` field (what `tools/review_lectures.py` resolves) only changes the "go and read" line. So a HippoNotes question filed by its 2023 week label shows under the wrong week even when `review` points at the right lecture. The fix is a new audit verdict, `misfiled`, that `tools/curriculum_audit.py apply` acts on by rewriting `week`/`weekLabel`/`lecture` (and `review`) from the lecture named in the verdict, plus a `report` gate that counts live questions whose resolved lecture's week disagrees with their filed week. An Opus reader produces the verdicts for endo and repro. The pom2-week skill's Stage 4b adopts the verdict and the gate.

**Tech Stack:** Python 3 (stdlib only, as the rest of `tools/`), pytest for `tools/tests/`, the medwiki Obsidian vault at `/mnt/c/Users/nsims/medwiki`.

**Spec:** this plan is its own spec. Background: GitHub issues schulichmed/preclerkship #29/#30 (hippo-repro-Q47 belongs to week 5), #31/#32 (hippo-repro-Q49 belongs to the ectopic pregnancy lecture, no lecture linked), #33/#34 (hippo-repro-Q48 not week 6). Reference docs: `skills/pom2-week/SKILL.md` (Stage 2 "Every question names the lecture it tests", Stage 4b "curriculum check"), `build/curriculum_audit/AUDIT_BRIEF.md`, `tools/curriculum_audit.py` module docstring, `tools/review_lectures.py` module docstring.

## Global Constraints

- **qids never change.** Progress and Anki cards join on them.
- Question banks are written compact: `json.dumps(qs, ensure_ascii=False)`, UTF-8, LF, no trailing newline (`save_bank` already does this; use it).
- `data/notes/*.json` are `indent=1`; they are regenerated from the vault, never hand-edited.
- Lecture names in `lecture` and `review[].t` are **the vault's spelling**, i.e. the `.md` filename under `/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2/<block>/Week N/` minus the `NN - ` prefix and `.md`. `review_lectures.py` route 3 (`lecture-name`) resolves exactly that.
- The canonical `weekLabel` for a week is `label` from `pom2/data/notes/<block>.json` → `weeks[]` (e.g. `"Week 5 - Pregnancy: Fertility, Genetics, Antenatal Care & Hypertension"`).
- Block week spans come from `tools/portal.py` COURSES: endo 1–3, repro 4–6, msk 7–11, neuro 12–16, psych 17–20. A question whose lecture's week is outside its bank's span moves to the bank that owns that week.
- Off-curriculum questions (`family == "offcurriculum"`) and the `offCurriculum`/`restored` records are left exactly as they are.
- Prose in the skill, README and brief keeps the author's voice: plain sentences, no em dashes.
- Scope: `pom2/data/questions/endo.json` and `repro.json` only. Do not read or edit msk, neuro, psych, fom, pom1 or t2c banks except where `review_lectures.py --derive` drift forces a `git checkout` (see Task 3).
- Never run `tools/rosters_from_vault.py` or `charts_from_vault.py` without `export POM2_VAULT="/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2"`.
- Do not commit anything inside the vault; Obsidian Git syncs it.
- Commit after each task, on `main`. Do not push until Task 5.

## Review Focus

Inputs the plan implies but no test fully exercises, most likely to bite first:

1. **A `misfiled` row whose `against` lecture does not exist in the vault** must be refused with the qid printed, not applied, otherwise `lecture` becomes a name route 3 cannot resolve and the question silently loses its review line. Test in Task 1.
2. **A `misfiled` row whose week lies outside the question's bank** must move the question to the owning bank and remove it from the old one, in one save. Test in Task 1.
3. **Applying the same verdict file twice** changes nothing the second time and reports "already refiled". Test in Task 1.
4. **A HippoNotes question whose `lecture` is still the week title** (e.g. `"Labour, Delivery, the Puerperium & the Newborn"`) after the read means the reader skipped it; `report` lists it under "lecture is the week title" so the gate catches it. Test in Task 1.
5. **`review_lectures.py --derive` drift** on banks outside endo/repro: after the run, `git diff --stat` must show only endo.json and repro.json changed, or the banks are checked out and `apply` is rerun. Procedure in Task 3.

---

### Task 1: The `misfiled` verdict in `tools/curriculum_audit.py`

**Files:**
- Modify: `tools/curriculum_audit.py` (module docstring, constants after `READ_FAMILIES`, `apply_rows`, `report`, `candidates`, `mark_vault`, `main`)
- Create: `tools/tests/test_curriculum_audit.py`

**Interfaces:**
- Consumes: existing `bank_path`, `load_bank`, `save_bank`, `load_rows`, `all_banks`, `BLOCKS`, `LECTURE_NOTES`, `VAULT_FAMILIES`, `vault_note`, `find_heading`.
- Produces, for Tasks 2–4:
  - verdict row shape `{"qid": str, "verdict": "misfiled", "week": int, "against": "<NN - Lecture as the vault spells it>", "evidence": str, "note": str}`
  - `python3 tools/curriculum_audit.py apply <files>` refiles `misfiled` rows
  - `python3 tools/curriculum_audit.py report` prints, per block, `misfiled N: <qids>` (review week disagrees with filed week) and `lecture is the week title N: <qids>`; both must read 0 for endo and repro when the work is done
  - `python3 tools/curriculum_audit.py candidates --block <slug>` lists those two conditions as reasons
  - a `refiled` record on each refiled question: `{"from": {"block": str, "week": int, "lecture": str}, "on": "YYYY-MM-DD"}`

- [ ] **Step 1: Write the failing tests**

Create `tools/tests/test_curriculum_audit.py`:

```python
# -*- coding: utf-8 -*-
"""
Purpose: pin what curriculum_audit.py does with a `misfiled` verdict
Author: Noor Sims
Date: 2026-10-06
Input: temporary question banks and note rosters built in tmp_path
Output: pytest results
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import curriculum_audit as ca  # noqa: E402


def question(qid, week, label, lecture, family="hipponotes"):
    return {"qid": qid, "num": qid.rsplit("Q", 1)[1], "week": week, "weekLabel": label,
            "lecture": lecture, "lectureMeta": "x", "family": family, "source": "hippo",
            "sourceLabel": "HippoNotes", "stem": "<p>s</p>", "kind": "mcq",
            "options": [{"letter": "A", "html": "a"}], "correct": ["A"], "answer": "<p>a</p>",
            "flags": [], "tags": [], "review": [], "retired": False}


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A repo with endo and repro banks, note rosters and a vault of two lectures."""
    root = tmp_path / "repo"
    (root / "pom2" / "data" / "questions").mkdir(parents=True)
    (root / "pom2" / "data" / "notes").mkdir(parents=True)
    endo = [question("hippo-endo-Q1", 2, "Week 2 - Thyroid", "Thyroid")]
    repro = [question("hippo-repro-Q47", 6, "Week 6 - Labour", "Labour"),
             question("hippo-repro-Q50", 6, "Week 6 - Labour", "Labour")]
    (root / "pom2/data/questions/endo.json").write_text(json.dumps(endo), encoding="utf-8")
    (root / "pom2/data/questions/repro.json").write_text(json.dumps(repro), encoding="utf-8")
    for slug, weeks in (("endo", [(2, "Week 2 - Thyroid"), (3, "Week 3 - Adrenal")]),
                        ("repro", [(5, "Week 5 - Pregnancy"), (6, "Week 6 - Labour")])):
        notes = {"block": slug, "weeks": [{"week": w, "label": lab, "lectures": []}
                                          for w, lab in weeks]}
        (root / f"pom2/data/notes/{slug}.json").write_text(json.dumps(notes), encoding="utf-8")
    vault = tmp_path / "vault" / "01 - Lectures" / "99 - PoM 2"
    (vault / "02 - Repro" / "Week 5").mkdir(parents=True)
    (vault / "02 - Repro" / "Week 5" / "11 - Approach to First Trimester Bleeding & Ultrasound.md").write_text("# x")
    (vault / "01 - Endocrinology" / "Week 3").mkdir(parents=True)
    (vault / "01 - Endocrinology" / "Week 3" / "01 - Adrenal Gland Disease.md").write_text("# x")
    monkeypatch.setattr(ca, "ROOT", root)
    monkeypatch.setattr(ca, "LECTURE_NOTES", vault)
    return root


def bank(root, slug):
    return json.loads((root / f"pom2/data/questions/{slug}.json").read_text(encoding="utf-8"))


def test_misfiled_rewrites_week_label_lecture_and_review(repo):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    q = bank(repo, "repro")[0]
    assert q["week"] == 5
    assert q["weekLabel"] == "Week 5 - Pregnancy"
    assert q["lecture"] == "Approach to First Trimester Bleeding & Ultrasound"
    assert q["review"] == [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    assert q["refiled"] == {"from": {"block": "repro", "week": 6, "lecture": "Labour"},
                            "on": "2026-10-06"}
    assert q["qid"] == "hippo-repro-Q47"


def test_misfiled_is_idempotent(repo, capsys):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-07")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "already refiled   1" in capsys.readouterr().out


def test_misfiled_outside_block_moves_banks(repo):
    row = {"qid": "hippo-repro-Q50", "verdict": "misfiled", "week": 3,
           "against": "01 - Adrenal Gland Disease", "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    assert [q["qid"] for q in bank(repo, "repro")] == ["hippo-repro-Q47"]
    moved = [q for q in bank(repo, "endo") if q["qid"] == "hippo-repro-Q50"]
    assert len(moved) == 1
    assert moved[0]["week"] == 3 and moved[0]["weekLabel"] == "Week 3 - Adrenal"
    assert moved[0]["refiled"]["from"]["block"] == "repro"


def test_misfiled_unknown_lecture_is_refused(repo, capsys):
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "99 - No Such Lecture", "evidence": "", "note": ""}
    before = (repo / "pom2/data/questions/repro.json").read_bytes()
    ca.apply_rows([row], checked="2026-10-06")
    assert (repo / "pom2/data/questions/repro.json").read_bytes() == before
    assert "hippo-repro-Q47" in capsys.readouterr().err


def test_misfiled_does_not_touch_off_curriculum(repo):
    qs = bank(repo, "repro")
    qs[0]["family"] = "offcurriculum"
    qs[0]["offCurriculum"] = {"reason": "retired", "from": "hipponotes", "against": "x",
                              "checked": "2026-10-05"}
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    row = {"qid": "hippo-repro-Q47", "verdict": "misfiled", "week": 5,
           "against": "11 - Approach to First Trimester Bleeding & Ultrasound",
           "evidence": "", "note": ""}
    ca.apply_rows([row], checked="2026-10-06")
    assert bank(repo, "repro")[0]["week"] == 6


def test_report_counts_review_week_disagreement_and_week_titles(repo, capsys):
    qs = bank(repo, "repro")
    qs[0]["review"] = [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.report()
    out = capsys.readouterr().out
    assert "misfiled 1: hippo-repro-Q47" in out
    assert "lecture is the week title 2: hippo-repro-Q47, hippo-repro-Q50" in out


def test_candidates_names_both_reasons(repo, capsys):
    qs = bank(repo, "repro")
    qs[0]["review"] = [{"w": 5, "n": "11", "t": "Approach to First Trimester Bleeding & Ultrasound"}]
    (repo / "pom2/data/questions/repro.json").write_text(json.dumps(qs), encoding="utf-8")
    ca.candidates("pom2", "repro", None)
    out = capsys.readouterr().out
    assert "review week 5 != filed week 6" in out
    assert "lecture is the week title" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/test_curriculum_audit.py -q 2>&1 | tail -15`
Expected: every test FAILS (`apply_rows` ignores `misfiled`, `report` prints no such lines, `candidates` has no such reasons).

- [ ] **Step 3: Implement**

In `tools/curriculum_audit.py`:

(a) Extend the module docstring. After the paragraph beginning "A moved question keeps its qid", add:

```
A `misfiled` verdict re-files a live question under the lecture that teaches
it this year: `week`, `weekLabel` and `lecture` are rewritten from the lecture
named in `against`, `review` is set to that lecture, and a `refiled` record
keeps where it came from. A question whose lecture's week lies outside its
bank's span moves to the bank that owns that week. The portal's week filter and
its week and lecture headings read `week` and `lecture`, not `review`, which is
why a right `review` on a wrong `week` still shows under the wrong week.
```

(b) After `READ_FAMILIES`, add:

```python
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
    """The `review` record for a lecture named as `NN - Title`, if the vault has it.

    Parameters
    ----------
    block : str
        Block slug that owns `week`.
    week : int
        Course week.
    against : str
        ``"11 - Approach to First Trimester Bleeding & Ultrasound"``.

    Returns
    -------
    dict or None
        ``{"w": week, "n": "11", "t": "Approach to ..."}``, or None when no such
        note exists under that week's folder.
    """
    m = re.match(r"^([\d.]+)\s*[-–]\s*(.+?)\s*$", against or "")
    if not m:
        return None
    num, title = m.group(1), m.group(2)
    note = LECTURE_NOTES / BLOCKS[block][0] / f"Week {week}" / f"{num} - {title}.md"
    if not note.exists():
        return None
    return {"w": week, "n": num, "t": title}
```

(c) In `apply_rows`, add counters and a branch. After `already = {b: 0 for b in banks}` add:

```python
    refiled = {b: 0 for b in banks}
    rerefiled = {b: 0 for b in banks}
    refused = []
    labels = week_labels()
    today = checked or datetime.date.today().isoformat()
```

Then, inside the loop, before `if row["verdict"] in MOVING_VERDICTS:`, add:

```python
        if row["verdict"] == REFILING_VERDICT:
            if q.get("family") == OFF or q.get("offCurriculum"):
                continue
            target = block_for_week(week)
            rec = vault_lecture(target, week, row["against"]) if target else None
            if rec is None:
                refused.append(f"{row['qid']}: no vault note '{row['against']}' under week {week}")
                continue
            if q.get("week") == week and q.get("lecture") == rec["t"] and q.get("refiled"):
                rerefiled[block] += 1
                continue
            q["refiled"] = {"from": {"block": block, "week": q.get("week"),
                                     "lecture": q.get("lecture")}, "on": today}
            q["week"] = week
            q["weekLabel"] = labels.get(week, week_label(week))
            q["lecture"] = rec["t"]
            q["review"] = [rec]
            if target != block:
                banks[block][1].remove(q)
                banks[target][1].append(q)
                where[q["qid"]] = (target, q)
                touched.add(target)
            refiled[block] += 1
            touched.add(block)
            continue
```

Change the summary print to:

```python
    for block in banks:
        if moved[block] or weeked[block] or already[block] or refiled[block] or rerefiled[block]:
            print(f"{block:6s} moved {moved[block]:3d}  week filled {weeked[block]:3d}  "
                  f"already moved {already[block]:3d}  refiled {refiled[block]:3d}  "
                  f"already refiled {rerefiled[block]:3d}")
    for line in refused:
        print(f"refused: {line}", file=sys.stderr)
```

Update the `apply_rows` docstring first line to "Re-file every outdated, not-covered or misfiled question, and fill null weeks."

(d) Add two helpers above `report` and use them in `report` and `candidates`:

```python
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
```

In `report`, after the `for fam, n in fams.items()` loop, add:

```python
        bad = [q["qid"] for q in qs if review_week_disagrees(q)]
        print(f"   misfiled {len(bad)}: {', '.join(bad)}")
        titled = [q["qid"] for q in qs if lecture_is_week_title(q)]
        print(f"   lecture is the week title {len(titled)}: {', '.join(titled)}")
```

In `candidates`, after `if q.get("family") in READ_FAMILIES:` block, add:

```python
        if review_week_disagrees(q):
            why.append(f"review week {q['review'][0]['w']} != filed week {q['week']}")
        if lecture_is_week_title(q):
            why.append("lecture is the week title")
```

Update `candidates` docstring: "Those with no `review`, no week, from a handed-down bank, whose resolved lecture sits in another week, whose `lecture` is only the week's title, or whose review note was edited after the bank was last written."

(e) In `mark_vault`, make `misfiled` rows on vault-authored families leave a comment marker (so a later re-export from the vault knows the filing changed). Change `if row["verdict"] not in MOVING_VERDICTS: continue` to `if row["verdict"] not in MOVING_VERDICTS + (REFILING_VERDICT,): continue`, and build the block as:

```python
        if row["verdict"] == REFILING_VERDICT:
            block = [f"<!-- set: refiled | week: {int(row['week'])} | lecture: {row['against']} "
                     f"| qid: {row['qid']} -->", ""]
            marker = "<!-- set: refiled "
        else:
            sentence = off_sentence(...)   # unchanged
            block = [...]                  # unchanged
            marker = "<!-- set: offcurriculum "
        edits.setdefault(note, []).append((row["qid"], block, marker))
```

and in the write loop unpack `for qid, block, marker in items:` and test `line.startswith(marker)` instead of the literal. Update the `mark_vault` docstring: "Mark moved and re-filed vault-authored questions under their ``# N`` heading."

(f) In `main`, change the `apply` help to `"move outdated, not-covered and retired questions; re-file misfiled ones"`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd /home/nsims/repos/preclerkship && python3 -m pytest tools/tests/ -q 2>&1 | tail -5`
Expected: all tests in `test_curriculum_audit.py` PASS and `test_infographic.py` still passes.

- [ ] **Step 5: Run `report` on the real banks and record the baseline**

Run: `cd /home/nsims/repos/preclerkship && python3 tools/curriculum_audit.py report 2>&1 | grep -E "^==|misfiled|week title"`
Expected: endo shows `misfiled 11` and repro `misfiled 57` (the counts measured on 2026-10-06 before any refiling), and both blocks show a non-zero "lecture is the week title" count made of hippo qids. Paste the output into the task report.

- [ ] **Step 6: Commit**

```bash
git add tools/curriculum_audit.py tools/tests/test_curriculum_audit.py
git commit -m "curriculum_audit: add the misfiled verdict, a refile gate in report, and tests"
```

---

### Task 2: Read the reproduction bank and write the refile verdicts

**Files:**
- Create: `build/curriculum_audit/repro_refile.qids.json` (the qid list read)
- Create: `build/curriculum_audit/repro_refile.json` (one verdict row per qid)
- Modify: `pom2/data/questions/repro.json` (and `endo.json` if a question's lecture is taught in weeks 1–3) via `apply` only

**Interfaces:**
- Consumes: `python3 tools/curriculum_audit.py candidates --block repro`, `apply`, `report` from Task 1; vault lecture notes under `/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2/02 - Repro/Week {4,5,6}/` and `01 - Endocrinology/Week {1,2,3}/`.
- Produces: `report` showing `misfiled 0` and `lecture is the week title 0` for repro.

- [ ] **Step 1: Build the qid list**

Live (not off-curriculum) repro questions that are any of: `family == "hipponotes"`; `review_week_disagrees`; `lecture_is_week_title`. Write a short python3 script in the scratchpad that imports `tools/curriculum_audit.py` and writes `build/curriculum_audit/repro_refile.qids.json` as a JSON list of qids. Expected size: about 95 hippo plus about 38 others (57 disagreeing minus the 19 hippo among them), so roughly 130. Print the count.

- [ ] **Step 2: Dump the chunk to plain text and read the lecture rosters**

Follow `build/curriculum_audit/AUDIT_BRIEF.md` "Method" steps 1 and 2: dump qid, filed week, lecture, review, stem, options, key and the first 400 chars of the answer with HTML stripped, in slices of 20–30; then list the lecture note filenames of repro weeks 4–6 and endo weeks 1–3 (`ls` each `Week N` folder) and skim each note's chart region once, so every question can be placed against a real filename.

- [ ] **Step 3: Decide each question's lecture**

For each qid, the lecture that teaches the tested discriminator this year, named exactly as its vault filename minus `.md`, e.g. `"09 - Early Pregnancy Complications"` for ectopic pregnancy (week 4), `"11 - Approach to First Trimester Bleeding & Ultrasound"` for hCG trends and CRL dating (week 5). Rules:

- `grep -ril "<term>" "<block folder>"` across both blocks before deciding; the lecture is where the fact is stated, not where the source filed it.
- If the lecture's week equals the filed week and `lecture` already names it, the verdict is `current` (row still written, `against` the lecture, so the read is on record).
- If the lecture's week differs from the filed week, or `lecture` is the week title, the verdict is `misfiled` with `week` = that lecture's week.
- If two lectures in the same week share the material, pick the one whose note states the key's discriminator; name the other in `note`.
- If the fact appears in no lecture this year, the verdict is `not-covered` (the existing audit verdict; `apply` moves it to Off-curriculum). Expect few: the 2026-10-05 audit already read these banks.
- A wrong key on taught material stays `current`/`misfiled` with `KEY?` in `note` (do not fix keys here).
- Never guess. If unsure, `current` with `UNVERIFIED` in `note`.

The three reported questions must come out as: hippo-repro-Q47 → `misfiled`, week 5, `11 - Approach to First Trimester Bleeding & Ultrasound`; hippo-repro-Q48 → `misfiled`, week 5, same lecture (CRL dating once an embryo is seen is first-trimester ultrasound; verify the note says so, and if the note places CRL dating elsewhere, follow the note and say so in the report); hippo-repro-Q49 → `misfiled`, week 4, `09 - Early Pregnancy Complications` (verify the note covers ectopic pregnancy risk factors; if PID as the commonest cause is stated only in another note, name that one).

- [ ] **Step 4: Write the verdict file and check it**

`build/curriculum_audit/repro_refile.json`: a JSON list, one object per qid in the qid list, in order, each `{"qid", "verdict": "current|misfiled|not-covered", "against": "<NN - Lecture>", "week": <int>, "evidence": "<quote ≤200 chars>", "note": "<one sentence or empty>"}`. Then run a check script: `len(rows) == len(qids)`, every qid present once, every `against` exists as `<vault>/<block folder>/Week <week>/<against>.md`. Fix any that fail before applying.

- [ ] **Step 5: Apply and verify**

```bash
cd /home/nsims/repos/preclerkship
python3 tools/curriculum_audit.py apply build/curriculum_audit/repro_refile.json
python3 tools/curriculum_audit.py report 2>&1 | grep -E "^==|misfiled|week title"
```
Expected: `apply` prints `refused:` for nothing; `report` shows repro `misfiled 0` and `lecture is the week title 0`. Then confirm the three reported questions directly:

```bash
python3 - <<'EOF'
import json
qs=json.load(open('pom2/data/questions/repro.json'))
for q in qs:
    if q['qid'] in ('hippo-repro-Q47','hippo-repro-Q48','hippo-repro-Q49'):
        print(q['qid'], q['week'], q['lecture'], q['review'], q.get('refiled'))
EOF
```
Expected: weeks 5, 5, 4 with the lectures from Step 3.

- [ ] **Step 6: Mark the vault-authored ones**

```bash
python3 tools/curriculum_audit.py mark-vault --dry-run build/curriculum_audit/repro_refile.json
python3 tools/curriculum_audit.py mark-vault build/curriculum_audit/repro_refile.json
```
Expected: the dry run names only workbook/weekly/module/meds2029 qids (hippo is "not vault-authored" and is regenerated in Task 4); the real run marks the same count.

- [ ] **Step 7: Commit**

```bash
git add build/curriculum_audit/repro_refile.json build/curriculum_audit/repro_refile.qids.json pom2/data/questions/repro.json pom2/data/questions/endo.json
git commit -m "Repro: refile the questions filed under the wrong week or with no lecture named (fixes #29, #31, #33)"
```

---

### Task 3: Read the endocrinology bank and write the refile verdicts

**Files:**
- Create: `build/curriculum_audit/endo_refile.qids.json`, `build/curriculum_audit/endo_refile.json`
- Modify: `pom2/data/questions/endo.json` (and `repro.json` for the workbook-repro questions filed in endo whose lecture is in weeks 4–6) via `apply` only

**Interfaces:** same as Task 2, block `endo`, vault folder `01 - Endocrinology/Week {1,2,3}/`, cross-block folder `02 - Repro/Week {4,5,6}/`.

- [ ] **Step 1: Build the qid list** exactly as Task 2 Step 1 for `--block endo` → `build/curriculum_audit/endo_refile.qids.json`. Expected roughly 63 hippo plus 11 disagreeing non-hippo (the 9 `workbook-repro-*` in endo pointing at the week 5 breast lectures, and `workbook-endo-Q61/Q62` pointing at week 3 PMOS).

- [ ] **Step 2: Dump and read** as Task 2 Step 2, with endo's three week folders read fully and repro's three listed.

- [ ] **Step 3: Decide each lecture** by the Task 2 Step 3 rules. The nine `workbook-repro-*` questions in endo.json: if the breast lectures (`06 - Pathology of the Breast`, `07 - Approach to Common Breast Problems`, week 5) are where the material is taught, they are `misfiled` to week 5 and `apply` will move them into `repro.json`. Say in `note` which of the two breast lectures states the discriminator and put that one in `against`.

- [ ] **Step 4: Write and check the verdict file** as Task 2 Step 4 → `build/curriculum_audit/endo_refile.json`.

- [ ] **Step 5: Apply and verify**

```bash
python3 tools/curriculum_audit.py apply build/curriculum_audit/endo_refile.json
python3 tools/curriculum_audit.py report 2>&1 | grep -E "^==|misfiled|week title"
```
Expected: endo and repro both `misfiled 0` and `lecture is the week title 0`.

- [ ] **Step 6: Mark the vault-authored ones** as Task 2 Step 6 with the endo file.

- [ ] **Step 7: Commit**

```bash
git add build/curriculum_audit/endo_refile.json build/curriculum_audit/endo_refile.qids.json pom2/data/questions/endo.json pom2/data/questions/repro.json
git commit -m "Endo: refile the questions filed under the wrong week or with no lecture named"
```

---

### Task 4: Rebuild the portal, regenerate the HippoNotes vault backup, and teach the skill

**Files:**
- Modify: `skills/pom2-week/SKILL.md` (Stage 2 "And the lecture decides the week" paragraph; Stage 4 bullet list; Stage 4b verdict table, the sentence after it, and "The procedure" steps)
- Modify: `build/curriculum_audit/AUDIT_BRIEF.md` (Method step 3 and Output shape)
- Modify: `pom2/README.md` (field table: `refiled` row)
- Modify (generated): `pom2/data/notes/*.json`, `pom2/*.html`, `index.html`, `pom2/data/questions/*.json` (review only)
- Modify (vault, not committed here): `/mnt/c/Users/nsims/medwiki/00 - Practice Questions/HippoNotes - Endocrinology.md` and `HippoNotes - Reproduction.md` via `tools/vault_backup.py questions`

**Interfaces:**
- Consumes: Tasks 2–3 banks; `report` gate.
- Produces: a rebuilt site whose bank pages serve the refiled JSON; a skill that runs the gate every week.

- [ ] **Step 1: Pull, then rebuild** (Stage 5 of the skill, verbatim):

```bash
cd /home/nsims/repos/preclerkship && git pull --ff-only
export POM2_VAULT="/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2"
python3 tools/rosters_from_vault.py
python3 tools/charts_from_vault.py
python3 tools/roman_items.py
python3 tools/question_figures.py
python3 tools/review_lectures.py --derive
git diff --stat -- '*/data/questions/*.json'
```
Expected: the diff touches only `pom2/data/questions/endo.json` and `repro.json`. If any other bank changed, run `git checkout -- fom/data/questions pom1/data/questions t2c/data/questions pom2/data/questions/msk.json pom2/data/questions/neuro.json pom2/data/questions/psych.json` and note the drift in the task report. Then check the refiled questions kept their review:

```bash
python3 tools/curriculum_audit.py report 2>&1 | grep -E "^==|misfiled|week title"
```
Expected: endo and repro still `misfiled 0`. If a refiled question now has an empty `review`, its `lecture` name did not resolve by route 3: fix the `against` in the verdict file, `git checkout` the two banks, re-run `apply` for both files, and re-run `--derive`.

```bash
python3 tools/build_pages.py
python3 tools/build_index.py
python3 tools/build_hub.py
python3 -m pytest tools/tests -q
```

- [ ] **Step 2: Regenerate the HippoNotes backup notes in the vault**

```bash
python3 tools/vault_backup.py questions --dry-run
python3 tools/vault_backup.py questions
grep -n "^## \|^#### " "/mnt/c/Users/nsims/medwiki/00 - Practice Questions/HippoNotes - Reproduction.md" | head -40
```
Expected: the dry run lists the HippoNotes endo and repro notes as the ones it would rewrite; afterwards the repro note's `####` headings are lecture names, not week titles, and `hippo-repro-Q49` sits under `## Week 4 ...` / `#### Early Pregnancy Complications`.

- [ ] **Step 3: Correct Stage 2 of the skill**

In `skills/pom2-week/SKILL.md`, replace the paragraph that begins `**And the lecture decides the week, not the other way round.**` (currently ending "...so a correct link quietly corrects a wrong heading.") with:

```
**And the lecture decides the week, not the other way round.** Where a question's material is
taught in a different week from the one the source filed it under, the lecture link is still the
lecture that teaches it - do not move the link to fit the heading. But a correct link does not
fix the filing on its own: the portal's week filter and its week and lecture headings read the
question's `week`, `weekLabel` and `lecture` fields, and `review` only changes the "go and read"
line. Three HippoNotes questions filed under their 2023 week shipped under Week 6 with a review
line pointing at Week 5 and were reported by readers on 2026-10-06. So the question is re-filed
in the JSON too: Stage 4b's `misfiled` verdict does it, and its report gate catches any that
were not.
```

- [ ] **Step 4: Add the export rule to Stage 4**

In Stage 4's bullet list, after the bullet that begins "The field list is in `pom2/README.md`", add:

```
- **A week-only bank gets its week from the lecture, not from the source.** HippoNotes and the
  Schulich Reviews group questions by the week of the year they were written in, and those weeks
  no longer match this year's. Export each such question with `week`, `weekLabel` and `lecture`
  set to the lecture that teaches it now, named as the vault spells it, so the week filter puts
  it where she will look for it. A question you cannot place yet keeps the source's week and
  Stage 4b's read places it.
```

- [ ] **Step 5: Teach Stage 4b the verdict and the gate**

In the Stage 4b verdict table, add a row after `not-covered`:

```
| `misfiled` | the tested fact is taught, but in a different week or lecture from where the question is filed, or no lecture is named | re-file under that lecture: `apply` rewrites `week`, `weekLabel`, `lecture` and `review`, and moves it to the owning block's bank if the week is in another block |
```

Replace the sentence `A question taught in a different week or lecture from where its source filed it is `current`.` with:

```
A question taught in a different week or lecture from where its source filed it, or whose
`lecture` is only the week's title, is `misfiled`, not `current`; it stays live and is re-filed.
```

In "The procedure", change the sentence after the `candidates` command so it reads: "lists the questions most likely to need a read: no `review`, no week, a handed-down family, a `review` whose week disagrees with the filed week, a `lecture` that only repeats the week title, or a `review` note edited after the bank was last written."

Change step 1's format line to `{qid, verdict, against, week, evidence, note}`, verdict one of `current | outdated | not-covered | misfiled`.

Change step 2 to: "`python3 tools/curriculum_audit.py apply build/curriculum_audit/<slug>_<chunk>.json` moves the outdated and not-covered ones and re-files the misfiled ones. Applying the same file twice changes nothing."

Change step 4 to: "`python3 tools/curriculum_audit.py report` **must show zero null weeks, zero `misfiled` and zero `lecture is the week title`** for the block. A null week is a question that will sit under a "No week" chip on the portal; a misfiled one sits under the wrong week with a review line that contradicts it, which is exactly what readers reported on 2026-10-06."

- [ ] **Step 6: Update the brief and the README**

`build/curriculum_audit/AUDIT_BRIEF.md`, Method step 3: change the `current` bullet's second sentence from "Taught in another week or lecture than filed is still current." to "Taught in another week or lecture than filed, or with `lecture` naming only the week, is `misfiled`: still live, re-filed under that lecture; `week` is that lecture's week and `against` its note name." In Output, change `"verdict": "current|outdated|not-covered"` to `"verdict": "current|outdated|not-covered|misfiled"`.

`pom2/README.md` field table: after the `restored` row add:

```
| `refiled` | only on a question an audit re-filed under the lecture that teaches it this year: `{"from": {"block": "<bank it left>", "week": <week it was filed under>, "lecture": "<lecture it named>"}, "on": "YYYY-MM-DD"}`. `week`, `weekLabel` and `lecture` are the lecture's; `review` points at the same lecture. |
```

- [ ] **Step 7: Commit**

```bash
git add -A pom2 index.html skills/pom2-week/SKILL.md build/curriculum_audit/AUDIT_BRIEF.md docs/superpowers/plans/2026-10-06-refile-misfiled-questions.md
git status --short | head -30
git commit -m "Rebuild after refiling; pom2-week Stage 4b gains the misfiled verdict and a zero-misfiled gate"
```
Expected: `git status --short` before the commit shows only generated pages, the two banks, notes JSON, the skill, the brief and the README.

---

### Task 5: Push and close the reports

Done by the orchestrator, not an agent.

- [ ] **Step 1:** `git push origin main`.
- [ ] **Step 2:** Comment on and close issues #29, #31, #33 and pull requests #30, #32, #34 via the GitHub REST API with the stored git credential, saying what each question was refiled to and that the fix landed on main, so the flag PRs are superseded.
- [ ] **Step 3:** Delete the superseded branches `report/29`, `report/31`, `report/33` on the remote.
