"""
Purpose: Build the clinical skills course prototype in the portal's own structure: one block
         page per section, the course opening straight on the first (index.html redirects to history.html,
         exam.html, pocus.html, osce.html). landing.html, once a preview of the portal landing,
         now redirects to the live landing, which carries the clinical skills card itself.
Author: Noor Simsam
Date: 2026-10-28
Input: SECTIONS and SKILLS below (from the 2025-26 and 2026-27 clinical skills syllabi);
       portal_theme.html and portal_theme_btn.html, copied from the portal's pom2/index.html
Output: the five pages above, styled by the live portal's base.css and portal.css
"""

import html
import json
import re
import logging
from pathlib import Path

LOG = logging.getLogger("clinical_skills")
HERE = Path(__file__).resolve().parent
PORTAL = "https://schulichmed.github.io/preclerkship/"
COURSES = {"fom": "FoM", "pom1": "PoM 1", "pom2": "PoM 2", "t2c": "T2C"}

# (slug, name, when, hue, what): the hues are the PoM 2 block hues, so the cards sit in the family
SECTIONS = [
    ("history", "History taking", "FoM to T2C", "#8c3566",
     "The interview every history is built on, then the special histories: obstetric, psychiatric, paediatric and geriatric."),
    ("exam", "Physical exam", "FoM to T2C", "#2f5d7c",
     "One page per system, in the order you examine."),
    ("ultrasound", "Ultrasound", "PoM 1 and T2C", "#0d6154",
     "Point-of-care views of the heart and the abdomen."),
    ("osce", "OSCE prep", "Every TOSCE and the OSCE", "#4b3f96",
     "How a station runs, what is marked, and putting a whole encounter together."),
]

# (section, picture key in img/, name, courses in teaching order, page once built, what it holds)
SKILLS = [
    ("history", "interview", "The patient-centred interview", ["fom", "pom1"], "../interview-skill/",
     "The template every history follows: opening, the presenting illness, past history, medications, family and social history, closing."),
    ("history", "humility", "Cultural humility", ["pom1"], "../humility-skill/",
     "Gender-expansive care, and interviews in a language other than English."),
    ("history", "present", "Presenting a case", ["fom", "t2c"], "../present-skill/",
     "Presenting to a preceptor, and the problem-oriented write-up."),
    ("history", "obhx", "Obstetric and gynecologic history", ["pom2"], "../obhx-skill/",
     "Built on the course OB/Gyne history reference and the Ontario Perinatal Record."),
    ("history", "psychhx", "Psychiatric interview", ["pom2"], "../psychhx-skill/",
     "The psychiatric history and the mental status exam."),
    ("history", "pedshx", "Paediatric history", ["t2c"], "../pedshx-skill/",
     "Birth, development, growth, nutrition and immunizations; talking with children and families."),
    ("history", "gerihx", "Geriatric assessment", ["t2c"], "../gerihx-skill/",
     "Collateral history, function (daily activities) and gait in an older adult."),
    ("exam", "vitals", "Vital signs", ["fom"], "../vitals-exam/",
     "Look at the patient, then pulse, breathing and blood pressure."),
    ("exam", "resp", "Respiratory", ["fom", "pom1"], "../resp-exam/",
     "Inspect, palpate, percuss and listen, back then front."),
    ("exam", "abdo", "Abdominal", ["fom", "pom1"], "../abdo-exam/",
     "Inspect, listen, percuss and palpate, then the liver, spleen, ascites and appendicitis tests."),
    ("exam", "cardio", "Cardiovascular", ["fom", "pom1"], "../cardio-exam/",
     "Inspect, then the neck, palpate and listen, then pulses and edema."),
    ("exam", "breast", "Breast", ["fom"], "../breast-exam/",
     "Inspect, palpate the breast, then the axillary nodes."),
    ("exam", "hn", "Head and neck", ["pom1", "t2c"], "../hn-exam/",
     "Eye, ear, nose, mouth and face, then the neck."),
    ("exam", "neuro", "Neurological", ["pom1", "pom2"], "../neuro-exam/",
     "Mental status, cranial nerves, motor, sensory, reflexes, coordination, then gait."),
    ("exam", "msk", "Musculoskeletal", ["pom1", "pom2"], "../msk-exam/",
     "Look, feel, move, then special tests for every joint."),
    ("exam", "gu", "Male genital and rectal", ["t2c"], "../gu-exam/",
     "Penis, scrotum and testes, groin and hernias, then the rectal exam."),
    ("exam", "gyne", "Pelvic and obstetrical", ["pom2", "t2c"], "../gyne-exam/",
     "Position and look, speculum, bimanual, then the obstetrical abdominal exam."),
    ("ultrasound", "pocus", "Heart and abdomen", ["pom1", "t2c"], "../pocus-skill/",
     "The view of the heart from under the ribs, and the right upper quadrant."),
    ("osce", "station", "How a station runs", ["fom", "t2c"], "../station-skill/",
     "What is marked, and the opening lines to say for each exam."),
    ("osce", "consol", "Putting it together", ["t2c"], "../consol-skill/",
     "A full history and focused exam, then a problem list and a differential."),
]

# shorter names for the block bar, so a section's topics fit on one line
SHORT = {"interview": "Interview", "humility": "Cultural humility", "present": "Presenting",
         "obhx": "OB/Gyn history", "psychhx": "Psychiatric", "pedshx": "Paediatric",
         "gerihx": "Geriatric", "vitals": "Vitals", "resp": "Respiratory", "abdo": "Abdominal",
         "cardio": "Cardiovascular", "breast": "Breast", "hn": "Head and neck", "neuro": "Neuro",
         "msk": "MSK", "gu": "Male GU", "gyne": "Pelvic", "pocus": "Heart and abdomen",
         "station": "How a station runs", "consol": "Putting it together"}


def set_pages(keys: set[str]) -> None:
    """Give every topic in keys its built page (<key>.html beside this file)."""
    for i, (sec, key, name, taught, page, what) in enumerate(SKILLS):
        if key in keys and not page:
            SKILLS[i] = (sec, key, name, taught, f"{key}.html", what)


set_pages({s[1] for s in SKILLS if (HERE / f"{s[1]}.html").exists()})

# a topic with no notes yet stays out of the bar and the hub until its page is built
SKILLS[:] = [s for s in SKILLS if s[4]]

THEME = (HERE / "portal_theme.html").read_text(encoding="utf-8")
THEME_BTN = (HERE / "portal_theme_btn.html").read_text(encoding="utf-8")

HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="theme-color" content="#ffffff">
<title>{title}</title>
{theme}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{portal}base.css">
<link rel="stylesheet" href="{portal}portal.css">
<style>
/* topic cards: a block card led by its icon, drawn in the section's hue */
.topic-grid{{grid-template-columns:repeat(auto-fill,minmax(230px,1fr));}}
.topic-card .ico{{display:block;width:44px;height:44px;margin-bottom:14px;color:var(--hue);}}
.topic-card .ico svg{{width:100%;height:100%;}}
.topic-card h2{{font-size:1.15rem;}}
.topic-card .go{{display:block;margin-top:14px;font-size:.82rem;font-weight:600;color:var(--hue);}}
.block-card.is-empty .go{{font-weight:500;font-style:italic;color:var(--muted);}}
.credits{{margin-top:40px;font-size:.75rem;color:var(--muted);}}
</style>
</head>
<body>
<a class="skip" href="#content">Skip to content</a>
<div class="pom2-page">
"""

# the portal's back-to-top pill (its notes tabs' posbar, styled by portal.css), shown once the page is scrolled
FOOT = """
<footer>
<p><strong>Unofficial and student-run.</strong> For any inquiries, email <a href="mailto:schulichmedfriend@gmail.com">schulichmedfriend@gmail.com</a>.</p>
</footer>
</div>
<div class="posbar notebar" id="notebar" hidden>
<button class="pb-step pb-top" id="nb-top" type="button" title="Back to the top" aria-label="Back to the top">Top</button>
</div>
<script>
(function () {
  var bar = document.getElementById("notebar"), queued = false;
  document.getElementById("nb-top").addEventListener("click", function () {
    var still = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    try { window.scrollTo({ top: 0, behavior: still ? "auto" : "smooth" }); } catch (e) { window.scrollTo(0, 0); }
  });
  function paint() { bar.hidden = window.pageYOffset <= 400; }
  window.addEventListener("scroll", function () {
    if (queued) return;
    queued = true;
    window.requestAnimationFrame(function () { queued = false; paint(); });
  }, { passive: true });
  paint();
})();
</script>
</body>
</html>
"""


def esc(text: str) -> str:
    """Escape text for HTML."""
    return html.escape(text, quote=True)


def head(title: str) -> str:
    """Return the page head and the opening of the portal's page wrapper."""
    return HEAD.format(title=esc(title), theme=THEME, portal=PORTAL)


def tally(slug: str) -> tuple[int, int]:
    """Return (topics, pages built) for one section."""
    rows = [s for s in SKILLS if s[0] == slug]
    return len(rows), sum(1 for s in rows if s[4])


def noun(slug: str, n: int) -> str:
    """Return 'exams' for the physical exam section, else 'topic(s)'."""
    return "exams" if slug == "exam" else ("topic" if n == 1 else "topics")


def block_card(slug: str, name: str, when: str, hue: str, what: str, number: int) -> str:
    """Return one section as a portal block card."""
    total, built = tally(slug)
    return f"""<a class="block-card" href="{slug}.html" style="--hue:{hue}">
<p class="bmeta">Section {number} &middot; {esc(when)}</p>
<h2>{esc(name)}</h2>
<p>{esc(what)}</p>
<span class="tally">
<span><b>{total}</b> {noun(slug, total)}</span>
<span><b>{built}</b> ready</span>
</span>
</a>"""


def course_page() -> str:
    """Return index.html as a redirect: the course opens straight on its first section, so a
    student reaches topics in one tap, and the section bar moves between the four sections."""
    first = SECTIONS[0][0]
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="robots" content="noindex, nofollow, noarchive">
<meta http-equiv="refresh" content="0; url={first}.html"><link rel="canonical" href="{first}.html">
<title>Clinical skills</title></head>
<body><p><a href="{first}.html">Clinical skills</a></p></body></html>
"""

def blocknav(current: str) -> str:
    """Return the section bar every block page opens on, as the PoM 2 block pages."""
    links = [f'<a class="home" href="{PORTAL}">All courses</a>']
    for i, (slug, name, *_rest) in enumerate(SECTIONS, 1):
        here = ' class="here"' if slug == current else ""
        links.append(f'<a href="{slug}.html"{here}>{i} &middot; {esc(name)}</a>')
    return '<nav class="blocknav" aria-label="Sections">\n' + "\n".join(links) + f"\n{THEME_BTN}\n</nav>"


def icon(key: str) -> str:
    """Return a topic's Healthicons outline icon (CC0) as inline SVG, so it takes the text colour."""
    svg = (HERE / "icons" / f"{key}.svg").read_text(encoding="utf-8")
    return re.sub(r'<svg width="\d+" height="\d+"', '<svg aria-hidden="true" focusable="false"', svg, count=1)


def topic_card(pic: str, name: str, taught: list[str], page: str | None, what: str, hue: str) -> str:
    """Return one topic as a block card led by its icon; a topic with no page yet is dimmed."""
    when = " &rarr; ".join(COURSES[c] for c in taught)
    body = f"""<span class="ico">{icon(pic)}</span>
<p class="bmeta">{when}</p>
<h2>{esc(name)}</h2>
<p>{esc(what)}</p>"""
    if page:
        return f'<a class="block-card topic-card" href="{page}" style="--hue:{hue}">\n{body}\n<span class="go">Open &rarr;</span>\n</a>'
    return f'<div class="block-card topic-card is-empty" style="--hue:{hue}">\n{body}\n<span class="go">Coming soon</span>\n</div>'


def section_page(number: int, slug: str, name: str, when: str, hue: str, what: str) -> str:
    """Return one section's block page: the section bar, masthead and a card per topic."""
    rows = [s for s in SKILLS if s[0] == slug]
    cards = "\n".join(topic_card(*s[1:], hue=hue) for s in rows)
    return head(f"{name} - Clinical skills") + blocknav(slug) + f"""

<header class="q-masthead" id="content" tabindex="-1">
<div>
<p class="eyebrow">Schulich Clinical Skills &middot; Section {number} &middot; {esc(when)}</p>
<h1>{esc(name)}</h1>
<p class="lead">{esc(what)}</p>
</div>
</header>

<main>
<div class="block-grid topic-grid">
{cards}
</div>
<p class="credits">Icons: <a href="https://healthicons.org">Healthicons</a> (CC0).</p>
</main>
""" + FOOT


EXAM_NAV_CSS = """<style>
/* the portal's block bar (.blocknav in portal.css), rebuilt for pages that carry their own
   stylesheet; on a page that loads portal.css the two agree */
.csn{display:flex;flex-wrap:wrap;align-items:center;gap:4px;padding:5px;margin:0 0 22px;
  background:var(--card-bg,var(--card));border:1px solid var(--border,var(--line));border-radius:8px}
.csn a,.csn span{padding:6px 12px;border-radius:4px;font-size:.82rem;font-weight:500;
  color:var(--muted);white-space:nowrap;text-decoration:none;transition:color .15s,background .15s}
.csn a:hover{color:var(--text,var(--ink))}
.csn .here{background:var(--q-accent-soft,color-mix(in srgb,var(--accent) 14%,transparent));
  color:var(--q-accent-ink,var(--accent));font-weight:600}
.csn .home{margin-right:6px;font-size:.7rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase}
.csn .soon{opacity:.45;cursor:default}
</style>"""


def exam_nav(current: str, base: str = "../clinical-skills/") -> str:
    """Return the bar an exam page opens on, built like the portal's block bar: CLINICAL SKILLS
    and the section on the left, then every topic in the section, this one shaded and the
    ones without a page yet faded. Every exam page carries the same bar."""
    sec = next(s for s in SKILLS if s[1] == current)[0]
    sec_name = next(s[1] for s in SECTIONS if s[0] == sec)
    items = [f'<a class="home" href="{PORTAL}">All courses</a>',
             f'<a class="home" href="{base}{sec}.html">{esc(sec_name)} &rsaquo;</a>']
    for _sec, key, name, _taught, page, _what in (s for s in SKILLS if s[0] == sec):
        if key == current:
            items.append(f'<span class="here" aria-current="page">{esc(SHORT[key])}</span>')
        elif page:
            items.append(f'<a href="{base}{page}">{esc(SHORT[key])}</a>')
        else:
            items.append(f'<span class="soon" title="Coming soon">{esc(SHORT[key])}</span>')
    return f"""{EXAM_NAV_CSS}
<nav class="csn" aria-label="{esc(sec_name)}">
{chr(10).join(items)}
</nav>"""


def landing_page() -> str:
    """Return landing.html as a redirect to the live portal landing, so old links reach the real
    hub: the preview it used to be went stale once the hub got its own clinical skills card."""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="robots" content="noindex, nofollow, noarchive">
<meta http-equiv="refresh" content="0; url={PORTAL}"><link rel="canonical" href="{PORTAL}">
<title>Schulich Pre-clerkship</title></head>
<body><p><a href="{PORTAL}">All courses</a></p></body></html>
"""


def main() -> None:
    """Write the course page, the section pages and the landing redirect."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    pages = {"index.html": course_page(), "landing.html": landing_page()}
    for i, section in enumerate(SECTIONS, 1):
        pages[f"{section[0]}.html"] = section_page(i, *section)
    for name, text in pages.items():
        (HERE / name).write_text(text, encoding="utf-8")
        LOG.info("wrote %s", name)


if __name__ == "__main__":
    main()
