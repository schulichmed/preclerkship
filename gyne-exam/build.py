"""
Purpose: Build the pelvic (gynecological) and obstetrical abdominal clinical skills page
         (gyne-exam/index.html) from the manoeuvre tables in the medwiki note
         "Summary Notes - Pelvic Exam Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; videos.json
       (Geeky Medics); img/ holds Commons pictures and drawings from draw_figures.py
Output: gyne-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each manoeuvre sits under, and its
picture, are set here. How the page looks lives in clinical-skills/exam_page.py,
shared by every exam page. No photographs of bodies: every picture is a drawing,
a diagram or an instrument.
"""

import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("exam_page", HERE.parent / "clinical-skills/exam_page.py")
exam_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exam_page)
VAULT = Path(os.environ.get("POM2_VAULT", "/mnt/c/Users/nsims/medwiki"))
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Pelvic Exam Clinical Skills.md"

# section number in the note -> region on the page
REGIONS = {
    2: ("prep", "Position, drape and look", "T2C · Gynecological Exam", "#3d6fb6"),
    3: ("speculum", "Speculum exam", "T2C · Gynecological Exam", "#a8366f"),
    4: ("bimanual", "Bimanual exam", "T2C · Gynecological Exam", "#7a3fb0"),
    6: ("obstetric", "Obstetrical abdominal exam", "Obstetrics & Gynaecology", "#2f6b4f"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "The general approach"), (5, "Feedback during and after the exam")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Position and drape": ("Before you touch", "position-and-drape.jpg"),
    "Inspect the vulva": ("The outside first", "inspect-the-vulva.jpg"),
    "Speculum insertion": ("Getting a view", "speculum-insertion.jpg"),
    "Viewing the cervix": ("Getting a view", "viewing-the-cervix.jpg"),
    "Speculum removal": ("Getting a view", "speculum-removal.jpg"),
    "Cervical screening sample (HPV test)": ("Samples", "cervical-screening-sample.jpg"),
    "Other swabs": ("Samples", "other-swabs.jpg"),
    "Cervix": ("Pelvic infection or ectopic pregnancy", "bimanual-exam.jpg"),
    "Uterus": ("Enlarged or fixed uterus", "bimanual-exam.jpg"),
    "Adnexa (ovaries and tubes)": ("An ovarian or tubal mass", "bimanual-exam.jpg"),
    "Position and drape (obstetrical)": ("Before you touch", "position-and-drape-obstetrical.jpg"),
    "Symphysis-fundal height (SFH)": ("Is the baby growing?", "symphysis-fundal-height.jpg"),
    "Leopold's 1: fundal grip": ("How is the baby lying?", "leopolds-1-fundal-grip.jpg"),
    "Leopold's 2: lateral grip": ("How is the baby lying?", "leopolds-2-lateral-grip.jpg"),
    "Leopold's 3: pelvic grip (Pawlik's)": ("How is the baby lying?", "leopolds-3-pelvic-grip.jpg"),
    "Leopold's 4: deep pelvic grip": ("How is the baby lying?", "leopolds-4-deep-pelvic-grip.jpg"),
    "Fetal heart rate": ("Is the baby well?", "fetal-heart-rate.jpg"),
}

# Geeky Medics videos (slug = YouTube id), on each region's spine card
SPECULUM_VIDEO, BIMANUAL_VIDEO, OB_VIDEO = "NEVyzP82T1U", "mhA7W-XNDso", "-pkkgBX7OFQ"

EXAM = exam_page.Exam(
    key="gyne", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS,
    opening={
        "prep": "Before we start, I'll explain each step before I do it. You can ask me to pause or stop at any point, and I will.",
        "speculum": "I'm going to place a small instrument called a speculum so I can see your cervix. You'll feel pressure, not pain; tell me if it hurts and I'll stop.",
        "bimanual": "Now I'll place two gloved fingers in the vagina and press gently on your lower tummy with my other hand, to feel your uterus and ovaries.",
        "obstetric": "I'm going to feel your tummy to check how the baby is growing and lying, then listen to the heartbeat. Tell me if anything is uncomfortable.",
    },
    h1="Pelvic exam",
    lead='Position and look, speculum, bimanual, then the obstetrical abdominal exam.',
    find="Find a step or a finding (e.g. cervix, fundal height)",
    root="Consent → Position → Look → Speculum → Bimanual → Explain  |  Pregnant: fundal height → Leopold → heart",
    root_note="Say what you will do before you do it, and the patient can stop at any time. Stop means stop.",
    video_credit='Videos by <a href="https://www.youtube.com/@geekymedics">Geeky Medics</a> (YouTube), loaded only when you tap them; '
                 "they use a UK OSCE format, so follow the steps on this page where they differ.",
    video={}, video_page="https://www.youtube.com/watch?v={slug}",
    region_video={"speculum": [SPECULUM_VIDEO], "bimanual": [BIMANUAL_VIDEO], "obstetric": [OB_VIDEO]},
    general_title="General approach", general_week="Every pelvic exam",
    spine_heading="Before the manoeuvres", spine_title="Steps and landmarks", pearls_heading="Pearls", count_noun="manoeuvres",
)


if __name__ == "__main__":
    exam_page.build(EXAM)
