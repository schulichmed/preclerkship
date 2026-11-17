"""
Purpose: Build the cardiovascular clinical skills page (cardio-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Cardiovascular Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; videos.json
       (Geeky Medics); clips.json (open-licence heart-sound audio from Wikimedia Commons)
Output: cardio-exam/index.html

The note is the single source of the steps and positive findings: edit the note,
then rerun this script. Which problem heading each manoeuvre sits under, and its
picture, are set here. How the page looks lives in clinical-skills/exam_page.py,
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
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Cardiovascular Clinical Skills.md"

CORE = "PPES 1 · Week 4"
ADV = "PoM 1 · Cardiology"
# section number in the note -> region on the page
REGIONS = {
    3: ("inspect", "Inspect", CORE, "#3d6fb6"),
    4: ("neck", "Neck: JVP and carotids", CORE, "#23798a"),
    5: ("palpate", "Palpate the precordium", CORE, "#7a3fb0"),
    6: ("auscultate", "Auscultate", CORE, "#a8366f"),
    7: ("pulses", "Pulses and edema", CORE, "#b4501f"),
    8: ("murmurs", "The four classic murmurs", ADV, "#7d6413"),
    9: ("finish", "Finishing the exam", ADV, "#2f6b4f"),
}

# the note's opening sections, shown as the first band
GENERAL = [(1, "The general approach"), (2, "Before you examine: the cardiac history")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "General inspection": ("Look at the whole patient", "general-inspection.jpg"),
    "Hands": ("Look at the whole patient", "hands.jpg"),
    "Face and eyes": ("Look at the whole patient", "face-xanthelasma.jpg"),
    "Chest wall inspection": ("Look at the chest", "chest-wall-inspection.jpg"),
    "JVP (jugular venous pressure)": ("Neck veins: right-sided pressure", "jvp-raised.jpg"),
    "Hepatojugular reflux": ("Neck veins: right-sided pressure", None),
    "Carotid pulse": ("Carotid artery", "carotid-pulse.jpg"),
    "Carotid bruit": ("Carotid artery", None),
    "Apical impulse (PMI)": ("Size and strength of the heart", "apical-impulse.jpg"),
    "Heaves and lifts": ("Things you can feel through the chest wall", None),
    "Thrills": ("Things you can feel through the chest wall", None),
    "Rub": ("Things you can feel through the chest wall", None),
    "Listening areas": ("Where and how to listen", "listening-areas.jpg"),
    "Rhythm, S1 and S2": ("Normal and extra sounds", "heart-sounds-cycle.jpg"),
    "Extra heart sounds": ("Normal and extra sounds", "heart-sounds-cycle.jpg"),
    "Describing a murmur": ("Murmurs", "describing-a-murmur.jpg"),
    "Aortic regurgitation position": ("Murmurs", "murmur-aortic-regurgitation.jpg"),
    "Carotid auscultation": ("Where and how to listen", None),  # still reclined, before the left-side and sitting-forward steps
    "Radial pulse": ("Arm pulses", "radial-pulse.jpg"),
    "Brachial pulse": ("Arm pulses", "brachial-pulse.jpg"),
    "Femoral pulse": ("Leg pulses", "femoral-pulse.jpg"),
    "Popliteal pulse": ("Leg pulses", None),
    "Posterior tibial pulse": ("Leg pulses", None),
    "Dorsalis pedis pulse": ("Leg pulses", "dorsalis-pedis-pulse.jpg"),
    "Capillary refill": ("Circulation and fluid", "capillary-refill.jpg"),
    "Peripheral edema": ("Circulation and fluid", "peripheral-edema.jpg"),
    "Aortic stenosis": ("Valves that will not open", "murmur-aortic-stenosis.jpg"),
    "Mitral stenosis": ("Valves that will not open", "murmur-mitral-stenosis.jpg"),
    "Aortic regurgitation": ("Valves that leak", "murmur-aortic-regurgitation.jpg"),
    "Mitral regurgitation": ("Valves that leak", "murmur-mitral-regurgitation.jpg"),
    "Tricuspid regurgitation": ("Valves that leak", "tricuspid-regurgitation.jpg"),
    "Liver and aorta": ("Beyond the heart", "liver-palpation.jpg"),
    "Ascites": ("Beyond the heart", "ascites.jpg"),
    "Lung bases and sacrum": ("Beyond the heart", "lung-bases.jpg"),
}

OPENING = {
    "inspect": "I'd like to start by looking at you, your hands, your face and your chest. Please lie back at an angle, and I'll keep you covered.",
    "neck": "Now I'd like to look at the veins in your neck and feel your neck pulse. Please turn your head slightly away from me.",
    "palpate": "I'm going to feel the front of your chest over your heart, to find your heartbeat and check for any vibrations.",
    "auscultate": "Now I'll listen to your heart with the stethoscope in four places. It may feel cold; please breathe normally.",
    "pulses": "Finally I'd like to feel the pulses in your arms and legs, and check your ankles for swelling.",
}

TAUGHT_VIDEO = "https://geekymedics.com/cardiovascular-examination-2/"
EXAM = exam_page.Exam(
    key="cardio", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening=OPENING,
    h1="Cardiovascular exam",
    lead='Inspect, then the neck, palpate and listen, then pulses and edema.',
    find="Find a manoeuvre or a murmur (e.g. JVP, apex, mitral)",
    root="Inspect → Palpate → Percuss → Auscultate",
    root_note="Neck veins and carotids, then the precordium and its four listening areas, then the pulses and the legs. "
              "Compare one side with the other, and time every sound against the carotid pulse.",
    video_credit='Demonstration video from <a href="https://geekymedics.com/cardiovascular-examination-2/">Geeky Medics</a> '
                 "(YouTube), loaded only when you tap it. Heart-sound audio from Wikimedia Commons, "
                 "Kudriavtsev, Polyshchuk and Roy (CC BY 2.0): aortic stenosis and a split S2. "
                 "Audio plays in Chrome, Firefox and Edge; Safari does not play .ogg files. "
                 "Other demonstrations are YouTube videos from AMBOSS, Open RN, JAMA Network and Emory University, loaded only when tapped.",
    video={}, video_page="", region_video={},
    other_video={
        "JVP (jugular venous pressure)": {"id": "Ez7KsKRi8e8", "start": 0, "title": "Measuring the JVP", "channel": "Geeky Medics"},
        "Describing a murmur": {"id": "Q5-0mSydRR4", "start": 0, "title": "Heart murmur sounds", "channel": "Geeky Medics"},
        "Peripheral edema": {"id": "1kfg1mYRJ-g", "start": 0, "title": "Peripheral vascular exam", "channel": "Geeky Medics"},
        "Hepatojugular reflux": {"id": "JxyECMTEmmc", "start": 0, "title": "Testing the hepatojugular reflux", "channel": "AMBOSS"},
        "Carotid bruit": {"id": "2DKucnJo2P4", "start": 0, "title": "Auscultation of carotid arteries", "channel": "Open RN"},
        "Carotid auscultation": {"id": "2DKucnJo2P4", "start": 0, "title": "Auscultation of carotid arteries", "channel": "Open RN"},
        "Heaves and lifts": {"id": "PaiYGbqgqRg", "start": 0, "title": "Palpation of the precordium", "channel": "Open RN"},
        "Thrills": {"id": "PaiYGbqgqRg", "start": 0, "title": "Palpation of the precordium", "channel": "Open RN"},
        "Rub": {"id": "b_FvP2Vw0OY", "start": 0, "title": "Three-component pericardial friction rub", "channel": "JAMA Network"},
        "Popliteal pulse": {"id": "ITAHG6V2-b8", "start": 0, "title": "Popliteal artery palpation", "channel": "Emory University MSK"},
        "Posterior tibial pulse": {"id": "zly846Ncsd8", "start": 0, "title": "Palpating the dorsalis pedis and posterior tibial pulses", "channel": "Open RN"},
    },
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    general_title="General approach", general_week="Every cardiovascular exam",
    spine_heading="What to look for", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
)
EXAM.video_page = TAUGHT_VIDEO + "#{slug}"
EXAM.region_video = {"The general approach": ["cardiovascular-examination"]}
EXAM.video = {}

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "The general approach": [
  {
   "id": "K5grjMcI2j0",
   "title": "Cardiovascular demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'

# captions for the landmark diagrams taken from the upper-year student notes
for _key, _cap in {'auscultate': 'Where to listen · tap to enlarge', 'neck': 'Carotid artery and jugular veins · tap to enlarge', 'murmurs': 'The four valves · tap to enlarge'}.items():
    EXAM.region_text.setdefault(_key, {})['landmark_caption'] = _cap

if __name__ == "__main__":
    exam_page.build(EXAM)
