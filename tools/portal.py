# -*- coding: utf-8 -*-
"""What every course in the pre-clerkship portal shares.

Purpose: hold the course roster, the block-page template and the cache-busting
         helpers in one place, so four courses cannot drift into four dialects.
Author:  Noor Sims
Date:    2026-09-21

The portal is one site per year of pre-clerkship, all served from one origin and
all drawing on one engine (base.css, portal.css, quiz.js, notes.js, portal.js at
the repo root). A course is a directory, a block list and a set of question-set
families; everything else about it is data under its own directory.

Two of the four courses have no content yet. They are listed anyway, because the
portal's whole habit is to show the gap rather than hide it - a lecture with no
note still renders greyed, and a course with no blocks says so on the hub.
"""

import hashlib
import io
import json
import os
import re

# Progress is per-course in localStorage. The prefixes must stay distinct or one
# course would read and overwrite another's answers, since they share an origin.
COURSES = [
    {
        "slug": "fom",
        "short": u"FoM",
        "name": u"Foundations of Medicine",
        "year": u"Year 1",
        "blurb": u"The first fifteen weeks: what a physician does, then the body from "
                 u"cells up, then blood, then infection and immunity.",
        "accent": u"#4f2683",
        "store": "nsq.fom.v1.",
        "blocks": [
            ("b1", 1, u"Principles & Development",      u"1–4"),
            ("b2", 2, u"Regulation, Neoplasia & Aging", u"5–8"),
            ("b3", 3, u"Hematology",                    u"9–12"),
            ("b4", 4, u"Infection & Immunity",          u"13–15"),
        ],
        "families": [
            {"key": "meds2024", "name": u"Meds 2024 bank",
             "tip": u"Class of 2024 bank, mostly faculty-edited",
             "blurb": u"The student-written, instructor-approved bank built by the Class "
                      u"of 2024 Academic Directors in December 2020, re-filed week by "
                      u"week. Its questions went to the teaching faculty and the "
                      u"instructors' edits are folded in, except for a tail of each week "
                      u"that time ran out on."},
            {"key": "new", "name": u"Meds 2025",
             "tip": u"Meds 2025 volunteers' bank, not faculty-checked",
             "blurb": u"Written fresh by the Meds 2025 volunteers in December 2021. The "
                      u"bank states on its own second page that these were not verified "
                      u"by faculty, so treat a disagreement as a question worth chasing "
                      u"rather than a correction to accept."},
            {"key": "workbook", "name": u"Pre-Clerkship Workbook",
             "tip": u"Handed-down peer bank; key has errors",
             "blurb": u"The 2023 edition of the workbook handed down through the Schulich "
                      u"classes of 2015 to 2025: its Foundations, Hematology and "
                      u"Infection & Immunity chapters. The workbook files by subject "
                      u"rather than by week, so the block is its own but the week here is "
                      u"inferred; where nothing in a question placed it, it says so on "
                      u"its face. The Foundations chapter's own subject labels are in the "
                      u"Topic filter."},
            {"key": "reviews", "name": u"Schulich Reviews",
             "tip": u"Upper-year exam review sessions",
             "blurb": u"The Schulich Reviews sessions, run by upper years before each exam. "
                      u"Their own practice questions, keyed by the deck, plus questions "
                      u"written from their high-yield slides. Where a review disagrees "
                      u"with this year's lecture, the lecture wins and the question says so."},
        ],
    },
    {
        "slug": "pom1",
        "short": u"PoM 1",
        "name": u"Principles of Medicine 1",
        "year": u"Year 1",
        "blurb": u"The second half of first year, system by system.",
        "accent": u"#6b3fb8",
        "store": "nsq.pom1.v1.",
        "blocks": [
            ("cardio", 1, u"Cardiology",             u"1\u20135"),
            ("resp",   2, u"Respirology",            u"6\u20138"),
            ("ent",    3, u"Ear, Nose & Throat",     u"9"),
            ("gi",     4, u"Gastroenterology",       u"10\u201313"),
            ("gu",     5, u"Nephrology & Urology",   u"14\u201317"),
        ],
        "families": [
            {"key": "meds2024", "name": u"Meds 2024 bank",
             "tip": u"Class of 2024 bank, partly faculty-reviewed",
             "blurb": u"The student-written bank the Class of 2024 Academic Directors "
                      u"built in May 2021, re-filed week by week by the Meds 2025 "
                      u"volunteers. About half the cardiology questions and a handful of "
                      u"the respirology ones were reviewed by faculty; the rest were not, "
                      u"and the bank says so on its own second page."},
            {"key": "new", "name": u"Meds 2025",
             "tip": u"Meds 2025 volunteers' bank, not faculty-checked",
             "blurb": u"Written fresh by the Meds 2025 volunteers through the spring of "
                      u"2022 to fill the gaps. Not verified by faculty, so treat a "
                      u"disagreement as a question worth chasing rather than a correction "
                      u"to accept."},
            {"key": "workbook", "name": u"Pre-Clerkship Workbook",
             "tip": u"Handed-down peer bank; key has errors",
             "blurb": u"The 2023 edition of the workbook handed down through the Schulich "
                      u"classes of 2015 to 2025: its Cardiology, Respiration & Airways, "
                      u"Ear Nose & Throat, Gastroenterology and Genitourinary chapters. "
                      u"The workbook files by organ system rather than by week, so the "
                      u"block is its own and the week here is inferred; where nothing in "
                      u"a question placed it, it says so on its face."},
            {"key": "reviews", "name": u"Schulich Reviews",
             "tip": u"Upper-year exam review sessions",
             "blurb": u"The Schulich Reviews sessions, run by upper years before each exam. "
                      u"Their own practice questions, keyed by the deck, plus questions "
                      u"written from their high-yield slides. Where a review disagrees "
                      u"with this year's lecture, the lecture wins and the question says so."},
        ],
    },
    {
        "slug": "pom2",
        "short": u"PoM 2",
        "name": u"Principles of Medicine 2",
        "year": u"Year 2",
        "blurb": u"The five blocks of second year, with a written note for every "
                 u"lecture that has one and a coverage map for the rest.",
        "accent": u"#7a3fb0",
        "store": "nsq.v1.",
        "blocks": [
            ("endo",  1, u"Endocrinology",   u"1–3"),
            ("repro", 2, u"Reproduction",    u"4–6"),
            ("msk",   3, u"Musculoskeletal", u"7–12"),
            ("neuro", 4, u"Neurology",       u"13–16"),
            ("psych", 5, u"Psychiatry",      u"17–20"),
        ],
        "families": [
            {"key": "meds2029", "name": u"Case-Based Questions",
             "tip": u"Cases from student session notes",
             "blurb": u"Cases and questions from student notes from modules, in-class "
                      u"sessions and small-group sessions."},
            {"key": "reviews", "name": u"Schulich Reviews",
             "tip": u"Upper-year exam review sessions",
             "blurb": u"The Schulich Reviews sessions, run by upper years before each exam. "
                      u"Their own practice questions, keyed by the deck, plus questions "
                      u"written from their high-yield slides. Where a review disagrees "
                      u"with this year's lecture, the lecture wins and the question says so."},
            {"key": "hipponotes", "name": u"HippoNotes",
             "tip": u"Meds 2025 peer bank; check the key",
             "blurb": u"The question banks at the back of the Meds 2025 HippoNotes "
                      u"(Academic Resources Team, May 2023) - one document per block, "
                      u"written by the class two years ahead. Peer-written like the "
                      u"Workbook, so the key is worth checking rather than trusting; "
                      u"the source groups by week only, with no per-lecture attribution."},
            {"key": "workbook", "name": u"Pre-Clerkship Workbook",
             "tip": u"Handed-down peer bank; key has errors",
             "blurb": u"The Pre-Clerkship Workbook (2023 edition), the student bank passed "
                      u"down through the Schulich classes of 2015-2025. It has a written "
                      u"key, but the key is peer-written and contains real errors. Every "
                      u"one found is flagged on the question."},
            {"key": "offcurriculum", "name": u"Off-curriculum",
             "tip": u"Not taught in this year's lectures",
             "blurb": u"Questions from the handed-down banks and older sets that this "
                      u"year's lectures do not teach, or teach differently. Kept here "
                      u"rather than deleted, for anyone who wants them. Each one names "
                      u"the lecture it was checked against and says what that lecture "
                      u"teaches now."},
        ],
    },
    {
        "slug": "t2c",
        "short": u"T2C",
        "name": u"Transition to Clerkship",
        "year": u"Year 2",
        "blurb": u"The bridge into clerkship at the end of second year.",
        "accent": u"#3a2a6e",
        "store": "nsq.t2c.v1.",
        "blocks": [
            ("peds",   1, u"Pediatrics",                          u"1\u20132"),
            ("surg",   2, u"Surgery",                             u"3\u20134"),
            ("psych",  3, u"Psychiatry, Palliative & Geriatrics", u"5\u20136"),
            ("em",     4, u"Emergency Medicine",                  u"7"),
            ("fmob",   5, u"Family Medicine & Obstetrics",        u"8\u20139"),
            ("dermim", 6, u"Dermatology & Internal Medicine",     u"10\u201313"),
        ],
        "families": [
            {"key": "hipponotes", "name": u"HippoNotes",
             "tip": u"Meds 2025 peer bank; check the key",
             "blurb": u"The T2C question bank at the back of the Meds 2025 HippoNotes "
                      u"(Academic Resources Team, May 2023), filed under the rotation "
                      u"each question was written for. Peer-written, so the key is "
                      u"worth checking rather than trusting."},
        ],
    },
]

BY_SLUG = dict((c["slug"], c) for c in COURSES)

# the engine, shared by every course and living at the repo root
ASSETS = ["base.css", "portal.css", "portal.js", "quiz.js", "notes.js", "sync.js"]


def course_count(qs):
    """How many questions the page advertises. The off-curriculum set is kept
    to be drilled, not counted - quiz.js leaves it out of the scoreboard too."""
    return sum(1 for q in qs if q.get("family") != "offcurriculum")


def digest(path):
    """The content hash of a file, for cache busting."""
    return hashlib.md5(io.open(path, "rb").read()).hexdigest()[:8]


def asset(name):
    """<../name>?v=<hash>, as a course page one level down refers to it.

    Static hosts serve these with a cache lifetime of several minutes, long
    enough for a browser to paint new markup with last deploy's rules. Stamping
    the content hash into the URL makes a changed file a different URL; an
    unchanged one keeps its hash and stays cached. Re-run the builders after
    editing any of the hand-maintained css or js, or the pages keep pointing at
    the previous hash.
    """
    return "../%s?v=%s" % (name, digest(name))


def counts(course):
    """(questions, notes written, lectures) for a course, from its own data."""
    d = course["slug"]
    q = w = l = 0
    for slug, _n, _name, _weeks in course["blocks"]:
        qp = os.path.join(d, "data", "questions", "%s.json" % slug)
        np = os.path.join(d, "data", "notes", "%s.json" % slug)
        if os.path.exists(qp):
            q += course_count(json.load(io.open(qp, encoding="utf-8")))
        if os.path.exists(np):
            lects = [x for wk in json.load(io.open(np, encoding="utf-8"))["weeks"]
                     for x in wk["lectures"]]
            l += len(lects)
            # A lecture whose material is written up under a neighbouring lecture
    # counts as written: the note exists and the page says where. Counting it
    # as a gap would disagree with the coverage the page itself paints.
            w += len([x for x in lects
                      if x.get("hasNote") or x.get("coveredBy")])
    return q, w, l


FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;'
         '9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">')

# The theme. data-theme on the root is always "light" or "dark", and it is set
# here, in the head, before the stylesheets apply, so a dark page never paints
# light first. The reader's choice is kept in localStorage; with nothing stored
# the page follows the OS setting and keeps following it until the reader picks.
# With scripting off there is no attribute and the page is light. The toggle's
# handler lives in the same snippet because the hub loads no script file and
# the portal is not growing a fourth one for a button. ES5, like the rest; the
# click is caught on the document because the button is not built yet when
# this runs, and DOMContentLoaded labels it once it is.
THEME_SCRIPT = """<meta name="theme-color" content="#ffffff">
<script>
(function(){
  var root=document.documentElement,KEY="pc-theme",stored=null,mq=null;
  try{stored=localStorage.getItem(KEY);}catch(e){}
  if(stored!=="dark"&&stored!=="light")stored=null;
  if(window.matchMedia)mq=window.matchMedia("(prefers-color-scheme: dark)");
  function os(){return mq&&mq.matches?"dark":"light";}
  function apply(t){
    root.setAttribute("data-theme",t);
    var m=document.querySelector('meta[name="theme-color"]');
    if(m)m.setAttribute("content",t==="dark"?"#140c22":"#ffffff");
    var b=document.getElementById("theme-btn");
    if(!b)return;
    b.setAttribute("aria-pressed",t==="dark"?"true":"false");
    b.setAttribute("aria-label","Switch to "+(t==="dark"?"light":"dark")+" mode");
    b.title=b.getAttribute("aria-label");
  }
  function follow(){if(!stored)apply(os());}
  apply(stored||os());
  if(mq&&mq.addEventListener)mq.addEventListener("change",follow);
  else if(mq&&mq.addListener)mq.addListener(follow);
  document.addEventListener("DOMContentLoaded",function(){apply(root.getAttribute("data-theme"));});
  document.addEventListener("click",function(e){
    var s=e.target&&e.target.closest?e.target.closest(".skip"):null;
    if(s){
      var c=document.getElementById("content");
      if(c){e.preventDefault();c.focus();c.scrollIntoView();}
      return;
    }
    /* Still gets one tab, reused, so a second click brings the music
       forward rather than restarting it (see STILL_BTN) */
    var m=e.target&&e.target.closest?e.target.closest(".still-btn,.still-strip"):null;
    if(m){
      if(e.button||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;
      var w=null;
      try{w=window.open("","still-music");}catch(e3){}
      if(!w)return;
      e.preventDefault();
      try{if(w.location.href==="about:blank")w.location.replace(m.href);}catch(e4){}
      try{w.focus();}catch(e5){}
      return;
    }
    var b=e.target&&e.target.closest?e.target.closest("#theme-btn"):null;
    if(!b)return;
    stored=root.getAttribute("data-theme")==="dark"?"light":"dark";
    try{localStorage.setItem(KEY,stored);}catch(e2){}
    /* a crossfade between the themes where the browser can draw one and the
       reader has not asked for less motion; otherwise the switch is instant */
    var calm=window.matchMedia&&window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if(document.startViewTransition&&!calm)document.startViewTransition(function(){apply(stored);});
    else apply(stored);
  });
})();
</script>"""

# The phone's browser bar takes the page's background from the theme-color
# meta above, and apply() keeps it in step with the toggle, so a dark page does
# not sit under a white bar.
#
# Every page's "Skip to content" link (class "skip") is caught here too. It
# moves focus rather than following its href, because the course pages keep
# their tab and their filters in the hash and "#content" would clobber them;
# the href is there for a page with scripting off.

# The toggle. A moon while the page is light and a sun while it is dark, each
# an inline path rather than an image file, so the hub's one HTML file stays
# self-contained; the stylesheet shows one or the other by data-theme, and
# hides the button altogether when scripting is off and it could do nothing.
THEME_BTN = (
    '<button class="theme-btn" id="theme-btn" type="button" aria-pressed="false" '
    'aria-label="Switch to dark mode" title="Switch to dark mode">'
    '<svg class="moon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
    '<svg class="sun" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<circle cx="12" cy="12" r="4"/>'
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2'
    'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
    '</button>')

# Still, Ash's study music player: original music generated in the browser,
# so no copyrighted tracks, streams or tracking. A round link in the same
# corner as the toggle, on every page that has one. It is a page of its own
# rather than a player framed in here, because the portal is many pages and
# a framed player would stop every time the reader moved between them; the
# head script reuses one tab for it so the music keeps going. It opens a
# window named "still-music" with no URL: a blank one means there was none
# yet, so it is sent to Still; one already on Still is cross-origin, reading
# its location throws, and it is only focused, so it is never reloaded and
# never stops playing. With a modifier key, or when the browser blocks the
# window, the link does what a link does.
STILL_URL = "https://ashishsara.github.io/still/"
STILL_BTN = (
    '<a class="theme-btn still-btn" href="%s" target="_blank" rel="noopener" '
    'aria-label="Study music: open Still in a new tab" '
    'title="Study music: Still, original music made in your browser">'
    '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/>'
    '<circle cx="18" cy="16" r="3"/></svg>'
    '</a>' % STILL_URL)
THEME_BTN = STILL_BTN + THEME_BTN

# The CSS, JS and JSON are all content-hashed, so the browser may cache them
# forever. The pages that name those hashes must NOT be cached that way, or a
# rebuild is invisible until someone thinks to hard-refresh - which is exactly
# what happened. "no-cache" is not "don't store": it stores the page and asks
# whether it changed, so an unchanged page still costs one 304 and no download.
NOCACHE = ('<meta http-equiv="Cache-Control" content="no-cache, must-revalidate">\n'
           '<meta http-equiv="Pragma" content="no-cache">')

# Cloudflare Web Analytics: counts visits without cookies, so it needs no consent
# banner. The token is from the dashboard's Web Analytics > schulichmed.github.io
# snippet; it is public (it ships in every page) and not a secret. Leave it empty
# and the pages go out with no analytics at all.
CF_TOKEN = "d66f0003318d42f1bd62e0a2c3e216af"
CF = (f"<script type='module' src='https://static.cloudflareinsights.com/beacon.min.js' "
      f"data-cf-beacon='{{\"token\": \"{CF_TOKEN}\"}}'></script>") if CF_TOKEN else ""

# The visitor counter in tools/presence-worker/. Every page pings it once a
# minute while its tab is visible, so "online" counts readers anywhere in the
# portal, not only on the hub; the hub alone has the #presence slot that shows
# the answer. The slot stays hidden until a ping succeeds, so a counter that is
# not deployed, or is down, leaves no broken number behind. Empty URL, no
# script. It rides along with CF because CF is already in every page's head.
PRESENCE_URL = "https://preclerkship-presence.schulichmed.workers.dev/"
PRESENCE_SCRIPT = """<script>
(function(){
  var URL_=%s,MINUTE=60000,timer=null,visitor=null;
  function rid(){return Math.random().toString(36).slice(2,12)+Date.now().toString(36);}
  try{visitor=localStorage.getItem("pc-visitor");if(!/^[a-z0-9]{8,40}$/.test(visitor||"")){visitor=rid();localStorage.setItem("pc-visitor",visitor);}}catch(e){visitor=rid();}
  // one id per browser tab, kept in sessionStorage so a refresh or a click to
  // another portal page is the same reader rather than a new one; the leaving
  // beacon below cannot be relied on to clear the old id, since blockers drop it
  var tab=null;
  try{tab=sessionStorage.getItem("pc-tab");if(!/^[a-z0-9]{8,40}$/.test(tab||"")){tab=rid();sessionStorage.setItem("pc-tab",tab);}}catch(e){tab=rid();}
  function body(leaving){return JSON.stringify({site:"preclerkship",visitor:visitor,tab:tab,leaving:leaving});}
  function show(d){
    var el=document.getElementById("presence");
    if(!el||typeof d.total!=="number")return;
    el.querySelector("[data-total]").textContent=d.total.toLocaleString();
    el.hidden=false;
  }
  function ping(){
    if(!window.fetch)return;
    fetch(URL_,{method:"POST",headers:{"content-type":"application/json"},body:body(false)})
      .then(function(r){return r.ok?r.json():null;}).then(function(d){if(d)show(d);}).catch(function(){});
  }
  function start(){if(!timer){ping();timer=setInterval(ping,MINUTE);}}
  function stop(){if(timer){clearInterval(timer);timer=null;}}
  document.addEventListener("visibilitychange",function(){document.hidden?stop():start();});
  window.addEventListener("pagehide",function(){stop();if(navigator.sendBeacon)navigator.sendBeacon(URL_,body(true));});
  window.addEventListener("pageshow",function(e){if(e.persisted&&!document.hidden)start();});
  if(!document.hidden)start();
})();
</script>""" % json.dumps(PRESENCE_URL)
if PRESENCE_URL:
    CF += "\n" + PRESENCE_SCRIPT

# Sign in with Google, so progress and notes follow a reader to any device:
# sync.js, backed by Firebase (Google sign-in and a Firestore database, both on
# the free plan). Paste the firebaseConfig block from the Firebase console's
# Project settings > Your apps here as a dict. It names the project and is
# public by design, not a secret: what keeps each reader's progress their own
# is the Firestore rule that a signed-in user may touch only users/<their id>.
# Empty, and no page loads sync.js or shows the button.
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCW-gbfcaiOv1Dl-hDdDz7c-1m5ZWiWl5k",
    "authDomain": "public-medfriend.firebaseapp.com",
    "projectId": "public-medfriend",
    "storageBucket": "public-medfriend.firebasestorage.app",
    "messagingSenderId": "1083842121706",
    "appId": "1:1083842121706:web:c63c6c9132e37a3d876c93",
}


def sync_tag(base="../"):
    """The config and the deferred sync.js, for a page's head. base is the
    path to the repo root: "../" from a course page, "" from the hub."""
    if not FIREBASE_CONFIG:
        return ""
    cfg = {"firebase": FIREBASE_CONFIG, "stores": [c["store"] for c in COURSES]}
    return ('\n<script>window.PORTAL_SYNC_CFG = %s;</script>'
            '\n<script defer src="%ssync.js?v=%s"></script>'
            % (json.dumps(cfg), base, digest("sync.js")))


# The hub's corner readout, filled by PRESENCE_SCRIPT.
PRESENCE_SLOT = (
    '<p class="presence" id="presence" hidden>'
    '<span><b data-total></b> visits</span></p>')


# Where "All courses" points. Absolute, not relative: the portal is served from
# more than one place, and the hub every page should return to is this one
# wherever the copy being read happens to live.
HUB_URL = "https://schulichmed.github.io/preclerkship/"


def uplink(depth=None):
    """The one way back up to the hub, for pages that have no block nav."""
    return '<a class="uplink" href="%s">&larr; All courses</a>' % HUB_URL


CONTACT = "schulichmedfriend@gmail.com"
# Where the bank's Report button posts. Empty until the relay in
# tools/report-worker/ is deployed; empty, the button emails CONTACT instead.
REPORT_URL = "https://preclerkship-report.schulichmed.workers.dev/"


# Every page carries this, so it is said once, here.
def footer():
    return ('<footer>\n<p><strong>Unofficial and student-run.</strong> For any inquiries, '
            'email <a href="mailto:%s">%s</a>.</p>\n</footer>' % (CONTACT, CONTACT))


def favicon(label="PC", fill="4f2683", base="../"):
    """The tab icon, drawn inline per course, and the home-screen icon and
    manifest, which are files at the site root (made by tools/icons/). base
    is the way from the page to that root."""
    return ("<link rel=\"icon\" href=\"data:image/svg+xml,"
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
            "<rect width='32' height='32' rx='7' fill='%%23%s'/>"
            "<text x='16' y='23' font-family='Georgia,serif' font-size='%d' "
            "font-weight='600' fill='%%23ffffff' text-anchor='middle'>%s</text>"
            "</svg>\">\n"
            "<link rel=\"apple-touch-icon\" href=\"%sapple-touch-icon.png\">\n"
            "<link rel=\"manifest\" href=\"%ssite.webmanifest\">"
            % (fill, 17 if len(label) < 3 else 13, label, base, base))


# What a group chat, Slack or iMessage shows when a page's address is pasted:
# the page's own title and description over one shared card. Crawlers that
# draw previews do not run scripts, so these are in the HTML. The image URL
# must be absolute, hence HUB_URL.
SHARE_IMAGE = "share.png"


def share(html, path):
    """html with Open Graph and Twitter card tags added after its description.
    path is the page's own path from the site root ("" for the hub)."""
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    desc = re.search(r'<meta name="description" content="(.*?)">', html, re.S)
    if not title or not desc or 'property="og:title"' in html:
        return html
    tags = ('\n<meta property="og:type" content="website">'
            '\n<meta property="og:site_name" content="Schulich MedFriend">'
            '\n<meta property="og:title" content="%s">'
            '\n<meta property="og:description" content="%s">'
            '\n<meta property="og:url" content="%s%s">'
            '\n<meta property="og:image" content="%s%s">'
            '\n<meta property="og:image:width" content="1200">'
            '\n<meta property="og:image:height" content="630">'
            '\n<meta name="twitter:card" content="summary_large_image">'
            % (title.group(1).strip(), desc.group(1), HUB_URL, path, HUB_URL, SHARE_IMAGE))
    return html[:desc.end()] + tags + html[desc.end():]
