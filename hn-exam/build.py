"""
Purpose: Build the head and neck, eye and ear clinical skills page (hn-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Head and Neck Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (Health Education Media Library video files, by test or region)
Output: hn-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each manoeuvre sits under, its picture and
its videos are set here. How the page looks lives in clinical-skills/exam_page.py,
shared by every exam page.
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
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Head and Neck Clinical Skills.md"

WEEK7 = "PPES 2 · Week 7"

# section number in the note -> region on the page
REGIONS = {
    2: ("eye", "Eye", WEEK7, "#3d6fb6"),
    3: ("ophth", "Full eye and vision exam", "T2C · Ophthalmology", "#4d5590"),
    4: ("ear", "Ear", WEEK7, "#23798a"),
    5: ("nose", "Nose", WEEK7, "#7a3fb0"),
    6: ("mouth", "Mouth and throat", WEEK7, "#a8366f"),
    7: ("face", "Face and head", WEEK7, "#b4501f"),
    8: ("neck", "Neck", WEEK7, "#2f6b4f"),
}

# the note's opening section, shown as the first band
GENERAL = [(1, "The general approach")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Inspect the eyes and eyelids": ("Look first", "inspect-the-eyes-and-eyelids.jpg"),
    "Pupils and light reflex": ("Pupils and movement (II, III, IV, VI)", "pupils-and-light-reflex.jpg"),
    "Eye movements": ("Pupils and movement (II, III, IV, VI)", "eye-movements.jpg"),
    "Visual fields by confrontation": ("Vision (II)", "visual-fields-by-confrontation.jpg"),
    "Visual acuity": ("Vision (II)", "visual-acuity.jpg"),
    "Ophthalmoscope: front of the eye, then the fundus": ("Inside the eye", "ophthalmoscope.jpg"),
    "Swinging flashlight test": ("Optic nerve problem", "swinging-flashlight-test.jpg"),
    "Red reflex": ("Opacity or misaligned eyes", "red-reflex.jpg"),
    "Slit lamp": ("Front of the eye", "slit-lamp.jpg"),
    "Inspect the external ear": ("Outer ear", "inspect-the-external-ear.jpg"),
    "Otoscopy": ("Canal and eardrum", "otoscopy.jpg"),
    "Whisper or finger-rub test": ("Is there hearing loss? (VIII)", "whisper-or-finger-rub-test.jpg"),
    "Weber test": ("Which kind of hearing loss?", "weber-test.jpg"),
    "Rinne test": ("Which kind of hearing loss?", "rinne-test.jpg"),
    "Nostril patency": ("Airflow", "nostril-patency.jpg"),
    "Septum and turbinates": ("Inside the nose", "septum-and-turbinates.jpg"),
    "Lips, tongue, teeth, gums and throat": ("Look first", "lips-tongue-teeth-gums-and-throat.jpg"),
    "Palate rise": ("Movement (IX, X, XII)", "palate-rise.jpg"),
    "Tongue": ("Movement (IX, X, XII)", "tongue.jpg"),
    "Hair and skin": ("Look first", "hair-and-skin.jpg"),
    "Facial movements": ("Nerves (VII, XI)", "facial-movements.jpg"),
    "Shoulder shrug and head turn": ("Nerves (VII, XI)", "shoulder-shrug-and-head-turn.jpg"),
    "Neck inspection": ("Look first", "neck-inspection.jpg"),
    "Lymph node palpation": ("Lumps and nodes", "lymph-node-palpation.jpg"),
    "Salivary glands": ("Lumps and nodes", "salivary-glands.jpg"),
    "Thyroid inspection": ("Thyroid", "thyroid-inspection.jpg"),
    "Thyroid palpation": ("Thyroid", "thyroid-palpation.jpg"),
}

# YouTube, Geeky Medics (ids checked with oEmbed on 2026-10-29)
GEEKY = "Geeky Medics"
OTHER_VIDEO = {
    "Otoscopy": {"id": "UvOcBxhdIVc", "title": "Otoscopy and hearing assessment", "channel": GEEKY},
    "Whisper or finger-rub test": {"id": "H-DVuHM0Bpo", "title": "Hearing and balance assessment (CN VIII)", "channel": GEEKY},
    "Weber test": {"id": "qYaU5Xo2i58", "title": "Rinne and Weber test", "channel": GEEKY},
    "Rinne test": {"id": "qYaU5Xo2i58", "title": "Rinne and Weber test", "channel": GEEKY},
    "Lymph node palpation": {"id": "SOACjGGAeTY", "title": "Head and neck lymph node palpation", "channel": GEEKY},
    "Thyroid inspection": {"id": "ziaYBkgEZNU", "title": "Thyroid status examination", "channel": GEEKY},
    "Thyroid palpation": {"id": "ziaYBkgEZNU", "title": "Thyroid status examination", "channel": GEEKY},
}

EXAM = exam_page.Exam(
    key="hn", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening={},
    h1="Head and neck exam",
    lead='Eye, ear, nose, mouth and face, then the neck.',
    find="Find a manoeuvre or a structure (e.g. Weber, thyroid, pupil)",
    root="Eye → Ear → Nose → Mouth → Face and head → Neck",
    root_note="Sit the patient up, look first, then use the instrument or your hands, and compare left with right. "
              "Several steps are also cranial nerve tests, so they come back in the neurological exam.",
    video_credit='Library videos from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries; Clinical Neurological Sciences, Schulich School of Medicine and Dentistry), "
                 "CC BY-NC 4.0, played from the library's own server; other videos are from the Geeky Medics channel on YouTube. "
                 "Each opens only when you tap it.",
    other_video=OTHER_VIDEO,
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    general_title="General approach", general_week="Every head and neck exam",
    spine_heading="What to look for", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "The general approach": [
  {
   "id": "wMiIapMcySg",
   "title": "ENT demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'

# captions for the landmark diagrams taken from the upper-year student notes
for _key, _cap in {'eye': 'Parts of the eye · tap to enlarge', 'ophth': 'Inside the eye · tap to enlarge'}.items():
    EXAM.region_text.setdefault(_key, {})['landmark_caption'] = _cap

if __name__ == "__main__":
    exam_page.build(EXAM)
