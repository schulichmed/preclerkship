# -*- coding: utf-8 -*-
"""Find the lecture-note sections this year's slides do not teach.

Purpose: a PoM 2 lecture note is a chart written this year from the slides,
         an Objectives callout, and a body that is often an upper year's notes.
         This tool finds each note's slide deck on disk, reads it with pymupdf,
         splits the body into sections and scores each section by the best
         single slide it contains. A section no slide lands in is `inherited`.
Author:  Noor Sims
Date:    2026-10-06
Input:   the block's lecture notes under ``$MEDWIKI/01 - Lectures/99 - PoM 2``
         (default the author's vault), and decks (.pdf or .pptx) in the
         colon-separated folders of ``$POM2_DECKS`` (default Downloads and
         OneDrive/Documents) plus the note's own week folder
Output:  a table per note on stdout: the deck used, then one line per section
         with heading, word count, score and verdict; ``--json`` writes the
         same under build/. The vault is never written.

    python tools/inherited_sections.py --block repro
    python tools/inherited_sections.py --block endo --note "09 - Introduction to Obesity"
    python tools/inherited_sections.py --block repro --json build/inherited_sections/repro.json

Verdicts: ``slides`` when some slide with at least SLIDE_MIN_TERMS distinct
terms has at least SLIDES_AT of them inside the section; ``inherited`` when no
slide does; ``no-deck`` when no deck was found, it could not be opened, or its
text layer holds fewer than DECK_MIN_TERMS distinct terms (image-only slides).
A thin section (under SECTION_MIN_TERMS distinct terms) takes its parent's
verdict. Sections are the body's top heading level and the next level present
(the neonatal note uses ``#`` and ``####``); deeper headings belong to their
parent. ``![[note]]`` and ``![[note#Heading]]`` transclusions are followed.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("MEDWIKI", "/mnt/c/Users/nsims/medwiki"))
LECTURE_NOTES = VAULT / "01 - Lectures" / "99 - PoM 2"
DECK_DIRS = [Path(p) for p in os.environ.get(
    "POM2_DECKS", "/mnt/c/Users/nsims/Downloads:/mnt/c/Users/nsims/OneDrive/Documents").split(":")]
DECK_SUFFIXES = (".pdf", ".pptx")

# block slug -> (vault folder, course weeks)
BLOCKS = {"endo": ("01 - Endocrinology", (1, 2, 3)), "repro": ("02 - Repro", (4, 5, 6))}

# Calibrated on 09 - Approach to Neonatal Care against the 2025 Cheng deck on
# 2026-10-06: its inherited sections (Neonatal Resuscitation, Newborn
# Transition, Respiratory Problems, Neonatal Sepsis) scored 0.11 to 0.44 and
# its taught sections (Apgar, Full Newborn Assessment, Hypothermia,
# Hypoglycemia, Bilirubin, Global Perspectives) scored 0.65 to 1.00 with this
# tokenizer (numbers kept); Newborn Vital Signs, on neither list, scored 0.17.
# DECK_MIN_TERMS: on the same day the readable decks held 50 (Thyroid Part 2,
# 6 slides) to 1046 distinct terms and the three corrupt ones 0, so 25 sits
# between an image-only deck's title words and the thinnest real deck.
SLIDES_AT = 0.5          # a section is taught when some slide is at least half inside it
SLIDE_MIN_TERMS = 6      # a slide with fewer distinct terms (title-only, image-only) does not count
SECTION_MIN_TERMS = 10   # a section with fewer distinct terms is thin and takes its parent's verdict
DECK_MIN_TERMS = 25      # a deck with fewer distinct terms has no usable text layer

INHERITED_MARK = "> [!warning] Inherited"
OBJECTIVES_MARK = "> [!check]"

STOPWORDS = set("""
the a an and or of to in on for with at by from as is are was were be been being this
that these those it its into than then so if not no yes but also can may might should
would will which who whom whose what when where why how all any each every both few
more most other some such only own same too very just about above after again against
between during before below under over out up down off once here there per via etc vs
have has had does did done do make made used using use get take given give less least
high low higher lower normal common usually often typically include including includes
due based following first second third one two three four five within without while
because however therefore also multi column tip note warning check summary condition
""".split())

TOKEN_RE = re.compile(r"[a-z][a-z0-9]{3,}|\d[\d.,]{2,}")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
EMBED_RE = re.compile(r"!\[\[([^\]]+)\]\]")
IMAGE_RE = re.compile(r"\.(png|jpe?g|gif|svg|webp|canvas|pdf)$", re.I)

# Note stem -> deck filenames (looked up in DECK_DIRS and the note's week
# folder). An entry wins over the loose title match; an empty list says there
# is no deck on disk and stops the matcher guessing. Filled on 2026-10-06 from
# the folder listings and confirmed against each deck's title slide; entries
# also pin notes the title match over-fills (pelvic pain, menopause, antepartum
# hemorrhage, the duplicate "(1)" download).
DECKS: dict[str, list[str]] = {
    "01 - Intro to Diabetes": [],
    "02 - Diagnosis and Management of Type 1 Diabetes": ["Diabetes Pathophysiology T1DM.pdf"],
    "03 - Pharmacology of Insulin": [],
    # the "04 - ..." PDF in OneDrive/Documents is a print of the vault note itself
    "04 - Clinically Useful Endocrine Principles": [],
    "05 - Type 2 Diabetes Mellitus - Diagnosis & Epidemiology": ["Diabetes Pathophysiology T2DM Final.pdf", "Hashmi  T2DMellitus.pdf"],
    "07 - Pharmacology of Glucose-Lowering Drugs": ["UME P2 Endocrine Pharmacology (Pharmacology of T2DM).pdf", "pharmacology_of_t2dm_2026_menti_post_after_.pdf"],
    "10 - Prevention of Complications of Diabetes": ["PreventionofDMComplications Hashmi 2024.pdf"],
    "12 - Prevention of Type 2 Diabetes": ["Diabetes Prevention Slides 2021.pdf"],
    "13 - Antihyperglycemic Drug Choices for T2DM (CBL)": ["antihyperglycemics_2026_students_blank_final_before.pptx"],
    "01 - Thyroid and Parathyroid Gland Physiology": ["Thyroid Part 1 2023.pdf", "Thyroid Part 2 2023.pdf", "Parathyroid Part1 2023.pdf", "Parathyroid Part2 2023.pdf"],
    "03 - Clinical Presentation and Evaluation of Hypothyroidism and Thyrotoxicosis": ["clinical_approach_to_hypothyroidism_and_thyrotoxicosis.pdf", "Morrison_ThyroidDysfunction_slides.pdf"],
    "04 - Clinical Presentation and Evaluation of Hyperparathyroidism and Hypoparathyroidism": ["Hyper Hypo Parathyroidism and Calcemia Slides.pdf"],
    "05 - Pathology of Thyroid Masses": ["Wehrli_ThyroidGlandPathology_slides_nv.pdf", "Clinical Presentation Investigation of Thyroid Masses - Morrison Weir.pdf", "thyroid_nodules_live_sep_2025_p2_post_after_.pdf"],
    "06 - Clinical Presentation and Evaluation of Osteoporosis": ["Osteoporosis clin presentation and invest 2024.pptx", "Osteoporosis treatment 2024.pdf", "Osteoporosis epi and tx gap.pdf"],
    "08 - Embryology & Histology": ["Farias_Embryogenesis_slides.pdf", "Normal Histology of the gyn tract_2020.pdf"],
    "09 - Hypothalamic-Pituitary-Gonadal Axis": ["Watson_HPG_Slides.pdf"],
    "01 - Clinical Presentation and Evaluation of Adrenal Gland Disease": ["Adrenal Insufficiency Van Uum 2024.pdf", "Adrenal Overproduction Adrenaline Incidentaloma VanUum 2024.pdf", "Adrenal Overproduction Cortisol VanUum2024.pdf", "Adrenal Overproduction Intro and Aldosterone Van Uum 2024.pdf"],
    "02 - Clinical Presentation and Evaluation of Pituitary Gland Disease": ["Pituitary Hormone Insufficiency 2024.pdf", "Pituitary Overproduction Cushing 2024.pdf", "Pituitary Overproduction Growth Hormone 2024.pdf", "Pituitary Overproduction Prolactin 2024.pdf"],
    "03 - Physiologic Changes that Lead to Puberty": ["Watson_Puberty_Slides.pdf", "Lovett_Puberty_MenstruationSlides.pdf"],
    "04 - Disorders of Puberty": ["P2_Gallego_AbnormalitiesOfPuberty.pdf"],
    "05 - Disorders of Growth": ["P2_Gallego_NormalGrowthShortStature.pdf"],
    "06 - Anatomy of the Female Pelvis, Perineum, & Sexual Function": ["AnatomyPelvisSlides2021.pdf"],
    "07 - Development of the Female Reproductive System": ["Development of the Female Reproductive Tract PDF Slides.pdf"],
    "08 - Introduction to Transgender Medicine": ["Stein Gender Pathways 2024.pdf", "Transgender Van Uum 2024.pdf"],
    "09 - Disorders of Sexual Differentiation": ["Stein DSD-CAH 2024A.pdf", "Stein DSD-CAH 2024B.pdf"],
    "10 - Polyendocrine Metabolic Ovarian Syndrome (PMOS)": [],
    "03 - Contraception and Drugs Used in Gynecology": ["Contraception 2026.pdf", "Drugs used in gynecology slides.pdf"],
    "08 - Approach to Sexually Transmitted Infections": ["STI2021Slides.pdf"],
    "09 - Early Pregnancy Complications - Spontaneous Abortion and Ectopic": ["P2_Sovran_Spontaenous_Abortion.pdf", "ECTOPIC PREGNANCY Year 2.pdf", "p2_kirby_ectopicpregnancy_slides_post_after_.pptx"],
    "11 - Clinical Approach to Acute Pelvic Pain": ["AcutePelvicPain_2021.pdf"],
    "12 - Clinical Approach to Chronic Pelvic Pain": ["ChronicPelvicPain_2021.pdf"],
    "13 - Approach to Pathology of AUB & Pelvic Pain": ["Weir_AUBPain_slides.pdf"],
    "15 - Abnormal Uterine Bleeding": ["P2_Arntfield_AUB_Slides.pdf"],
    "16 - Genetic Screening for Pregnancy in Canada": ["saleh_prenatalgeneticsscreening_Asynchronous.pdf", "Repro Genetics Noninvasive Slides.pdf", "Repro-invasive testing 2023.pdf"],
    "17 - Early Pregnancy Counselling": [],
    "In-Class - Amenorrhea": [],
    "02 - Dilation and Curettage": [],
    "03 - Clinical Approach to Menopause": ["Menopause MedSchoolLecture.pdf"],
    "04 - Approach to and Pathology of a Pelvic Mass": ["Armstrong_OvarianNeoplasms_slides.pdf"],
    "05 - Post-menopausal Woman Presenting with Bleeding": ["Post-Menopausal Bleeding - Notes.pdf"],
    "09 - Pathology of 1st Trimester Bleeding": ["Pathology of Early Pregnancy_EG_notes.pdf"],
    "11 - Approach to First Trimester Bleeding & Ultrasound": ["P2_Vilos_2021_Ultrasound.pdf"],
    "12 - Hypertension in Pregnancy": ["P2_Schmidt_Hypertensive Disorders in Pregnancy_slides.pdf"],
    "13 - Second Trimester Ultrasound": ["T2 Ultrasound Presentation_2021.pdf"],
    # Schmidt's title slide reads "Pregnancy care in the first trimester": note 15, not note 11
    "15 - Care for Pregnancy in the First Trimester": ["P2_Schmidt_FirstTrimester_slides.pdf", "common_concerns_in_pregnancy_post_before.pdf"],
    "16 - Approach to Sexual Health": ["Sexual Health -KCameron.pdf"],
    "17 - Physiologic Changes in Pregnancy": [],
    "01 - Antepartum Hemorrhage & Abnormal Placentation": ["P2_Schmidt_Antepartum Hemorrhage_slides.pdf"],
    "02 - Approach to the Small Fetus": ["P2_Schmidt_IUGR_slides.pdf"],
    "03 - Approach to Preterm Labour": ["Preterm Birth Slides_Banner.pdf"],
    "04 - Process of Labour and Birth": ["P2Sovran_LabourSlides.pdf"],
    "05 - Abnormal Labour": ["Overview of Abnormal Labour and Birth Module.pdf", "AbnormalLabourOperativeDeliveriesandTOLAC.pdf", "AbnormalLabourPostpartumHemorrhage.pdf", "Induction and Augmentation.pdf"],
    "06 - Hemorrhagic Shock": ["P2_Sovran_HShock.pdf"],
    "08 - Postpartum Care": ["POSTPARTUMCARE LS Y2 V2.pdf"],
}

# words in a title or filename that say nothing about the lecture
TITLE_NOISE = set("""
approach clinical presentation evaluation introduction intro overview slides slide notes
module lecture lectures pdf year p2 ume y2 post before after final draft student students
material part online version revised blank cases case dssg cbl meds
""".split())


@dataclass
class Section:
    """One heading of a note body with the text under it.

    Attributes
    ----------
    level : int
        Heading depth, 1 for ``#``.
    heading : str
        Heading text.
    line : int
        0-based index of the heading line in the whole note.
    text : str
        Own text plus every child's, transclusions resolved.
    words : int
        Whitespace word count of ``text``.
    score : float or None
        Best slide coverage, None when thin or no deck.
    verdict : str
        ``slides``, ``inherited`` or ``no-deck``.
    children : list of Section
        Sections at the next heading level under this one.
    """
    level: int
    heading: str
    line: int
    text: str = ""
    words: int = 0
    score: float | None = None
    verdict: str = ""
    children: list["Section"] = field(default_factory=list)


@dataclass
class NoteParts:
    """A note split into its chart region and its body.

    Attributes
    ----------
    chart : str
        Text between the frontmatter and the first ``---`` after it.
    body : list of str
        Lines after that ``---`` and after the Objectives callout.
    body_start : int
        0-based index in the note of ``body[0]``.
    """
    chart: str
    body: list[str]
    body_start: int


@dataclass
class NoteResult:
    """What the tool found for one note."""
    note: Path
    decks: list[Path]
    deck_label: str
    sections: list[Section]
    skipped: str = ""

    def flat(self) -> list[Section]:
        """Every section, parents before their children, in note order."""
        out = []
        for s in self.sections:
            out.append(s)
            out.extend(s.children)
        return out


def clean_markup(text: str) -> str:
    """Strip HTML, embeds and wikilink brackets so only words remain.

    Parameters
    ----------
    text : str
        Obsidian markdown.

    Returns
    -------
    str
        The same text with ``<tags>`` and ``![[embeds]]`` removed and
        ``[[link|alias]]`` reduced to ``link``.
    """
    text = re.sub(r"<[^>]+>", " ", text)
    text = EMBED_RE.sub(" ", text)
    return re.sub(r"\[\[([^\]|#]*)[^\]]*\]\]", r"\1", text)


def tokens(text: str) -> list[str]:
    """Lower-case content words and numbers of a text, stopwords dropped.

    Parameters
    ----------
    text : str
        Any text; markup is cleaned first.

    Returns
    -------
    list of str
        Words of four or more letters and numbers of three or more
        characters, in order, minus STOPWORDS.
    """
    return [t for t in TOKEN_RE.findall(clean_markup(text).lower()) if t not in STOPWORDS]


def terms(text: str) -> set[str]:
    """The distinct tokens of a text."""
    return set(tokens(text))


def split_note(text: str) -> NoteParts:
    """Separate a lecture note into chart region and body.

    Parameters
    ----------
    text : str
        The whole note.

    Returns
    -------
    NoteParts
        ``body`` is empty when the note has no ``---`` after its frontmatter,
        i.e. it is chart only, or when its frontmatter is never closed.
    """
    lines = text.split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        close = next((k for k in range(1, len(lines)) if lines[k].strip() == "---"), None)
        # an unclosed frontmatter block runs to the end: there is no body
        i = close + 1 if close is not None else len(lines)
    end = next((k for k in range(i, len(lines)) if lines[k].strip() == "---"), None)
    if end is None:
        return NoteParts("\n".join(lines[i:]), [], len(lines))
    chart = "\n".join(lines[i:end])
    start = end + 1
    k = start
    while k < len(lines) and not lines[k].startswith(OBJECTIVES_MARK) and lines[k].strip() == "":
        k += 1
    if k < len(lines) and lines[k].startswith(OBJECTIVES_MARK):
        k += 1
        while k < len(lines) and lines[k].startswith(">"):
            k += 1
        start = k
    return NoteParts(chart, lines[start:], start)


def embed_index() -> dict[str, Path]:
    """Every ``.md`` note in the vault by lower-cased stem, for transclusions.

    Returns
    -------
    dict
        stem -> path; the first path seen wins for a duplicated stem.
    """
    index: dict[str, Path] = {}
    for p in VAULT.rglob("*.md"):
        index.setdefault(p.stem.lower(), p)
    return index


def embed_text(name: str, index: dict[str, Path]) -> str:
    """The text an ``![[...]]`` embed pulls in.

    Parameters
    ----------
    name : str
        The embed target, e.g. ``"neonatal sepsis"``,
        ``"hypothyroidism#Clinical Features"`` or ``"figure.png|caption"``.
    index : dict
        From ``embed_index``.

    Returns
    -------
    str
        The target note, or just the named heading's section of it, or an
        empty string for a picture, a canvas or a note not in the vault.
    """
    name = name.split("|", 1)[0].strip()
    heading = None
    if "#" in name:
        name, heading = name.split("#", 1)
    if IMAGE_RE.search(name):
        return ""
    p = index.get(name.strip().lower())
    if p is None:
        return ""
    text = p.read_text(encoding="utf-8", errors="replace")
    if heading:
        m = re.search(r"^#+\s*" + re.escape(heading.strip()) + r"\s*$(.*?)(?=^#|\Z)",
                      text, re.M | re.S)
        return m.group(1) if m else ""
    return text


def sections(body: list[str], body_start: int, embed: Callable[[str], str]) -> list[Section]:
    """Split a note body at its top heading level and the next level present.

    Parameters
    ----------
    body : list of str
        Body lines from ``split_note``.
    body_start : int
        Index of ``body[0]`` in the note, so each section knows its line.
    embed : callable
        Resolves an embed target to text.

    Returns
    -------
    list of Section
        Top-level sections with their children; each section's ``text``
        includes its children's and every transclusion's text. A body with
        no heading at all is one section called ``(body)`` at line
        ``body_start``.
    """
    levels = sorted({len(m.group(1)) for ln in body if (m := HEADING_RE.match(ln))})
    if not levels:
        text = "\n".join(body)
        if not text.strip():
            return []
        s = Section(0, "(body)", body_start, _with_embeds(text, embed))
        s.words = len(s.text.split())
        return [s]
    top, child = levels[0], (levels[1] if len(levels) > 1 else None)
    out: list[Section] = []
    own: dict[int, list[str]] = {}
    cur_top = cur_child = None
    for k, ln in enumerate(body):
        m = HEADING_RE.match(ln)
        level = len(m.group(1)) if m else None
        if level == top:
            cur_top = Section(top, m.group(2), body_start + k)
            cur_child = None
            out.append(cur_top)
            own[id(cur_top)] = []
        elif child is not None and level == child and cur_top is not None:
            cur_child = Section(child, m.group(2), body_start + k)
            cur_top.children.append(cur_child)
            own[id(cur_child)] = []
        else:
            target = cur_child if cur_child is not None else cur_top
            if target is not None:
                own[id(target)].append(ln)
    for s in out:
        for c in s.children:
            c.text = _with_embeds("\n".join(own[id(c)]), embed)
            c.words = len(c.text.split())
        s.text = "\n".join([_with_embeds("\n".join(own[id(s)]), embed)] + [c.text for c in s.children])
        s.words = len(s.text.split())
    return out


def _with_embeds(text: str, embed: Callable[[str], str]) -> str:
    """Append the text of every embed in ``text`` to it."""
    extra = [embed(name) for name in EMBED_RE.findall(text)]
    return "\n".join([text] + [e for e in extra if e])


def deck_pages(path: Path) -> list[str]:
    """The text of each slide of a deck.

    Parameters
    ----------
    path : Path
        A ``.pdf`` or ``.pptx``; pymupdf opens both.

    Returns
    -------
    list of str
        One string per page, empty for an image-only page.

    Raises
    ------
    RuntimeError
        When pymupdf cannot open the file.
    """
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)   # a damaged stream is reported once, as no usable text
    try:
        doc = pymupdf.open(path)
    except Exception as exc:  # pymupdf raises its own hierarchy
        raise RuntimeError(f"cannot open {path.name}: {exc}") from exc
    return [page.get_text() for page in doc]


def deck_files() -> list[Path]:
    """Every deck in DECK_DIRS.

    Returns
    -------
    list of Path
        ``.pdf`` and ``.pptx`` files, folders that do not exist skipped.
    """
    out = []
    for d in DECK_DIRS:
        if d.is_dir():
            out.extend(p for p in d.iterdir() if p.suffix.lower() in DECK_SUFFIXES)
    return out


def title_words(stem: str) -> set[str]:
    """The distinctive words of a note or deck title, stemmed to six letters.

    Parameters
    ----------
    stem : str
        A filename without suffix.

    Returns
    -------
    set of str
        Lower-case words of four or more letters, split on punctuation and
        camel case, minus STOPWORDS and TITLE_NOISE, each cut to six letters
        so ``hypertension`` meets ``hypertensive``.
    """
    stem = re.sub(r"^[\d.]+\s*-\s*", "", stem)
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    words = re.findall(r"[a-z]+", stem.lower())
    return {w[:6] for w in words if len(w) >= 4 and w not in STOPWORDS and w not in TITLE_NOISE}


def decks_for(note: Path, files: list[Path]) -> list[Path]:
    """The deck files that belong to a note.

    Parameters
    ----------
    note : Path
        The lecture note.
    files : list of Path
        From ``deck_files``. The note's own week folder is searched as well.

    Returns
    -------
    list of Path
        The DECKS entry when there is one (names resolved against ``files``
        and the week folder; an empty entry gives an empty list). Otherwise
        every file whose squashed name contains at least half of the note's
        title words and at least two of them (one when the title has only
        one), best score first.
    """
    local = [p for p in note.parent.iterdir() if p.suffix.lower() in DECK_SUFFIXES]
    pool = local + files
    if note.stem in DECKS:
        by_name = {p.name: p for p in pool}
        return [by_name[n] for n in DECKS[note.stem] if n in by_name]
    want = title_words(note.stem)
    if not want:
        return []
    need = min(2, len(want))
    scored = []
    for p in pool:
        squashed = re.sub(r"[^a-z0-9]", "", p.stem.lower())
        hit = sum(1 for w in want if w in squashed)
        if hit >= need and hit / len(want) >= 0.5:
            scored.append((hit / len(want), hit, p))
    scored.sort(key=lambda t: (-t[0], -t[1], t[2].name))
    return [p for _s, _h, p in scored]


def slide_coverage(section_terms: set[str], slides: list[set[str]]) -> float:
    """How much of the best-matching slide a section contains.

    Parameters
    ----------
    section_terms : set of str
        The section's distinct terms.
    slides : list of set of str
        Each slide's distinct terms; slides under SLIDE_MIN_TERMS are ignored.

    Returns
    -------
    float
        The largest fraction of one slide's terms found in the section.
    """
    best = 0.0
    for s in slides:
        if len(s) < SLIDE_MIN_TERMS:
            continue
        best = max(best, len(s & section_terms) / len(s))
    return best


def judge(secs: list[Section], slides: list[set[str]] | None) -> None:
    """Set score and verdict on every section and child.

    Parameters
    ----------
    secs : list of Section
        From ``sections``.
    slides : list of set of str or None
        Per-slide terms, or None when the note has no usable deck.
    """
    for s in secs:
        for item, parent in [(s, None)] + [(c, s) for c in s.children]:
            if slides is None:
                item.verdict = "no-deck"
                continue
            own = terms(item.text)
            if len(own) < SECTION_MIN_TERMS and parent is not None:
                item.score, item.verdict = None, parent.verdict
                continue
            item.score = slide_coverage(own, slides)
            item.verdict = "slides" if item.score >= SLIDES_AT else "inherited"


def audit_note(note: Path, files: list[Path], index: dict[str, Path]) -> NoteResult:
    """Find a note's deck and score its sections.

    Parameters
    ----------
    note : Path
        The lecture note.
    files : list of Path
        From ``deck_files``.
    index : dict
        From ``embed_index``.

    Returns
    -------
    NoteResult
        ``skipped`` is ``"no body"`` for a chart-only note. ``deck_label`` is
        the deck filenames joined with ``", "``, or ``"no deck found"``, or
        the filenames followed by ``" (no usable text)"`` or
        ``" (unreadable: ...)"``.
    """
    parts = split_note(note.read_text(encoding="utf-8", errors="replace"))
    secs = sections(parts.body, parts.body_start, lambda n: embed_text(n, index))
    decks = decks_for(note, files)
    if not secs:
        return NoteResult(note, decks, ", ".join(p.name for p in decks) or "no deck found", [], "no body")
    if not decks:
        judge(secs, None)
        return NoteResult(note, [], "no deck found", secs)
    label = ", ".join(p.name for p in decks)
    try:
        pages = [page for p in decks for page in deck_pages(p)]
    except RuntimeError as exc:
        judge(secs, None)
        return NoteResult(note, decks, f"{label} (unreadable: {exc})", secs)
    slides = [terms(page) for page in pages]
    usable = len(set().union(*slides)) if slides else 0
    if usable < DECK_MIN_TERMS:
        judge(secs, None)
        return NoteResult(note, decks, f"{label} (no usable text)", secs)
    judge(secs, slides)
    return NoteResult(note, decks, label, secs)


def lecture_notes(block: str) -> list[Path]:
    """The block's lecture notes in week and number order.

    Parameters
    ----------
    block : str
        ``"endo"`` or ``"repro"``.

    Returns
    -------
    list of Path
        Every ``.md`` under the block's week folders except ``Week N.md``.
    """
    folder, weeks = BLOCKS[block]
    out = []
    for w in weeks:
        d = LECTURE_NOTES / folder / f"Week {w}"
        if d.is_dir():
            out.extend(sorted(p for p in d.glob("*.md") if p.stem != f"Week {w}"))
    return out


def print_table(result: NoteResult) -> None:
    """Print one note's table."""
    print(f"== {result.note.stem}  [{result.note.parent.parent.name} / {result.note.parent.name}]")
    print(f"   deck: {result.deck_label}")
    if result.skipped:
        print(f"   {result.skipped}")
        return
    print(f"   {'section':60s} {'words':>5s} {'score':>5s}  verdict")
    for s in result.flat():
        name = ("#" * s.level + " " if s.level else "") + s.heading
        score = "-" if s.score is None else f"{s.score:.2f}"
        print(f"   {name[:60]:60s} {s.words:5d} {score:>5s}  {s.verdict}")


def write_json(results: list[NoteResult], out: Path) -> None:
    """Write the results as JSON under build/.

    Parameters
    ----------
    results : list of NoteResult
    out : Path
        Destination; its parent is created. Refuses a path inside the vault.
    """
    if VAULT in out.resolve().parents:
        raise SystemExit("refusing to write inside the vault")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = []
    for r in results:
        data.append({
            "note": r.note.stem, "week": r.note.parent.name, "decks": [p.name for p in r.decks],
            "deck_label": r.deck_label, "skipped": r.skipped,
            "sections": [{"level": s.level, "heading": s.heading, "line": s.line, "words": s.words,
                          "score": s.score, "verdict": s.verdict,
                          "parent": None if s in r.sections else next(
                              t.heading for t in r.sections if s in t.children)}
                         for s in r.flat()]})
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    """Parse the command line and print a table per note."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--block", required=True, choices=sorted(BLOCKS))
    ap.add_argument("--note", help="only the note with this stem, e.g. '09 - Approach to Neonatal Care'")
    ap.add_argument("--json", type=Path, help="also write the results here (under build/)")
    args = ap.parse_args()
    files = deck_files()
    index = embed_index()
    results = []
    for note in lecture_notes(args.block):
        if args.note and note.stem != args.note:
            continue
        r = audit_note(note, files, index)
        print_table(r)
        results.append(r)
    inherited = sum(1 for r in results for s in r.flat() if s.verdict == "inherited")
    nodeck = [r.note.stem for r in results if r.deck_label.startswith("no deck") or "(no usable" in r.deck_label or "(unreadable" in r.deck_label]
    print(f"\n{len(results)} notes, {inherited} inherited sections, {len(nodeck)} without a usable deck")
    for stem in nodeck:
        print(f"   no deck: {stem}", file=sys.stderr)
    if args.json:
        write_json(results, args.json)


if __name__ == "__main__":
    main()
