"""
Purpose: Build the neurological clinical skills page (neuro-exam/index.html) from the
         manoeuvre tables in the medwiki note "Summary Notes - Neurological Clinical Skills".
Author: Noor Simsam
Date: 2026-10-28
Input: the vault note (POM2_VAULT or the default vault path); img/credits.json; clips.json
       (the Health Education Media Library's neurology videos, by test, region or card)
Output: neuro-exam/index.html

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
NOTE = VAULT / "01 - Lectures/99 - Clinical Skills/Summary Notes - Neurological Clinical Skills.md"

# section number in the note -> region on the page
REGIONS = {
    2: ("mental", "Mental status and language", "PPES 2 · Weeks 8–9", "#3d6fb6"),
    3: ("cranial", "Cranial nerves", "PPES 2 · Weeks 8–9", "#23798a"),
    4: ("motor", "Motor", "PPES 2 · Weeks 8–9", "#7a3fb0"),
    5: ("reflexes", "Reflexes", "PPES 2 · Weeks 8–9", "#b4501f"),
    6: ("sensory", "Sensory", "PPES 2 · Weeks 8–9", "#a8366f"),
    7: ("coordination", "Coordination", "PPES 2 · Weeks 8–9", "#7d6413"),
    8: ("gait", "Balance and gait", "PPES 2 · Weeks 8–9", "#2f6b4f"),
    9: ("lesion", "Where is the lesion?", "PoM 2 · Neurology block", "#4d5590"),
}

# the note's opening section, shown as the first band
GENERAL = [(1, "The general approach")]

# manoeuvre name as the note shows it -> (problem heading, picture in img/)
TESTS = {
    "Language (aphasia screen)": ("Language", "language-aphasia-screen.jpg"),
    "CN I, olfactory: smell": ("Smell and hearing (I, VIII)", "cn-i-olfactory-smell.jpg"),
    "CN VIII, vestibulocochlear: hearing": ("Smell and hearing (I, VIII)", "cn-viii-vestibulocochlear-hearing.jpg"),
    "CN II, optic: visual acuity": ("The eye (II, III, IV, VI)", "cn-ii-optic-visual-acuity.jpg"),
    "CN II: visual fields by confrontation": ("The eye (II, III, IV, VI)", "cn-ii-visual-fields-by-confrontation.jpg"),
    "CN II and III: pupillary light reflex": ("The eye (II, III, IV, VI)", "cn-ii-and-iii-pupillary-light-reflex.jpg"),
    "CN II: swinging light test": ("The eye (II, III, IV, VI)", "cn-ii-swinging-light-test.jpg"),
    "CN II: fundoscopy": ("The eye (II, III, IV, VI)", "cn-ii-fundoscopy.jpg"),
    "CN III, IV, VI: eye movements": ("The eye (II, III, IV, VI)", "cn-iii-iv-vi-eye-movements.jpg"),
    "CN V, trigeminal: sensation": ("The face (V, VII)", "cn-v-trigeminal-sensation.jpg"),
    "CN V: motor": ("The face (V, VII)", "cn-v-motor.jpg"),
    "CN V and VII: corneal reflex": ("The face (V, VII)", "cn-v-and-vii-corneal-reflex.jpg"),
    "CN VII, facial: motor": ("The face (V, VII)", "cn-vii-facial-motor.jpg"),
    "CN VII: sensory": ("The face (V, VII)", "cn-vii-sensory-taste.jpg"),
    "CN IX and X: palate": ("Throat, neck and tongue (IX–XII)", "cn-ix-and-x-palate.jpg"),
    "CN IX and X: gag reflex": ("Throat, neck and tongue (IX–XII)", "cn-ix-x-gag-reflex.jpg"),
    "CN XI, spinal accessory": ("Throat, neck and tongue (IX–XII)", "cn-xi-spinal-accessory.jpg"),
    "CN XII, hypoglossal": ("Throat, neck and tongue (IX–XII)", "cn-xii-hypoglossal.jpg"),
    "Pronator drift": ("Arm power (C5–T1)", "pronator-drift.jpg"),
    "Shoulder abduction": ("Arm power (C5–T1)", "shoulder-abduction.jpg"),
    "Elbow flexion": ("Arm power (C5–T1)", "elbow-flexion.jpg"),
    "Elbow extension": ("Arm power (C5–T1)", "elbow-extension.jpg"),
    "Wrist extension": ("Arm power (C5–T1)", "wrist-extension.jpg"),
    "Finger extension": ("Arm power (C5–T1)", None),
    "Finger abduction": ("Arm power (C5–T1)", "finger-abduction.jpg"),
    "Grip strength": ("Arm power (C5–T1)", "grip-strength.jpg"),
    "Hip flexion": ("Leg power (L1–S1)", "hip-flexion.jpg"),
    "Hip adduction": ("Leg power (L1–S1)", None),
    "Hip abduction": ("Leg power (L1–S1)", None),
    "Knee extension": ("Leg power (L1–S1)", "knee-extension.jpg"),
    "Knee flexion": ("Leg power (L1–S1)", "knee-flexion.jpg"),
    "Ankle dorsiflexion": ("Leg power (L1–S1)", "ankle-dorsiflexion.jpg"),
    "Ankle plantar flexion": ("Leg power (L1–S1)", "ankle-plantar-flexion.jpg"),
    "Big toe extension": ("Leg power (L1–S1)", None),
    "Pain (pinprick)": ("Pain and temperature (spinothalamic)", "pain-pinprick.jpg"),
    "Temperature": ("Pain and temperature (spinothalamic)", "temperature.jpg"),
    "Light touch": ("Light touch", "light-touch.jpg"),
    "Vibration": ("Vibration and position (dorsal columns)", "vibration.jpg"),
    "Proprioception (joint position)": ("Vibration and position (dorsal columns)", "proprioception-joint-position.jpg"),
    "Stereognosis": ("Cortical sensation", "stereognosis.jpg"),
    "Graphesthesia": ("Cortical sensation", "graphesthesia.jpg"),
    "Extinction (both sides at once)": ("Cortical sensation", "extinction-both-sides-at-once.jpg"),
    "Two-point discrimination": ("Cortical sensation", "two-point-discrimination.jpg"),
    # section 9: levels of the nervous system: drawn concept schematics (lesion-<level>.jpg)
    "Cortex": ("Brain", "lesion-cortex.jpg"),
    "Subcortex (white matter, internal capsule)": ("Brain", "lesion-subcortex.jpg"),
    "Brainstem": ("Brain", "lesion-brainstem.jpg"),
    "Cerebellum": ("Brain", "lesion-cerebellum.jpg"),
    "Spinal cord": ("Spinal cord", "lesion-spinal-cord.jpg"),
    "Anterior horn cell": ("Spinal cord", "lesion-anterior-horn-cell.jpg"),
    "Nerve root": ("Peripheral (lower motor neuron)", "lesion-nerve-root.jpg"),
    "Plexus": ("Peripheral (lower motor neuron)", "lesion-plexus.jpg"),
    "Peripheral nerve": ("Peripheral (lower motor neuron)", "lesion-peripheral-nerve.jpg"),
    "Neuromuscular junction": ("Peripheral (lower motor neuron)", "lesion-neuromuscular-junction.jpg"),
    "Muscle": ("Peripheral (lower motor neuron)", "lesion-muscle.jpg"),
    "Biceps": ("Arm reflexes", "biceps.jpg"),
    "Brachioradialis": ("Arm reflexes", "brachioradialis.jpg"),
    "Triceps": ("Arm reflexes", "triceps.jpg"),
    "Knee (patellar)": ("Leg reflexes", "knee-patellar.jpg"),
    "Ankle (Achilles)": ("Leg reflexes", "ankle-achilles.jpg"),
    "Plantar response": ("Upper motor neuron sign", "plantar-response.jpg"),
    "Ankle clonus": ("Upper motor neuron sign", "ankle-clonus.jpg"),
    "Rapid alternating movements": ("Arms", "rapid-alternating-movements.jpg"),
    "Finger-nose": ("Arms", "finger-nose.jpg"),
    "Heel-shin": ("Legs", "heel-shin.jpg"),
    "Tandem gait": ("Walking", "tandem-gait.jpg"),
    "Romberg test": ("Balance", "romberg-test.jpg"),
}

# YouTube, Utah NeuroLogic Exam, Eccles Health Sciences Library Digital Publishing (University of Utah);
# "Sensory Exam: Normal" (id checked with oEmbed on 2026-11-01), started at each test's chapter
UTAH = "Eccles Health Sciences Library (Univ. of Utah)"
UTAH_ID = "uf8eSNFHeew"
UTAH_TITLE = "Sensory Exam: Normal (NeuroLogic Exam)"
OTHER_VIDEO = {
    "Temperature": {"id": UTAH_ID, "start": 212, "title": UTAH_TITLE, "channel": UTAH},
    "Two-point discrimination": {"id": UTAH_ID, "start": 509, "title": UTAH_TITLE, "channel": UTAH},
    "Graphesthesia": {"id": UTAH_ID, "start": 569, "title": UTAH_TITLE, "channel": UTAH},
}

EXAM = exam_page.Exam(
    key="neuro", folder=HERE, note=NOTE, regions=REGIONS, general=GENERAL, tests=TESTS, opening={},
    h1="Neurological exam",
    lead='The Year 2 Neurology Handbook screening exam: mental status and language, cranial nerves, motor (with reflexes), sensory, coordination, balance, then gait. <a href="neuro-one-pager.pdf">One-page summary (PDF)</a>',
    find="Find a manoeuvre or a level (e.g. C7, cerebellum)",
    root="Mental status → Cranial nerves → Motor → Reflexes → Sensory → Coordination → Balance → Gait",
    root_note="Compare left with right, and near the trunk with far. Every finding answers one question: where is "
              "the lesion, and is it an upper or a lower motor neuron problem?",
    video_credit='Videos from the <a href="https://rsc.lib.uwo.ca/s/healthedu/item-set">Health Education Media Library</a> '
                 "(Western Libraries; Clinical Neurological Sciences, Schulich School of Medicine and Dentistry), "
                 "CC BY-NC 4.0, played from the library's own server; the sensory-exam videos are from the University of Utah's NeuroLogic Exam "
                 "(Eccles Health Sciences Library) on YouTube. Each opens only when you tap it.",
    other_video=OTHER_VIDEO,
    clips=json.loads((HERE / "clips.json").read_text(encoding="utf-8")),
    general_title="General approach", general_week="Every neuro exam",
    spine_heading="What to look for", spine_title="Before the manoeuvres", pearls_heading="Pearls", count_noun="manoeuvres",
    region_text={"lesion": {"count_noun": "levels", "spine_title": "The approach",
                            "landmark_caption": "The approach to a neurological problem · tap to enlarge"}},
)

# Hamzah Algodi's own demonstration videos (his permission, 2026-11); shown on the spine cards
EXAM.walk = {
 "cranial": [
  {
   "id": "RCoFsjWy5gQ",
   "title": "Cranial nerves demonstration",
   "channel": "Hamzah Algodi"
  }
 ],
 "reflexes": [
  {
   "id": "XuBAEu-JWsE",
   "title": "Reflexes demonstration",
   "channel": "Hamzah Algodi"
  }
 ],
 "The general approach": [
  {
   "id": "HePBVeDMAio",
   "title": "Full neuro exam demonstration",
   "channel": "Hamzah Algodi"
  }
 ]
}
EXAM.video_credit += ' Demonstration videos by Hamzah Algodi ("*Unofficial* Schulich Clinical Skills"), used with his permission.'

# the handbook's "Definitions and terms": each mention on the page is underlined with a pop-up definition
EXAM.glossary = {
    "Dizzy": (r"dizzy|dizziness", "A patient's word that can mean vertigo, unsteadiness, ataxia or nausea: ask what they felt."),
    "Black out": (r"black(?:ing)?[ -]outs?", "A patient's word that can mean loss of consciousness, of memory or of vision: ask what happened."),
    "Allodynia": (r"allodynia", "Light touch and other harmless stimuli are felt as painful."),
    "Bell's palsy": (r"Bell(?:'|&#x27;|&#39;|’)s palsy", "Idiopathic inflammation of one facial nerve (CN VII), a lower motor neuron lesion, so the forehead is weak too."),
    "Clonus": (r"clonus", "A sudden stretch of a high-tone muscle makes it contract by reflex; if you hold the stretch, it keeps contracting in rhythmic beats. An upper motor neuron sign."),
    "Rigidity": (r"rigidity|rigid", "Increased tone that is the same at any speed and in every direction (velocity independent). A sign of extrapyramidal disease, e.g. Parkinson disease."),
    "Dysarthria": (r"dysarthria", "Speech volume and content are normal, but individual words are articulated and pronounced unclearly. A speech problem, not a language one."),
    "Extrapyramidal": (r"extrapyramidal", "The basal ganglia and their tracts: they suppress involuntary movements and start voluntary ones. Disease here often shows as rigid tone."),
    "Fasciculation": (r"fasciculations?", "Irregular, non-rhythmic twitches of muscle fascicles from whole motor units firing at random; fine or coarse. Tapping or warming the muscle brings them out. A lower motor neuron sign."),
    "Paresis": (r"\w*paresis", "Weakness (hemiparesis: one side; paraparesis: both legs; quadriparesis: all four limbs)."),
    "Plegia": (r"\w*plegia", "Paralysis (hemiplegia: one side)."),
    "Paresthesia": (r"paresthesias?|paraesthesias?", "Altered sensation, usually positive: pins and needles, tingling."),
    "Pyramidal pattern": (r"pyramidal(?: pattern)?", "Upper motor neuron weakness of the arm extensors (deltoids, triceps, wrist and finger extensors) and the leg flexors (hip flexion, knee flexion, ankle dorsiflexion, big toe extension)."),
    "Paratonia": (r"paratonia", "The patient cannot relax the muscles while you test tone."),
    "Spasticity": (r"spasticity|spastic", "Resistance is greatest as the movement starts, then suddenly gives way: a velocity-dependent increase in tone. An upper motor neuron sign."),
}

# the region clips are whole-section walkthroughs and a few clips with no card of their own, not movements
EXAM.moves_label = "Walkthroughs and more videos"

# captions for the landmark diagrams taken from the upper-year student notes
for _key, _cap in {'cranial': 'Eye movements and their nerves · tap to enlarge', 'motor': 'Wasting to look for · tap to enlarge', 'sensory': 'Dermatomes · tap to enlarge'}.items():
    EXAM.region_text.setdefault(_key, {})['landmark_caption'] = _cap

if __name__ == "__main__":
    exam_page.build(EXAM)
