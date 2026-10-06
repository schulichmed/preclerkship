# Endo + repro curriculum audit, and an Off-curriculum question set

Date: 2026-10-05. Owner: Noor Sims. Executed one Opus agent at a time.

## Goal

Every PoM 2 endocrinology and reproduction question on the portal is either current to this
year's lecture slides, or sits in a new **Off-curriculum** question set. "Off-curriculum" stops
being a week chip (today it is `week: null`, 7 endo + 6 repro, all workbook extras).

## What counts as current

The medwiki lecture notes under `01 - Lectures/99 - PoM 2/01 - Endocrinology` and `02 - Repro`
were brought up to this year's slides on 2026-10-03 (vault commits "up to this year's slides").
They are the reference. Where a note is silent on an exact value, the slide PDF in
`/mnt/c/Users/nsims/OneDrive/Documents/` or `/mnt/c/Users/nsims/Downloads/` decides.

| Verdict | Meaning | Action |
| --- | --- | --- |
| `current` | the tested fact is taught in this year's block notes, and the key agrees | nothing |
| `outdated` | this year's lecture contradicts the key or the stem's premise | move to Off-curriculum, say what the slide now says |
| `not-covered` | the tested fact appears in none of this year's block notes (follow transclusions) | move to Off-curriculum, name the nearest lecture |

A question taught in a different week or lecture from where its source filed it is `current`.
A wrong peer-written key on taught material is a key fix (existing bug-flag process), not a move.
Adjacent clinical depth that the lecture does not go into (a drug the note never names, a
staging system the slides skip) is `not-covered`.

## Data model

- New family in `tools/portal.py` (pom2): `{"key": "offcurriculum", "name": "Off-curriculum"}`,
  listed last. Blurb in her voice, no em dashes: these are questions from the handed-down banks
  that this year's lectures do not teach, or teach differently, kept for anyone who wants them.
- A moved question keeps `qid`, `num`, `source`, `sourceLabel`, `lecture`, `lectureMeta`,
  `options`, `correct`, `answer`, `retired`, `tags`. It gains:
  - `family: "offcurriculum"`
  - `week`: the week of the nearest lecture (never null); `weekLabel: "Week N"`
  - a first `flags` entry `{"type": "note", "title": "Off-curriculum", "html": "<p>...</p>"}`
    saying whether it is not taught or taught differently, naming the lecture checked
  - `offCurriculum: {"reason": "not-covered" | "outdated", "from": "<original family>",
    "against": "<lecture note name>", "checked": "2026-10-05"}`
- `quiz.js`: the `week === null` label becomes "No week" (three places), so the chip can never
  read as the set. After this run no endo or repro question has a null week.
- Vault: families authored in the vault (module, weekly, workbook, meds2029) get a marker under
  the `# N` heading, in the `med-questions` marker form:
  `<!-- set: offcurriculum | reason: not-covered | qid: ... -->` plus a
  `> [!warning] Off-curriculum` callout. HippoNotes and Schulich Reviews are backed up from JSON
  by `tools/vault_backup.py questions`, which must file an off-curriculum question under its
  `offCurriculum.from` family's note.

## Steps (one agent each, in order)

1. **Audit agents** (Opus, sequential), one per chunk of about 120 questions:
   endo W1a, W1b, W2a, W2b, W3a, W3b (+ the 7 null-week), repro W4a, W4b, W5, W6 (+ the 6
   null-week). Each writes `build/curriculum_audit/<slug>_<chunk>.json`:
   `[{qid, verdict, against, week, evidence, note}]`, one row per qid in the chunk, evidence a
   quote of at most 200 characters from the note or slide.
2. **Apply agent**: write `tools/curriculum_audit.py` (`candidates`, `apply`, `report`), apply
   every verdict file, add the family, fix `quiz.js`, mark the vault notes, extend
   `vault_backup.py`, rebuild, diff the banks for `review` drift, update `pom2/README.md` and
   `tools/README.md`, commit. No push.
3. **Skill agent**: add the curriculum check to `skills/pom2-week/SKILL.md` as a stage that runs
   after Stage 1 rewrites a note and after Stage 4 exports, using the tool from step 2; add the
   `set: offcurriculum` marker to the vault's `med-questions/SKILL.md`.
4. **Verify** (main session): counts, no null weeks, rebuild clean, spot-check ten verdicts.

## Refinement after chunk 1 (endo W1a)

This year's own sources (`weekly`, `module`, `meds2029`) are curriculum by definition and only
get the `outdated` test. The strict `not-covered` test applies to the handed-down banks
(`workbook`, `hipponotes`, `reviews`), and reaching the key by elimination does not count as
covered. weekly-endo-Q10 and Q12 from chunk 1 therefore stay current (module-only content).
