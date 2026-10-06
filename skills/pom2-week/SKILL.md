---
name: pom2-week
description: Run a week of PoM 2 work end to end, in order - update the medwiki lecture notes from the current OneNote lectures, bank the week's questions from every source, chart them, then ship both to the preclerkship repo as portal JSON, rebuild the site, and update Anki. Use for "do week 2", "catch up endo week 3", "run the weekly pipeline", or any request spanning more than one of med-chart / med-questions / med-anki.
---

# A week of PoM 2, end to end

This skill is the **order and the glue**. The four `med-*` skills own their own formats and
rules. Invoke them, do not restate or second-guess them here - and where one of them is wrong,
fix it in its own file rather than adding a correction to this one, or the fix only exists for
someone who came in through this skill.

Windows paths below (`C:\Users\nsims\...`) are `/mnt/c/Users/nsims/...` from WSL, where this
session and the repo run.

**Read first:** `C:\Users\nsims\medwiki\CLAUDE.md` (vault conventions) and
`/home/nsims/repos/preclerkship/README.md` (the rebuild order, under "Rebuilding") and
`pom2/README.md` (PoM 2's sources and field list).

## The unit of work is one block-week

| Block | Vault folder | Weeks | Portal slug |
| --- | --- | --- | --- |
| 1 Endocrinology | `01 - Endocrinology` | 1-3 | `endo` |
| 2 Reproduction | `02 - Repro` | 4-6 | `repro` |
| 3 Musculoskeletal | `03 - MSK` | 7-11 | `msk` |
| 4 Neurology | `04 - Neuro` | 12-16 | `neuro` |
| 5 Psychiatry | `05 - Psych` | 17-20 | `psych` |

Lecture notes live at
`C:\Users\nsims\medwiki\01 - Lectures\99 - PoM 2\<block folder>\Week N\NN - <Lecture>.md`.
Week folders are numbered **across the year, not within the block**, so Repro's weeks are
`Week 4` / `Week 5` / `Week 6` inside `02 - Repro`. The week number in the request is the folder
name, verbatim.

If the request does not name a block and a week, ask once, then run the rest without check-ins
except at the gates below.

## The order, and why it is this order

```
0  inventory            what is here, and is OneNote actually assembled yet
1  notes  <- OneNote    the vault note is rewritten from this year's lecture
2  questions <- notes   every source banked into the vault question notes
3  charts <- questions  the chart is written knowing what gets tested
4  portal JSON <- both  the hand-authored hop, pictures included
4b curriculum check     every question in the block against this year's notes
5  rebuild             four scripts, then commit
6  Anki <- notes        the delta against CLim, prioritised by the chart
7  report
8  late arrivals        quiz, DSSG, in-class cases - optional, never blocking
```

The high-yield signal flows **downhill from the questions**: the questions tell the chart what
matters, the chart tells the Anki pass which of its gaps matter most. That is why questions come
before charts, and why neither can be written from the note alone.

## Where the work lands

**The repo is the destination. Charts and questions ship on the site, not as an Artifact.**

| What | Written to | Shipped by |
| --- | --- | --- |
| Chart | the top of the vault lecture note | `pom2/data/notes/<slug>.json`, then the block page's notes tab |
| Question | a `00 - Practice Questions/` note | `pom2/data/questions/<slug>.json`, then the block page's questions tab |

**The repo is `/home/nsims/repos/preclerkship`** (GitHub `schulichmed/preclerkship`), which holds
FoM, PoM 1, PoM 2 and T2C side by side; PoM 2 lives under `pom2/`. The old
`C:\Users\nsims\OneDrive\Desktop\projects\pom2` repo stopped being updated on 2026-09-23 - never
write to it. The site is <https://schulichmed.github.io/preclerkship/pom2/>, and `quiz.js` is its own question runner with its own
progress store, keyed on the same `qid` and held in the browser's `localStorage`.

**Do not publish a quiz Artifact as part of a week.** The five per-block Artifact hubs that
`med-quiz` documents predate the portal's questions tab and duplicate it. They still exist and
still hold recorded attempts, which is why **qids stay append-only** and
`reorder_bank.py` stays unrun, but regenerating them is **not** a step in this pipeline. Invoke
`med-quiz` only when she asks for a hub by name, or to read progress back out of one.

## Stage 0 - inventory before touching anything

Report this before doing any work, because it decides which stages have anything to do:

- Which lectures are in the week folder, which have a note at all, and which already open with
  `Overview chart:`. **A note existing is not a note being current**, see Stage 1.
- Which lecture slides are available, as a PDF in `C:\Users\nsims\OneDrive\Documents\` or as a
  OneNote page, and which lectures have neither.
- Which question notes in `00 - Practice Questions/` already carry a `## Week N` section for
  this week, and the highest `# N` in each, since that is where new qids continue from.
- Which slide decks for these lectures are on disk. They land flat in `C:\Users\nsims\Downloads\`,
  named by lecturer or by lecture title, so match loosely and list what you found **and what you
  did not**. The Week 2 clinical decks and all of Week 3 endo were never on disk.
- Which Rise module captures are on disk, as `C:\Users\nsims\Downloads\rise-*.js`, and which
  lectures they cover.
- Whether any of the **Stage 8** sources exist yet: a grabbed capture of the week's Elentra quiz,
  notes from the DSSG, notes from the in-class CBL. **Note them, do not chase them.** All three
  are on the course's schedule, so "not there" is the normal state for most of a week and says
  nothing about whether she is behind. Do not ask whether she has sat the quiz or been to the
  session, do not tell her to go, and do not hold any other work for them.

### Is OneNote actually assembled yet

**This is a required-fail check, not an observation.** She assembles the week herself: she
downloads the slides, uploads them to OneNote, and grabs the Rise module in alongside them. Only
then does OneNote hold this year's lecture. Stage 1 rewrites the vault note from OneNote on the
authority that OneNote is current, so running it against a **half-assembled** section does the
one thing worse than leaving a stale note in place: it overwrites good content with last year's,
and reports the overwrite as an update.

So before Stage 1 touches anything, confirm the week's OneNote section holds a page per lecture
in the week folder, with this year's decks in them. One command answers it, against the live
notebook and with no login:

```bash
python tools/onenote_local.py list "Principles of Medicine 2"
```

**If pages are missing, name them and stop.**
Do not proceed on the assumption she will add them; do not treat a thin section as a lecture with
little content.

**Recount every total at the moment you need it.** Never quote a question count from a skill
file, a README, this file, or a memory. Use `len()` over `pom2/data/questions/<slug>.json`, and say
when the count was taken.

## Stage 1 - update the vault lecture notes from OneNote

**This is work, not a check, and it comes first.** OneNote holds the current lectures. The vault
lecture note is written from them, and everything downstream is written from the vault note. So
every run of this skill **updates the week's medwiki notes from the current OneNote lectures
before anything else happens**. Skipping straight to questions or charts is the single most
damaging thing this pipeline can do, because a chart, its questions, its cards and its portal
page are all only as current as the note underneath them, and **nothing downstream can detect a
stale note**.

For every lecture in the week, in this order:

1. **Pull the current lecture from OneNote** (routes below).
2. **Write or update
   `01 - Lectures\99 - PoM 2\<block>\Week N\NN - <Lecture>.md` from it.** A missing note gets
   written. An existing note gets brought up to the lecture as it now stands: sections the
   lecture added, content it changed, figures it introduced. Follow the note's transclusions
   before concluding a topic is absent, since a note's byte size understates its coverage.
3. **Only then bank its questions** (Stage 2), and chart it after that (Stage 3).

Updating the body is a separate act from charting. The chart sits above the `---`, and
everything from the `> [!check] Objectives` callout down is the note's own body, which is what
this stage writes.

### OneNote outranks what is already in the note

**The lecture slides are the gold standard**, whether they sit in OneNote or as a deck in
`C:\Users\nsims\Downloads\`. They beat the vault note, her cards, review decks and textbook
teaching. When a card, chart or question is disputed, check the **slide itself**, not the vault
note, and never correct anything to standard teaching when the slide says otherwise; flag it.

**Most pre-existing medwiki lecture content is an upper year's notes, "Maggie's notes", not
hers and not this year's course.** Nothing in the vault says so: there is no provenance line, no
frontmatter field, and `CLAUDE.md` does not mention it. A note that reads as authoritative and
complete may be entirely inherited.

So when OneNote and the existing note disagree, **OneNote wins and the note gets corrected**.
This is not a merge and not a both-sides note. Replace the conflicting content, do not append the
current version underneath the old one and do not soften it into "some sources say".

- **Conflicting** content is overwritten from OneNote.
- **Absent** content, in OneNote but not in the note, is added.
- **Extra** content, in the note but not in this year's lecture, is left alone unless it
  contradicts OneNote. An upper year's note going deeper than the lecture is not a conflict, it
  is context.

**Report every override**: the lecture, what the note said, what OneNote says. Correcting the
note silently is what makes an inherited error indistinguishable from taught material next time
anyone reads it. The report is the only record, since the note keeps no history of what it used
to say.

This ordering holds for anything derived downstream too. Where a chart, a question's reasoned
answer, or a card was built on inherited content that OneNote contradicts, it is wrong at the
source and gets rebuilt, not patched. **Every override is also a trigger for Stage 4b on that
lecture's questions**, because the slide change that corrected the note can invalidate a
question's key.

### Staleness has to be read, not detected

**There is no automated sync and no provenance line in the note.** A lecture note records nothing
about which slide version it came from, so staleness cannot be found by timestamp or diff. The
note has to be read against the lecture. Do not skip a note because it looks long or looks
finished, and especially not because it looks polished: inherited notes are the polished ones.

Report every lecture as **written**, **updated**, **already current**, or **not updatable** with
the reason, and list the overrides made under each. "Already current" is a claim about content,
so only make it after actually comparing, never because a note exists.

**Getting at the slides.** Two routes, in order of preference:

1. **The PDF export in `C:\Users\nsims\OneDrive\Documents\`.** Named either by the vault lecture
   name (`04 - Clinically Useful Endocrine Principles.pdf`) or by the OneNote page title
   (`UME P2 Endocrine Pharmacology (Pharmacology of T2DM).pdf`), so match on both.
2. **OneNote itself, through `tools/onenote_local.py` in the preclerkship repo.** It drives the
   installed desktop app over COM, which is already signed in, so there is **no login, no
   token and nothing to expire**. The ms365 MCP server is not the route any more: it has been
   refused since 2026-09-07 with `AADSTS50158`, a Duo challenge on a stale token. Do not try to
   fix that, and do not ask her to run `login`.

   From the preclerkship repo root, under either interpreter - this one takes a script file, so the
   pyenv shim that mangles a multi-line `-c` is not in play:

   ```bash
   python tools/onenote_local.py list "Principles of Medicine 2"    # path :: title :: id
   python tools/onenote_local.py page --find "<title fragment>" --slides
   ```

   `list` prints the full path through the section group, and `--find` refuses an ambiguous
   match rather than guessing - which is what keeps the two `Synch W1`s and two `Synch W2`s in
   this notebook apart. Narrow with `--notebook` when a fragment hits more than one.

   **Her typed notes come first, and they are the point.** `page` prints them under
   `## typed notes` before anything else: they are her annotation rather than the lecturer's
   slide, and they are the most valuable thing on the page. **Incorporate them into the vault
   note alongside the slide content.** A page that looks thin is *not* proof it is title-only -
   this cost a wrong answer on 2026-09-07, when her note on the Synch W2 hypothyroidism page
   was skipped on the assumption the body was image-only.

   **`--slides` gives you the slide text as text.** OneNote has already run OCR over every
   printout and stores it in the page, so the words on the decks need no image download and no
   contact sheets. Two limits on that text: the OCR garbles small type and logos (`Western`
   comes back as `NVestern`), so **confirm any exact value - a dose, a lab number, a cutoff -
   against the PDF** rather than banking it from OCR; and a **figure is still pixels**, so a
   diagram, a graph or a histology image is read from the route-1 PDF.

   Handwritten ink is **not** part of this routine. Her typed notes are what this stage
   incorporates; don't go after ink unless she asks for it by name.

   The tool needs `powershell.exe` and Office 16, so it works on her laptop and nowhere else.
   If the app will not start, OneNote's own automatic backups under
   `%LOCALAPPDATA%/Microsoft/OneNote/16.0/Backup` hold the same text, and `strings -el` reads a
   `.one` section file without any app at all - but flattened, so her notes and the lecturer's
   slides are no longer separable. Treat that as evidence of what a page said, not as a source
   for Stage 1.

Reading OneNote needs no permission and no network. *Posting* to OneNote is a gate further down.

## Stage 2 - questions into the vault

**A patient is the discriminator.** A question that presents a patient and reasons through them
is a **case**, and every case belongs to `New Questions - <topic>.md` with
`family: "meds2029"`, `source: "module-case"` - **whatever source it came from**: an Elentra
module knowledge check, a lecture slide, a DSSG, an in-class case. A case goes to `meds2029`
even when it carries lettered options, and a check on understanding stays in the module set
even when it is a one-line vignette. **Options are not the discriminator, a patient is.**

This rule governs every source below, and belongs at the top of the stage. Nested inside the
slide-deck sweep it read as deck-only, which is what let 38 endo cases sit under the module
family until 2026-09-08.

**A case already banked in the wrong note is marked, not moved.** Moving one changes its `qid`,
which orphans the `med-quiz` progress and the Anki cards joined on it. Leave the block where it
is and emit the marker directly under its `# N` heading:

```
<!-- set: meds2029 | source: module-case | qid: module-endo-Q99 -->
```

**An export reads the marker, not the note it is sitting in**; an unmarked question belongs to
the note's own family. Before Stage 5, check that the markers in the vault and the `meds2029`
entries in `pom2/data/questions/<slug>.json` name the same set.

### Every question names the lecture it tests, not just the week

**The week is a given. The lecture is the thing she actually has to go back and read.** A
question that resolves only to "Week 4 - Gynecology: Contraception, STIs, Pelvic Pain &
Menopause" has told her nothing she did not already know from the filter she used to get there,
and a week of PoM 2 is sixteen lectures deep.

So **every question banked in the vault carries its lecture**, and it carries it in a form that
resolves against the vault rather than in prose:

- The `#### group` heading is **the lecture's own name as the vault spells it**, minus the
  number. `#### Contraception`, not `#### Contraceptive methods`, because
  `01 - Lectures/99 - PoM 2/02 - Repro/Week 4/03 - Contraception.md` is the note it has to find.
- Where the group's name cannot be the lecture's - a CBL, a DSSG, a HippoNotes chapter, a
  workbook group spanning three lectures - the group carries an explicit
  **`Tests [[NN - Lecture]]`** line naming every lecture it draws on, the way the workbook notes
  already do:

  ```
  #### Pelvic pain, endometriosis & PID
  *Workbook Q15, Q34-Q38, Q138. Tests [[11 - Clinical Approach to Acute Pelvic Pain]],
  [[12 - Clinical Approach to Chronic Pelvic Pain]], [[10 - Endometriosis]].*
  ```

- **The link has to resolve.** A `Tests [[...]]` naming a note that does not exist is worse than
  no line at all, because it reads as attribution and is not. `tools/review_lectures.py` reports
  every one it cannot resolve; a run that names any is not finished.

**Name the lecture that teaches the material, not the session that asked the question.** A DSSG
case on adrenal incidentalomas tests `[[01 - Clinical Presentation and Evaluation of Adrenal
Gland Disease]]`; "DSSG - Approach to Adrenal & Pituitary Issues" is where it was asked, which is
already in `lectureMeta` and is not a lecture.

**And the lecture decides the week, not the other way round.** Where a question's material is
taught in a different week from the one the source filed it under, the lecture link is still the
lecture that teaches it - do not move the link to fit the heading. But a correct link does not
fix the filing on its own: the portal's week filter and its week and lecture headings read the
question's `week`, `weekLabel` and `lecture` fields, and `review` only changes the "go and read"
line. Three HippoNotes questions filed under their 2023 week shipped under Week 6 with a review
line pointing at Week 5 and were reported by readers on 2026-10-06. So the question is re-filed
in the JSON too: Stage 4b's `misfiled` verdict does it, and its report gate catches any that
were not.

### A case with no question posed asks for its reveal

**Every case in a slide deck or a module is banked, including the ones that pose no question.**
The usual shape is a `Case Presentation` slide, then the gross, histology or imaging pictures,
then the diagnosis named in a caption, a heading or an answer slide. The deck is asking *what is
this?* without printing the words, and that ask is the question to bank:

- **Stem**: `Which of the following is the most likely diagnosis?`, or the reveal's own kind where
  the deck reveals a next step or a management choice instead. The case is the case slide plus
  what the pictures show on their face.
- ⭐ **The reveal stays out of the case.** No caption words, and nothing from a later slide that
  names the answer. A shot of the primary tumour is a reveal too, however clinical it looks.
- **Options are a differential**: the diagnosis plus three others **the same deck teaches** that
  the case has to be told apart from, such as the same lineage with a different behaviour, or the
  same gross look from a different lineage. Plain diagnosis names, not statements, and no
  behaviour tails. A tail like *"- benign germ cell tumour"* on one option hands over the answer.
- **The answer** cites the reveal slide, then says from the deck why each other diagnosis fails.
- A teaching slide after the reveal (behaviour, markers, treatment) may become **a follow-up
  question after the diagnosis question, never instead of it**.
- Mark the stem `*(stem assembled from slides N-M, leaving out the caption that names the
  diagnosis; the deck poses no question)*`, and carry the same slide range into `lectureMeta`.

*Worked example, 2026-09-28: the six `Case Presentation` slides in the Approach to and
Pathology of a Pelvic Mass deck (`Armstrong_OvarianNeoplasms_slides.pdf`) are `new-repro-Q89-96`
in `New Questions - Reproduction.md`. The first pass asked "which statement is correct?" and
"what should the pathologist report?", and one case gave away its gastric primary. All of them
now ask for the diagnosis, with a differential as the options.*

### Every option has to look like the answer

**The medicine is the only thing allowed to pick the key out of the set.** Anything else that
singles it out is a **tell**, and one tell turns a case into a formatting puzzle she can solve
without reading it. Three have shipped and been caught after the fact, each in a different
currency. Check all three before banking, and again before the Stage 4 export:

- **Length.** Write every option to roughly the length of the longest one. A key that is
  qualified - *"..., so they confirm she is thyrotoxic but are not specific to Graves; the
  Graves-specific findings are absent"* - sitting above three four-word distractors is readable
  across the room. ⭐ **The qualification belongs in the answer callout, not in the option**: the
  option states the claim, the callout does the reasoning. **Measure it, do not eyeball it** -
  `len()` every option and confirm the key is not the longest. *Observed 2026-09-09: the key was
  the longest option in 18 of 24 DSSG questions, up to 4.8x the mean distractor.*
- **Markup.** Options carry **none** - no `**bold**`, no ⭐ or ⚠, and ⭐ **no wikilinks**, which
  `portal.css` paints in accent ink with a dotted underline while plain options stay black.
  Whatever markup one option carries, all of them carry. Stems and answer callouts keep their
  wikilinks; those give nothing away. `.opt .wl` is neutralised in `portal.css` as a backstop, but
  it knows only that one class - a lone `<strong>` is the same tell in another colour. *Observed
  2026-09-08: 252 endo options carried a wikilink, and in 16 questions exactly one option was
  tinted and it was the key.*
- **Position.** Spread the key across A-D, and check the spread **over the batch**, not per
  question. *Observed 2026-09-09: a first pass keyed all 25 new questions to A.*

The vault note and the portal JSON both carry the option text, so a tell fixed in one is still
live in the other. **Fix it in the vault note and re-export.**

### Nothing enters a question that the material did not put there

**Ask the source's own question, verbatim.** A DSSG prompt, an Elentra stem, a deck's Concept
Check: copy it, do not improve it. Its typos, its missing punctuation and its wrong units are
copied too and flagged in a `> [!warning]`, ⭐ **never silently corrected**. **Verify the copy
mechanically** rather than by eye - normalise whitespace and case, then assert each stem is a
substring of the extracted source text. Eyeballing missed a dropped question mark and a
`mmol/L`-for-`pmol/L` on the same pass that felt careful.

**Bank the questions the source asks, and no others.** The count comes from the source: 24
prompts is 24 questions. A question the material never asks is out of scope however good it is,
and a plausible one is worse than an obvious one because nothing later flags it.

**Build options and answers from the block's own notes.** ⭐ **Grep the block before asserting a
clinical fact in an answer** - if the phrase is not there, it is not available, whatever you know
about the medicine. Where a case turns on something the notes genuinely lack, ⭐ **say so in the
answer and leave it open for the facilitator**; do not fill the gap from elsewhere and let it
read as taught material.

*Observed 2026-09-09, all four from one DSSG pass: a thyroid bruit, non-pitting edema, a pleural
effusion and a thyroiditis timeline in months were all reasoned into answers, and none of the
four appears anywhere in the endocrinology block.* The notes usually carry a **better**
discriminator than the one being reached for - goiter symmetry, the wide-versus-narrow pulse
pressure and the Woltman sign were all sitting in the same table.

Invoke **`med-questions`**. Two sources are available the moment the lecture is, and they never
merge across notes:

- **Elentra module knowledge checks** into `Module Questions - <topic>.md`. **Do not transcribe
  these by hand.** Rise ships a whole module, keys included, as one `runtime-data.js`, so the
  Rise grab in the bookmarks bar fetches it without reading the page, and it decodes with:

  ```
  python "C:\Users\nsims\medwiki\.scripts\rise_to_bank.py" "<bank note>.md" C:\Users\nsims\Downloads\rise-*.js
  ```

  It appends each module as its own `#### <module title>` section and continues the `# N`
  numbering from whatever is already in the bank. **Re-running with a module already present is
  a no-op**, so running it over the whole `Downloads` folder is safe and is usually the right
  call. It also records an image card's referenced filename and emits `![[filename]]`, which is
  where Stage 4's picture rule picks up.

  > `rise_to_bank.py` and `reorder_bank.py` sit in the same directory. You run the first one
  > every week. You never run the second - see the qid rule below.

- **Slide decks, split by what the slide is.** A comprehension check goes to
  `Module Questions - <topic>.md` under its own `#### Concept Checks - <Lecture>` heading. A
  **patient case** goes to `New Questions - <topic>.md`, `family: "meds2029"`,
  `source: "module-case"`. This is the routing rule, not a guideline. See the sweep below, which
  `med-questions` does not cover.

The **weekly quiz, the DSSG cases and the in-class CBL cases** are not here. They arrive on the
course's schedule rather than hers, so they are **Stage 8**, and a week is complete without any
of them.

**Watch for the same question arriving twice.** A module and its lecturer's deck are often the
same slides, so a knowledge check can come in through both the Rise grab and the sweep. **Grep
the existing banks for a distinctive stem phrase before transcribing** or the same question gets
banked twice under a second qid.

**qids are append-only.** New questions take the next number, removed ones are marked retired and
left in place. **Never run `medwiki\.scripts\reorder_bank.py`**: it renumbers the join key shared
by the vault notes, the five quiz artifact databases, `data/questions/*.json`, and roughly 5,500
Anki cards.

### Sweeping a slide deck

**An Elentra module with no knowledge checks does not mean the lecture has no questions.** Four
Week 1 endo lectures with confirmed-empty modules carry real questions in their decks.

Use **PyMuPDF, not `pdftotext`**, at
`C:\Users\nsims\.pyenv\pyenv-win\versions\3.9.13\python.exe` (it carries PyMuPDF 1.26.5). Write
sweep output to a UTF-8 file, since the console's `cp1252` dies on Wingdings arrows.

**Three shapes, not one.** Each miss below was a real one:

1. **Option-shaped lines.** `^\s*\(?([a-eA-E1-5])[.)]\s*\S` is right. Do **not** require
   whitespace after the marker: the `\s+` version misses `1.T2DM IS DIAGNOSED...`, which is how
   one deck writes every option, and it hid that slide through two separate sweeps.
2. **A case marker** (`NN-year-old`, `Case N`, `POP QUIZ`) **with an ask** (`What should...`,
   `Back to the cases`). This finds short-answer vignettes with no lettered options. Missing it
   lost the Glycemic Goals target-A1c cases and recorded that deck as having no questions.
3. **Any patient-shaped slide at all**, even with no question posed, which finds worked case
   illustrations. Missing it lost four more cases across three decks.

**Four answer-marking mechanisms.** Decks key answers by:

- (a) repeating the slide with the correct option **bolded** (`span["flags"] & 16`, which
  `pdftotext` discards);
- (b) an explicit `ANSWERS` slide a page or two later;
- (c) a **coloured highlight box drawn around the correct options in place**. This is a vector
  shape, invisible to `pdftotext` and to any span or bold read. Detect it with
  `page.get_drawings()`, match the fill colour, and test which lines' vertical midpoint falls
  inside the box. Missing this made three keyed questions look unkeyed and hid that one keys
  *two* correct options;
- (d) **✓ / ✗ glyphs per option** (U+2713 / U+2717). These are in the text layer, but they
  **extract in a different order than they appear**, so match each glyph to its option by
  vertical position, never by reading order.

Beware bold numbered diagram labels, which are false positives for (a).

**Routing every swept slide.** The two destinations are decided by what the slide *is*, and the
decks do not use one word for it. Observed labels include `Concept Check`,
`CHECK YOUR UNDERSTANDING` and `POP QUIZ`, so **read the slide, do not match the heading**:

| The slide is | Destination | Fields |
| --- | --- | --- |
| A check on understanding: a standalone question testing whether the last few slides landed | `Module Questions - <topic>.md`, under `#### Concept Checks - <Lecture>` | the note's usual `module` family |
| A **case**: a patient presented and reasoned through, whether or not a question is posed | `New Questions - <topic>.md` | `family: "meds2029"`, `source: "module-case"` |

The case rule at the top of this stage decides the row. Sweep shape 3 exists precisely because
some cases pose no question at all, and those are still cases.

Cases sit beside the CBL and DSSG questions in `New Questions` because that note is where
reasoned answers live, and a deck case is usually keyed by the lecturer's own worked reasoning
rather than by an answer letter.

## Stage 3 - charts

Invoke **`med-chart`** per lecture in the week whose note is current after Stage 1. One chart per
lecture, at the top of the lecture note itself.

**Apply the block's Schulich Reviews digest when one exists.** MSK, Neuro and Psych were
reviewed before they were taught, so their review points wait in
`<block folder>/Schulich Reviews - <Block>.md`, filed by week and lecture. When charting a lecture
listed there, **bold** each point the chart already carries, and put the rest in one
`> [!tip] Schulich Reviews` callout inside the chart region. **This year's lecture outranks the
review**: a point OneNote contradicts goes in as the lecture says it, or not at all, and is
reported. The review decides what is high yield, not what is true.

**The chart is written after the questions, and reads them.** By this point the week's questions
are banked, and they are the best available evidence of what the course actually tests. Open the
week's new questions for the lecture before charting it: what they turn on belongs on the chart,
and a discriminator three questions hinge on is not an optional row. This is the reason Stage 2
comes first, and charting a lecture whose questions have not been banked yet throws that away.

Bold marks the testable discriminator only. Stage 6 reads the bolded spans as its **priority
signal** - which of its gaps matter most - not as its list of cards; the note is the card source,
not the chart.

**A lecture whose note Stage 1 could not bring up to date does not get charted.** Report it as
skipped. A chart is the wrong place to discover the note was out of date.

## Stage 4 - the manual hop into the portal JSON

`data/questions/*.json` **has no extractor**. Every week it is re-authored by hand from the vault
notes. This is the one unautomated step in the chain, so budget for it.

- **Re-check the option sets as you export them** - length parity, no markup, key spread across
  A-D (see *Every option has to look like the answer*, Stage 2). The export is where a wikilink
  becomes a tinted option, because the vault note legitimately carries links the site must not.
- The shipped files are **compact** JSON (`json.dumps` default separators, UTF-8, LF, no trailing
  newline), unlike `data/notes/*.json` which is `indent=1`.
- The field list is in `pom2/README.md`. `keyed: false`, `unscorable: true` and
  `retired: true` carry real meaning, do not flatten them.
- **A week-only bank gets its week from the lecture, not from the source.** HippoNotes and the
  Schulich Reviews group questions by the week of the year they were written in, and those weeks
  no longer match this year's. Export each such question with `week`, `weekLabel` and `lecture`
  set to the lecture that teaches it now, named as the vault spells it, so the week filter puts
  it where she will look for it. A question you cannot place yet keeps the source's week and
  Stage 4b's read places it.
- **A matching question ships as a dropdown grid, never as an MCQ over complete mappings**
  ("1-W, 2-X, 3-Y") or as one question per item. Give it `kind: "pairing"` and a `pairs` object
  (see `module-repro-Q2`), and add its spec to `tools/pairings/` so `tools/curated_pairings.py`
  re-applies it after any re-export.
- If `tools/questions_from_vault.py` exists by the time you read this, it replaces this stage and
  must run **before** `rosters_from_vault.py`, which borrows its week headings from the questions
  JSON.

### An option carries no markup the other options lack

`<span class="wl">` is how the vault's wikilinks render, and it is the easiest thing to paste in
by accident, because the vault note links the concept the answer names. In an option it tints
that one choice and dotted-underlines it while the rest stay plain, which reads as the key. Endo
shipped 252 of these; 16 questions had exactly one tinted option and it was the correct one.

- **Strip wikilink spans out of every option**, keeping the text. Stems and answer bodies may
  keep theirs - they give nothing away.
- The rule is wider than `.wl`: **whatever markup one option carries, all of them carry**. A lone
  `<strong>` or `<em>` is the same tell in a different colour. `pom2.css` neutralises `.opt .wl`
  as a backstop, but the backstop only knows about that one class.

### Questions with pictures

Some questions are answerable only from an image, and the module sometimes tests the image
itself. **The picture ships inside the question**, as a `data:` URI in the stem HTML - there is no
image field, no assets directory, and `quiz.js` needs no image handling because it renders the
stem as HTML. This is existing practice; it works; keep doing it:

- **Re-compress before embedding.** The vault original can be far larger than the site needs -
  one 3 MB PNG ships as a 75 KB JPEG. Convert to JPEG and keep each picture **under about
  100 KB**. `tools/embed_image.py` does the resolve-compress-encode step in one command.
- **One embed per distinct picture, reused.** Four endo questions share the cortisol figure and
  carry the same embed; do not paste four copies of a different encoding.
- **Report the count in Stage 7.** A dropped question is obvious; a dropped picture is not,
  because the stem still reads as though the image were there.

### Cadaveric images do not ship

Illustrations, radiology, endoscopy, gross pathology specimens and clinical photographs are all
fine and there is approved precedent for every one of them. **Cadaveric images are the exception**
and are covered by a separate protocol.

- **Recognise them by looking at the image, never by which module it came from.** Most anatomy
  module images are imaging or illustrations, and cadaveric images turn up in textbook figures
  too, so the module predicts badly in both directions.
- **Never include one initially.** Ship the question without it, flag the question so the missing
  image shows on its face, and list it for her - she approves case by case.
- **Flag and propose, never substitute.** Where an online alternative would work, name a
  candidate and wait. An anatomy question usually turns on one structure at one angle, and a
  plausible near-miss makes the question quietly wrong, which is worse than a question that says
  its picture is missing.

## Stage 4b - curriculum check

**Every run, without being asked.** Stage 1 has just brought the week's notes up to this year's
slides, and Stage 4 has just exported the week's questions. Now **every question in the block,
not only the week's new ones**, is checked against those notes, because a rewritten note can
invalidate a question banked months ago and nothing else will notice. The plan this came from is
`docs/plans/2026-10-05-endo-repro-curriculum-audit.md`, and the method each read follows is
`build/curriculum_audit/AUDIT_BRIEF.md`. Read the brief before the first read of a run.

Each question gets one of three verdicts, against this year's notes for the block (follow
transclusions before calling anything absent; where a note is silent on an exact value, the slide
PDF decides):

| Verdict | Meaning | Action |
| --- | --- | --- |
| `current` | the tested fact is taught in this year's block notes, and the key agrees | nothing |
| `outdated` | this year's lecture contradicts the key or the stem's premise | move to Off-curriculum, say what the slide now says |
| `not-covered` | the tested fact appears in none of this year's block notes | move to Off-curriculum, name the nearest lecture |
| `misfiled` | the tested fact is taught, but in a different week or lecture from where the question is filed, or no lecture is named | re-file under that lecture: `apply` rewrites `week`, `weekLabel`, `lecture` and `review`, and moves it to the owning block's bank if the week is in another block |
| `retired` | the source itself retired the question (`retired: true`), whatever its content | move to Off-curriculum; her call 2026-10-05, so the retired tag never sits inside a live set |

A question taught in a different week or lecture from where its source filed it, or whose
`lecture` is only the week's title, is `misfiled`, not `current`; it stays live and is re-filed.
Adjacent clinical depth the lecture does not go into (a drug the note never names, a staging
system the slides skip) is `not-covered`.

**Which test applies depends on the family.**

- **This year's own sources, `weekly`, `module` and `meds2029`, get only the `outdated` test.**
  They are curriculum by definition, so `not-covered` is never their verdict; a fact that is in
  the quiz or module but not on the slides is noted `MODULE-ONLY` and stays current.
- **The handed-down banks, `workbook`, `hipponotes` and `reviews`, get the strict test**: the
  discriminator that picks the key has to be stated in this year's notes or slides. **Reaching
  the key by eliminating the other options does not count as covered.**

*Observed 2026-10-05: the first run checked all 1216 endo and repro questions and moved 71, 16
outdated and 55 not-covered, 54 of them workbook. It also found two of this year's own module
questions, module-endo-Q21 and module-repro-Q9, whose slide now contradicts their key. That is
why the `outdated` test runs on this year's sources too: this year's family says where a
question came from, not that its key still matches the slide.*

**Not-covered means the question, not an option.** The thing the stem asks about has to be
untaught. A question whose main discriminator is taught stays current even when one option
leans on a detail the lecture skips, and the gap goes in `note` instead. *Observed 2026-10-05:
hippo-repro-Q8 asks who is eligible for cervical screening; the lecture teaches "from about
age 25, ever sexually active", which is the question, and only the immunocompromised-at-21
option was untaught. It was moved and she called it fair game.* When she overrules a move, run
`python3 tools/curriculum_audit.py restore --note "<why>" <qid>`, which returns the question to
its original set, keeps its week, and marks it `restored` so a later `apply` leaves it alone;
then set that row to `current` in the verdict file and rerun `vault_backup.py questions` if the
set is HippoNotes or Reviews.

### The Off-curriculum set

**A question that fails is moved, never deleted.** It goes into the `offcurriculum` family
("Off-curriculum", listed last in `tools/portal.py`) and keeps everything it had: `qid`, `num`,
`source`, `sourceLabel`, `lecture`, `lectureMeta`, `options`, `correct`, `answer`, `retired`,
`tags`. It gains:

- `family: "offcurriculum"`;
- `week`: the week of the nearest lecture, **never null**, with `weekLabel: "Week N"`;
- a first `flags` entry, `{"type": "note", "title": "Off-curriculum", ...}`, saying whether it is
  not taught or taught differently and naming the lecture it was checked against;
- `offCurriculum: {"reason": "not-covered" | "outdated" | "retired", "from": "<original family>",
  "against": "<lecture note name>", "checked": "<date>"}`.

**qids never change**, here or anywhere: progress and Anki cards join on them.

**A wrong key on taught material is a key fix, not a move.** The question stays `current`, the
read notes it with `KEY?`, and it is fixed through the usual bug flag, in the JSON and the vault
both, rekeyed to the lecture.

### The procedure

```bash
python3 tools/curriculum_audit.py candidates --course pom2 --block <slug> --week N
```

lists the questions most likely to need a read: no `review`, no week, a handed-down family, a
`review` whose week disagrees with the filed week, a `lecture` that only repeats the week title,
or a `review` note edited after the bank was last written. Run it per week of the block. **It is a
shortlist, not the check. The read is the work.** Read each candidate, and **every question
whose lecture note Stage 1 changed this run**, against that note, the way the brief says.

1. Write the verdicts to `build/curriculum_audit/<slug>_<chunk>.json`, one row per question read,
   in the brief's format: `{qid, verdict, against, week, evidence, note}`, verdict one of
   `current | outdated | not-covered | misfiled`, evidence a quote of at most 200 characters
   from the note or slide.
2. `python3 tools/curriculum_audit.py apply build/curriculum_audit/<slug>_<chunk>.json` moves
   the outdated and not-covered ones and re-files the misfiled ones. Applying the same file
   twice changes nothing.
3. `python3 tools/curriculum_audit.py mark-vault --dry-run <files>`, read its line, then the
   same without `--dry-run`. It writes the marker and callout under each moved question's
   `# N` heading in the vault-authored notes; the form is in `med-questions` (the marker
   section), so do not restate it here.
4. `python3 tools/curriculum_audit.py report` **must show zero null weeks, zero `misfiled` and
   zero `lecture is the week title`** for the block. A null week is a question that will sit
   under a "No week" chip on the portal; a misfiled one sits under the wrong week with a review
   line that contradicts it, which is exactly what readers reported on 2026-10-06.
5. Add any `KEY?` rows to `build/curriculum_audit/KEY_ISSUES.md`, for Stage 7.

## Stage 5 - rebuild the portal

**Pull first.** Other sessions of hers commit to this repo, and this stage commits. Check
`git -C <repo> status` and pull before rebuilding - committing on top of a stale read of another
session's work is worse than a stale wikilink, because it is the shared history that ends up
wrong. During one recent session two commits landed mid-conversation from elsewhere.

From the repo root, in this order. Run them from WSL with `python3` (the repo lives at
`/home/nsims/repos/preclerkship`), and point the two vault readers at the WSL mount, since their
defaults are Windows paths and `rosters_from_vault.py` dies on them:

```bash
export POM2_VAULT="/mnt/c/Users/nsims/medwiki/01 - Lectures/99 - PoM 2"
python3 tools/rosters_from_vault.py
python3 tools/figures.py              # only if a chart embeds a picture
python3 tools/charts_from_vault.py
python3 tools/roman_items.py
python3 tools/question_figures.py
python3 tools/review_lectures.py --derive
python3 tools/build_pages.py
python3 tools/build_index.py
python3 tools/build_hub.py
```

The repo `README.md` ("Rebuilding") is the authority on this list and also covers FoM, PoM 1 and
T2C; a week of PoM 2 needs only the lines above.

`review_lectures.py` is the one script here that **does write** `data/questions/*.json`, and the
exception is narrow: it sets each question's `review` field and touches nothing else. Read its
run line. It prints how many questions resolved to a lecture and by which route, and
`--report` lists the ones that did not - a new week's questions showing up under `ambiguous`
means the `#### group` heading or the `Tests [[...]]` line did not resolve, which is a vault fix,
not a tool fix. Run `--validate` after any change to the matcher.

⚠ **It re-derives every course, not just the questions you added.** On 2026-10-03 one run moved
the `review` field on ~1,600 existing questions across FoM, PoM 1 and all five PoM 2 blocks -
drift nobody asked for, in a commit about one week. **Diff the banks after it runs**: if fields
other than your new questions' `review` moved, keep the values for your new qids, `git checkout`
the banks, re-apply your export and write just those values back. Raise the drift with her
separately rather than shipping it under a week's commit. A question carrying a `refiled` record
keeps its review through a derive (route 0), so this rule is about the questions nobody has read,
not about the refiled ones.

**The Off-curriculum set rides through the rebuild unchanged.** `rosters_from_vault.py` takes its
week headings from the questions JSON, and a moved question carries a bare `Week N` label, so it
now prefers a week's fuller heading and uses a bare one only when no question in that week has
anything better. `review_lectures.py` sets `review` on an Off-curriculum question exactly as on
any other, and the drift rule above applies to it unchanged.

**For a weekly quiz or any set spanning several lectures, give each question its own
`Tests [[NN - Lecture]]`** in its `lectureMeta`, not one list for the whole set. Route 2 takes
every wikilink in `lectureMeta`, so a set-level list sends every question to every lecture. The
endo Week 1 quiz did exactly that and its questions each review seven lectures.

**This updates the portal, it does not rebuild the repo.** Worth knowing exactly what each script
touches, because the question bank is the irreplaceable part:

- **Only `review_lectures.py` writes `data/questions/*.json`, and only its `review` field.**
  The others read the bank and never write it, so the hand-authored stems, options, keys and
  answer callouts cannot be clobbered by a rebuild.
- `data/notes/*.json` is regenerated from the vault, which is the point - the vault is the source
  of truth for notes and charts.
- The block pages and `index.html` are **overwritten wholesale**, but `existing()` in
  `build_pages.py` reads the blurb, the meta description and the accent trio back out of the page
  it is replacing and writes them into the new one, so per-block identity survives.
- **Anything else hand-edited directly into the HTML is lost on the next rebuild.** That is why
  prose gets edited in the templates inside `build_pages.py` and `build_index.py`, not in the
  pages. It is not a style preference, it is the only place an edit survives.

Re-run the last three after editing any of `base.css`, `portal.css`, `portal.js`, `quiz.js` or
`notes.js` (all at the repo root), because the asset cache-busting hash is read off the file at build time. The per-block
blurb and the accent trio are the two things read back out of the HTML and preserved.

**Any prose written for the portal keeps her voice and uses no em dashes.** Edit her existing
sentences and add to them, do not rewrite the passage in another register.

Commit at the end of this stage. Do not push unless asked.

## Stage 6 - Anki

Invoke **`med-anki`**.

**This is a delta, not a deck build.** The CLim endo deck already holds the breadth, so the job
is what changed: content the updated vault note has that CLim is **missing**, and content CLim
has that the note now **contradicts**. You are not starting from scratch and you are not choosing
a deck size.

- **There is no card-count target.** Some weeks the delta is three cards; after a substantially
  rewritten lecture it is forty. A number invites padding.
- **Outdated cannot be detected, only read.** CLim's cards carry no provenance, exactly as the
  lecture notes do not, so pull the lecture's cards out of CLim with `findNotes` / `notesInfo`
  and compare them against the note. There is no timestamp shortcut.
- **The chart sets priority, not scope.** The note is the source. Where the chart bolded
  something, that gap goes first and earns `#HighYield`.
- **Give every card that needs one an established mnemonic.** This applies to cards you add and
  to the CLim cards you touch. The user asked for the hooks med students already share (classic
  acronyms, drug-name stems, Sketchy-style images, number patterns) ahead of invented ones.
  `med-anki`'s "Established mnemonics come first" states the order, the `(classic)` label and
  what to do when a classic disagrees with the lecture. On a CLim note, **append** the hook to her
  `Extra` with `updateNoteFields` and never overwrite what she wrote there. List the mnemonics
  added in the Stage 7 report so she can veto one.

High yield means facts that drive a clinical decision. Keep a number when it changes a decision,
drop it when it is a property of the molecule. The deck naming, the tag handling and the
AnkiConnect mechanics are `med-anki`'s to state, and it now does.

### Figures on a chart

A chart may carry **one figure**, embedded in its chart region and written by `med-chart`
(see its "Where the user's charts deliberately differ"). `figures.py` resolves it against the
vault's `Attachments`, re-compresses it into `assets/figures/<hash>.jpg` and writes the
`data/figures.json` manifest; `charts_from_vault.py` only reads that manifest.

- **It runs between the roster and the charts**, and it is skippable in a week whose charts
  embed nothing.
- **A picture it cannot find is named on stderr and the block is dropped**, so the chart still
  ships. Check its summary line - `N in manifest, N new, N missing` - before Stage 5. Missing is
  the number that matters; the chart reads fine without the figure, which is how a dropped one
  hides.
- **Report the figure count in Stage 7**, for the same reason the question pictures are reported.
- ⚠ **Never generate a figure.** It has to already be in the vault. A diagram with a garbled
  label or an invented structure is worse than none, because it gets studied and then believed.

## Stage 7 - report

- Lecture notes written or updated from slides, questions banked per source with their qid
  ranges, lectures charted, cards added and corrected per lecture.
- **Any lecture whose note could not be brought up to date**, named, with what was missing. This
  is the one that quietly poisons everything downstream, so it goes near the top of the report.
- The recounted question total, per block and overall, with the time it was taken.
- **How many pictures were embedded**, and any question whose picture is missing because it is
  cadaveric or unresolved. A dropped picture is invisible otherwise.
- Everything skipped and why: decks not on disk, modules with no questions, and which of the
  **Stage 8** sources have not arrived. **Report a pending quiz, DSSG or CBL as a normal open
  item, not as an incomplete week.**
- Any source errors flagged rather than silently corrected.
- **Questions moved to Off-curriculum this run, per reason** (outdated, not-covered, retired), with their
  qids, and any `KEY?` items written to `build/curriculum_audit/KEY_ISSUES.md`.

## Stage 8 - the late arrivals (the bonus stage)

Three sources do not run on her schedule: the **weekly quiz**, the **DSSG cases** and the
**in-class CBL cases**. Everything in Stages 1 through 7 is available as soon as the lecture is;
these three are released, or held, by the course. So they are grouped here, after the report, and
they are **optional by construction**:

- **A week with none of them is a complete week.** Finish Stages 1 through 7 and report these as
  pending, never the week as unfinished.
- **Absent is expected, not merely normal.** The quiz opens at the **end** of the week, so for
  the first four days there is no judgement to make: not there is the correct state and says
  nothing about whether she is behind.
- **Never wait, and never chase.** Do not ask whether she has sat the quiz or been to the DSSG,
  and do not tell her to go.
- **Never hold Stages 1 through 7 for any of them.**

### All three land as MCQs

They arrive as prose, a discussion or a select-all, and the bank takes none of those. Each becomes
a **single-best-answer MCQ** in `kind: mcq` form, which is what all 71 case-derived endo questions
already are.

| Source | Destination | Fields | The rewrite |
| --- | --- | --- | --- |
| Weekly Elentra quiz | `Weekly Quizzes - <topic>.md` | the note's `weekly` family | mostly select-all, which the house rule forbids in a banked question, so each becomes a **combinations MCQ** |
| DSSG cases | `New Questions - <topic>.md` | `family: "meds2029"`, `source: "dssg"` | a discussed case becomes a stem with options, keyed to the group's reasoning |
| In-class CBL cases | `New Questions - <topic>.md` | `family: "meds2029"`, `source: "new"` | the same, from the case as it was worked in class |

**Writing the options is where both Stage 2 rules bind hardest** - *Every option has to look
like the answer* and *Nothing enters a question that the material did not put there*. A source
that arrives as prose has no options at all, so every one is written from scratch, and the key
is the one you understand best: that is how it ends up longest, most qualified, and first.

**Start from `tools/elentra_quiz.py <capture>.json --topic <slug> --week N --note "<Weekly Quizzes note>"`**,
which writes a house-format fragment into `build/`. The capture file accumulates every quiz
ever grabbed (the 2026-10-04 one still held Week 1 endo), so take only the capture whose title
is this week's. **The key is the `Correct Answer:` line in the feedback, not the `correct` field**,
which lists every option on a radio question.

**The rewrite is the work, not the extraction.** Capturing the quiz is one bookmarklet click;
turning ten select-alls into defensible combinations MCQs is the slow part, and a case discussed
for forty minutes has to be cut down to one decision worth asking about.

**Where the reasoning is yours, say so.** Elentra usually writes `Rationale: N/A`, and a DSSG or
CBL case is keyed by the discussion rather than by an answer letter. Write the reasoning and
**label it as yours** rather than passing it off as transcribed. Where the discussion genuinely
does not settle a single answer, ship it **`keyed: false`** rather than inventing a letter - three
module cases already do exactly this, and the portal states it on the question's face.

**The weekly quizzes carry no images**, so nothing in the picture rule applies to them.

#### A matching activity becomes a numbered-against-lettered MCQ

A matching activity has no single best answer and the bank cannot score it, so it converts to one
MCQ over the whole set rather than shipping `kind: "matching"` and `free: true`, which scores
nothing and reads as a gap.

- **Number the left column 1, 2, 3 and letter the right column A, B, C**, as a two-column table
  in the stem.
- ⚠ **Shuffle the lettered column.** Left in source order the two columns line up row by row and
  the question answers itself.
- **Each option is the whole set of pairings**, `1-F · 2-B · 3-E · …`, so the options are
  identical in length by construction and the Stage 2 parity rule is satisfied for free.
- **Distractors swap two or three pairs, never one.** A single swap is spotted by scanning one
  row; the swaps should be **the pairs that are genuinely confusable** - the two that both come
  from the same primordium, the two that both end as labia.
- Ship it `kind: "mcq"`, `free: false`, keyed to a letter.

`module-endo-Q156` is the worked example: nine primordial structures against nine terminal ones,
four options, the key spread away from the letters its neighbours use.

**Writing the options is where both Stage 2 rules bind hardest** - *Every option has to look
like the answer* and *Nothing enters a question that the material did not put there*. A source
that arrives as prose has no options at all, so every one is written from scratch, and the key
is the one you understand best: that is how it ends up longest, most qualified, and first.

**Start from `tools/elentra_quiz.py <capture>.json --topic <slug> --week N --note "<Weekly Quizzes note>"`**,
which writes a house-format fragment into `build/`. The capture file accumulates every quiz
ever grabbed (the 2026-10-04 one still held Week 1 endo), so take only the capture whose title
is this week's. **The key is the `Correct Answer:` line in the feedback, not the `correct` field**,
which lists every option on a radio question.

**The rewrite is the work, not the extraction.** Capturing the quiz is one bookmarklet click;
turning ten select-alls into defensible combinations MCQs is the slow part, and a case discussed
for forty minutes has to be cut down to one decision worth asking about.

**Where the reasoning is yours, say so.** Elentra usually writes `Rationale: N/A`, and a DSSG or
CBL case is keyed by the discussion rather than by an answer letter. Write the reasoning and
**label it as yours** rather than passing it off as transcribed. Where the discussion genuinely
does not settle a single answer, ship it **`keyed: false`** rather than inventing a letter - three
module cases already do exactly this, and the portal states it on the question's face.

**The weekly quizzes carry no images**, so nothing in the picture rule applies to them.

### Re-entering for one late arrival

**Do not re-run the week.** Take the short path:

| | |
| --- | --- |
| Stage 8 | bank it into its own note, numbering continuing from that note |
| Stage 4 | add those questions to `pom2/data/questions/<slug>.json` |
| Stage 5 | rebuild the portal so the counts move |
| Stage 7 | report what it added, and what is still pending |

**Stages 1, 2, 3 and 6 do not re-run**: the notes, the module and deck questions, the charts and
the cards do not change because a quiz or a case session happened. **This holds even though
Stage 3 reads the questions** - a chart is not rewritten for a late arrival. The one exception is
a late question that **contradicts the lecture note**, which is a Stage 1 conflict and follows the
OneNote precedence rule, not a banking decision.

## Gates - stop and confirm

- **A cadaveric image she has not approved.** Flag, propose, and wait. Never ship one and never
  substitute one.
- **Deleting the CLim source deck.** Import, verify, then ask. Do not delete it for her, and run
  no Check Media purge before the import: 333 of the endo notes carry images that the deck owns.
- **Posting charts to OneNote.** Her notebook is the year's lecture record - propose the page
  and wait for an explicit yes before creating or updating one, every time. Reading is local and
  needs nothing; **writing still has no local route**, so posting means the ms365 MCP server,
  which is refused with `AADSTS50158` until she completes an interactive sign-in. So today the
  honest answer to a posting request is that it needs her login first - ask before starting one.
  Two traps if that server is ever re-added: spawn it from the installed binary
  (`~/.npm-global/bin/ms-365-mcp-server`), **not** `npx -y`, which re-resolves the registry on
  every launch and blows the MCP startup window; and `--verify-login` returns
  `Graph API access failed: 403` even when it works, because it probes `/v1.0/me` for a
  `User.Read` the onenote preset does not request - test a real OneNote call instead.
- **Pushing to GitHub.** Committing is part of Stage 5, pushing is not.
- **Publishing any Artifact at all.** A week's work ships through the repo. If publishing one
  looks like the right answer, ask first, because it usually means the repo path was missed.

## Concurrency

Other sessions of hers work this vault **and this repo** at the same time, split by topic. A file
listing taken at the start of a stage is not trustworthy at the end.

- **Re-validate every wikilink as the last step of any vault stage**, and re-read a question note
  before appending to it rather than trusting an earlier read of its highest `# N`.
- **Re-check `git status` before the Stage 5 commit**, for the same reason. The repo drifts under
  you exactly as the vault does, and a commit is harder to unpick than an appended note.
