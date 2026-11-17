"""
Purpose: Build the vital signs and general inspection clinical skills page (vitals-exam/index.html)
         from the medwiki note "Summary Notes - Vital Signs Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (Health Education Media Library clips); videos.json (Geeky Medics)
Output: vitals-exam/index.html

The note is the single source of the steps and positive findings: edit the note, then rerun this
script. Problem headings and pictures are set here; how the page looks lives in
clinical-skills/exam_page.py, shared by every exam page.
"""

import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("exam_page", HERE.parent / "clinical-skills/exam_page.py")
exam_page = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exam_page)
VAULT = Path(os.environ.get("POM2_VAULT", "/mnt/c/Users/nsims/medwiki"))
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Vital Signs Clinical Skills.md"

WEEK = "PPES 1 · Week 1"
REGIONS = {
    2: ("inspection", "General inspection", WEEK, "#3d6fb6"),
    3: ("pulse", "Pulse", WEEK, "#b4501f"),
    4: ("resp", "Respiratory rate", WEEK, "#23798a"),
    5: ("bp", "Blood pressure", WEEK, "#7a3fb0"),
    6: ("temp", "Temperature and SpO2", WEEK, "#7d6413"),
    7: ("normals", "Normal values", WEEK, "#2f6b4f"),
}
GENERAL = [(1, "The general approach")]

TESTS = {
    "Central cyanosis": ("Colour of the skin", "central-cyanosis.jpg"),
    "Peripheral cyanosis": ("Colour of the skin", "peripheral-cyanosis.jpg"),
    "Pallor": ("Colour of the skin", "pallor.jpg"),
    "Plethora": ("Colour of the skin", None),
    "Jaundice": ("Colour of the skin", "jaundice.jpg"),
    "Radial pulse": ("Rate, rhythm, amplitude, contour", "radial-pulse.jpg"),
    "Counting the respiratory rate": ("Rate and distress", "counting-respiratory-rate.jpg"),
    "Palpated systolic estimate": ("Before the reading", "palpated-systolic-estimate.jpg"),
    "Auscultated blood pressure": ("The reading", "auscultated-bp.jpg"),
    "Orthostatic blood pressure": ("Lying to standing", "orthostatic-bp.jpg"),
}

OPENING = {
    "pulse": "Hello, I'm ___, a medical student. Can I check your name against your wristband? I'd like to check your vital signs, "
             "which means feeling your pulse and taking your blood pressure in both arms. Is that alright?",
}

EXAM = exam_page.Exam(
    key="vitals", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening=OPENING,
    h1="Vital signs exam",
    lead='Look at the patient, then pulse, breathing and blood pressure.',
    find="Find a sign or a vital (e.g. jaundice, orthostatic)",
    root="General inspection → Pulse → Respiratory rate → Blood pressure → (Temperature, SpO2)",
    root_note="The survey starts the moment you meet the patient. Anything paired is checked on both sides and compared.",
    video_credit='Intro and set-up clips from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries), CC BY-NC 4.0, played from the library's own server. The vital signs walkthrough is by "
                 '<a href="https://www.youtube.com/@geekymedics">Geeky Medics</a>. Each opens only when you tap it.',
    other_video={"Plethora": {"id": "yPx7aMEgAR0", "start": 0, "title": "Plethora face: causes", "channel": "Medicine Handy Points"}},
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    video={}, video_page="https://www.youtube.com/watch?v=llosVAoeojQ "
                 "The plethora clip is a YouTube video (Medicine Handy Points), loaded only when tapped.",
    region_video={"pulse": ["vital-signs"], "bp": ["vital-signs"]},
    general_title="General approach", general_week="Every exam",
    spine_heading="How to do it", spine_title="The routine", pearls_heading="Pearls", count_noun="signs and manoeuvres",
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "The general approach": [
  {
   "id": "FqeLIykKDFw",
   "title": "Vitals demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'


if __name__ == "__main__":
    exam_page.build(EXAM)
