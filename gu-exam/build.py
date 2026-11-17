"""
Purpose: Build the male genital and rectal clinical skills page (gu-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Male Genital and Rectal Exam Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json
Output: gu-exam/index.html

The note is the single source of the steps and positive findings: edit the note, then rerun this
script. Which problem heading each manoeuvre sits under, and its picture, are set here. How the
page looks lives in clinical-skills/exam_page.py, shared by every exam page. Every picture is a
drawn schematic: this is an intimate exam, so no photographs of bodies are used.
"""

import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("exam_page", HERE.parent / "clinical-skills/exam_page.py")
exam_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exam_page)
VAULT = Path(os.environ.get("POM2_VAULT", "/mnt/c/Users/nsims/medwiki"))
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Male Genital and Rectal Exam Clinical Skills.md"

# section number in the note -> region on the page
REGIONS = {
    3: ("penis", "Penis", "T2C · Genitourinary", "#3d6fb6"),
    4: ("scrotum", "Scrotum and testes", "T2C · Genitourinary", "#7a3fb0"),
    5: ("hernia", "Inguinal region and hernia check", "T2C · Genitourinary", "#23798a"),
    6: ("rectal", "Anus, rectum and prostate", "T2C · Genitourinary", "#b4501f"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "The general approach"), (2, "Normal anatomy")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Penis: inspection": ("Penis", "penis-inspection.jpg"),
    "Penis: palpation": ("Penis", "penis-palpation.jpg"),
    "Scrotum: inspection": ("Swelling, lumps or pain in the scrotum", "scrotum-inspection.jpg"),
    "Testis palpation": ("Swelling, lumps or pain in the scrotum", "testis-palpation.jpg"),
    "Epididymis palpation": ("Swelling, lumps or pain in the scrotum", "epididymis-palpation.jpg"),
    "Spermatic cord and vas deferens": ("Swelling, lumps or pain in the scrotum", "spermatic-cord-and-vas-deferens.jpg"),
    "Transillumination": ("Swelling, lumps or pain in the scrotum", "transillumination.jpg"),
    "Cremasteric reflex": ("Swelling, lumps or pain in the scrotum", "cremasteric-reflex.jpg"),
    "Groin inspection with Valsalva": ("A bulge in the groin (hernia)", "groin-inspection-with-valsalva.jpg"),
    "Inguinal canal palpation": ("A bulge in the groin (hernia)", "inguinal-canal-palpation.jpg"),
    "Inguinal lymph nodes": ("A bulge in the groin (hernia)", "inguinal-lymph-nodes.jpg"),
    "Anus: inspection": ("Anus and rectum", "anus-inspection.jpg"),
    "Digital rectal exam (DRE)": ("Anus and rectum", "digital-rectal-exam-dre.jpg"),
    "Prostate palpation": ("Prostate", None),
    "Withdrawing and the glove": ("Anus and rectum", "withdrawing-and-the-glove.jpg"),
}

EXAM = exam_page.Exam(
    key="gu", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS,
    opening={
        "penis": "I'll explain each step before I do it. Let me know if anything is uncomfortable, and you can ask me to stop at any time.",
        "scrotum": "I'm going to look at and gently feel each testicle. Tell me straight away if anything hurts.",
        "hernia": "I'm going to check for a hernia. I'll ask you to cough or bear down while I feel the groin.",
        "rectal": "I'm going to place a gloved, lubricated finger in your rectum. It may feel like you need a bowel movement; tell me if you want me to stop.",
    },
    h1="Male genital and rectal exam",
    lead='Penis, scrotum and testes, groin and hernias, then the rectal exam.',
    find="Find a step or a finding (e.g. hernia, prostate)",
    root="Consent → Penis → Scrotum and testes → Groin and hernia → Anus, rectum and prostate → Explain",
    root_note="Look, then feel, comparing left with right. Say what you are about to do before you do it, "
              "and stop at once if the patient asks.",
    video_credit="No videos for this exam: none were found in the course library, and none could be verified elsewhere.",
    general_title="General approach", general_week="Every GU and rectal exam",
    spine_heading="Look and feel", spine_title="Before the steps", pearls_heading="Pearls", count_noun="steps",
)


if __name__ == "__main__":
    exam_page.build(EXAM)
