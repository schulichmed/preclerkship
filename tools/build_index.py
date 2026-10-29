# -*- coding: utf-8 -*-
"""Point each course's old landing page at its first block.

Purpose: each course's index.html is now a redirect to its first block page. The portal's
         landing cards open that block directly, and every block page's bar reaches the
         other blocks and the question bank, so the course page only added a click. The
         template and card builder below are kept unused, in case the page comes back.
Author:  Noor Sims
Date:    2026-09-21
Input:   tools/portal.py, each course's data/ and block pages, and the landing
         page being replaced (for its hero blurb and its prose section)
Output:  <course>/index.html

Run from the repo root, after build_pages.py. The prose under each landing page
is read back out of the page being replaced rather than held here, for the same
reason the block pages keep their own blurbs: it is written by hand, it is long,
and a rebuild must not quietly revert it. A course with no page yet gets the
seed below, which is deliberately thin - it is a placeholder saying the course
is not built, not a pretence that it is.
"""

import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal

FAVICON = {"fom": ("FM", "4f2683"), "pom2": ("P2", "7a3fb0"),
           "pom1": ("P1", "6b3fb8"), "t2c": ("T2C", "3a2a6e")}

EMPTY_PROSE = u"""<div class="prose">

</div>"""


def part(page, opener, closer="\n</div>"):
    i = page.index(opener)
    j = page.index(closer, i)
    return page[i:j + len(closer)]


def existing(course):
    """(hero blurb, prose block) from the page being replaced, or the seed."""
    p = os.path.join(course["slug"], "index.html")
    if not os.path.exists(p):
        return course["blurb"], EMPTY_PROSE
    s = io.open(p, encoding="utf-8").read()
    hero = re.search(r'<div class="page-hero[^"]*">\s*<h1>.*?</h1>\s*(.*?)\s*</div>', s, re.S)
    prose = part(s, '<div class="prose">')
    return (hero.group(1) if hero else course["blurb"]), prose


def cards(course):
    """A block is its notes and its Anki deck; its questions are in the bank."""
    out = []
    for slug, n, name, weeks in course["blocks"]:
        page = io.open(os.path.join(course["slug"], "%s.html" % slug),
                       encoding="utf-8").read()
        blurb = re.search(r'<p class="lead">\s*(.*?)\s*</p>', page, re.S).group(1)
        hue = re.search(r'--q-accent:(#\w+);', page).group(1)
        qs = json.load(io.open(os.path.join(course["slug"], "data", "questions",
                                            "%s.json" % slug), encoding="utf-8"))
        nt = json.load(io.open(os.path.join(course["slug"], "data", "notes",
                                            "%s.json" % slug), encoding="utf-8"))
        lects = [l for w in nt["weeks"] for l in w["lectures"]]
        # A lecture whose material is written up under a neighbouring lecture
    # counts as written: the note exists and the page says where. Counting it
    # as a gap would disagree with the coverage the page itself paints.
        written = len([l for l in lects
                       if l.get("hasNote") or l.get("coveredBy")])
        out.append(
            u'<a class="block-card" href="%s.html" style="--hue:%s">\n'
            u'<p class="bmeta">Block %d &middot; %s %s</p>\n'
            u'<h2>%s</h2>\n<p>%s</p>\n'
            u'<span class="tally">\n'
            u'<span><b>%d</b> lecture notes</span>\n'
            u'<span><b>%d</b> questions in the bank</span>\n'
            u'</span>\n'
            u'</a>' % (slug, hue, n,
                      # a block that is one week long says "Week", not "Weeks"
                      u"Weeks" if re.search(u"[-\u2013]", weeks) else u"Week",
                      weeks, name, blurb, written, portal.course_count(qs)))
    return "\n".join(out)


TEMPLATE = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{short}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="noindex, nofollow">
{favicon}

{nocache}
{theme}
{fonts}
<link rel="stylesheet" href="{base_css}">
<link rel="stylesheet" href="{portal_css}">
<style>
:root{{--q-accent:{accent};--q-accent-soft:#ede5f9;--q-accent-ink:{accent};}}
</style>
{cf}
</head>
<body>
<a class="skip" href="#content">Skip to content</a>

<div class="pom2-page">

<header class="topline">
{uplink}
{toggle}
</header>

<main id="content" tabindex="-1">

<div class="page-hero compact">
<h1>{short}.</h1>
{hero}
</div>

<div class="block-grid">
{cards}
</div>

{prose}

</main>

{footer}

</div>

</body>
</html>
"""


REDIRECT = u"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0; url={first}.html">
<link rel="canonical" href="{first}.html">
<title>{short}</title>
</head>
<body><p><a href="{first}.html">{short}</a></p></body>
</html>
"""


def main():
    """Write each course's index.html as a redirect to its first block. The landing cards
    open that block directly; the redirect keeps old links and bookmarks working."""
    for course in portal.COURSES:
        if not course["blocks"]:
            continue
        first = course["blocks"][0][0]
        io.open(os.path.join(course["slug"], "index.html"), "w", encoding="utf-8",
                newline="\n").write(REDIRECT.format(first=first, short=course["short"]))
        print("%-5s index.html -> %s.html" % (course["slug"], first))


if __name__ == "__main__":
    main()
