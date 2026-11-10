"""Guided judge path — a no-login demo with synthetic material only.

A visitor (for example a hackathon judge with four minutes) can
walk the real beats of a sitting — talk, chapter draft,
source-check, approval, keepsake — without collecting any real
story, and without touching the real sitting's gates:

* Nothing here is a real user's story. The telling, the photo
  description, the dedication and the chapter are all invented
  for this demo and are labelled as such in every payload and
  on the page that renders them.
* No real user input is sent to any model on this path. The
  exchange is preloaded and canned; no chat endpoint is called.
* The 18+ consent gate for REAL sittings is untouched: this
  module creates no session, stores nothing, and mints no
  share link. It exists precisely so a visitor can see the
  shape of the product without handing anything over.

The one real piece of machinery the demo reuses is the
chapter module's deterministic source-check (chapter.source_check):
the synthetic draft below carries ONE planted detail that does
not appear in the synthetic telling, and the check that flags
it is the same function that checks real drafts.
"""
from . import chapter as chapter_mod

# --- The synthetic telling -------------------------------------
# Clearly fictional: a grandfather's workshop, invented for the
# demo. The storyteller character is "Margaret" only inside this
# made-up sample; no real person told any of this.

TELLING = [
    {
        "speaker": "storyteller",
        "text": (
            "My grandfather kept a small workshop behind his house "
            "in Dayton. The walls were lined with jars of screws "
            "and nails, each one labelled in pencil in his "
            "careful hand."
        ),
    },
    {
        "speaker": "liv",
        "text": (
            "Jars along the wall, each one labelled in pencil — "
            "I can picture the care in that. What did he make "
            "in there?"
        ),
    },
    {
        "speaker": "storyteller",
        "text": (
            "Mostly he mended things for neighbours. He taught me "
            "to sharpen a chisel on a whetstone by the window. "
            "I can still smell the pine shavings and the oil, and "
            "hear the radio playing low while he worked."
        ),
    },
    {
        "speaker": "liv",
        "text": (
            "The whetstone by the window, the radio low — thank "
            "you for letting me sit in that room a moment. "
            "Would you like to show me the photograph you "
            "mentioned?"
        ),
    },
    {
        "speaker": "storyteller",
        "text": (
            "This photograph shows his workbench by the window, "
            "with the whetstone, a chisel, and jars of screws "
            "lined up along the back edge."
        ),
    },
]

PHOTO = {
    "kind": "photo",
    "description": (
        "A made-up photo description for the demo: a workbench "
        "by a window, a whetstone and a chisel on it, and jars "
        "of screws lined up along the back edge."
    ),
    "caption": "The workbench by the window",
}

TITLE = "The Workshop Behind the House"
DEDICATION = "my family"

# The one forwardable line the demo keepsake carries — the same
# shape the real keepsake share card uses.
SUMMARY_LINE = (
    "\u201cThe Workshop Behind the House\u201d \u2014 a sample "
    "chapter arranged from a made-up conversation with Liv, "
    "reviewed in the guided demo."
)


def _sources():
    """The synthetic telling as chapter sources (words only,
    plus the photo's caption) — the corpus the source-check
    checks the draft against."""
    sources = []
    n = 0
    for turn in TELLING:
        if turn["speaker"] != "storyteller":
            continue
        n += 1
        sources.append({
            "id": "s%d" % n,
            "kind": "words",
            "label": chapter_mod._telling_label(turn["text"]),
            "text": turn["text"],
            "media_id": None,
        })
    return sources


def _draft():
    """The synthetic draft. Two sections arrange the telling;
    ONE detail is planted on purpose — the year 1968 appears
    nowhere in the telling — so the real source-check has
    something honest to flag."""
    return {
        "title": TITLE,
        "dedication": DEDICATION,
        "mode": "guided",
        "sections": [
            {
                "heading": "The beginning",
                "paragraphs": [
                    {"text": TELLING[0]["text"], "source_ids": ["s1"]},
                ],
                "media_ids": [],
            },
            {
                "heading": "Where it rests",
                "paragraphs": [
                    {"text": TELLING[2]["text"], "source_ids": ["s2"]},
                    {
                        "text": (
                            "In 1968, he built the workshop himself, "
                            "working through the winter to finish it."
                        ),
                        "source_ids": [],
                    },
                ],
                "media_ids": [],
            },
        ],
    }


def demo_payload():
    """Everything the guided page renders, in beat order.

    The source-check result is computed here, at request time,
    by the chapter module's real deterministic check — it is
    not a stored or invented result.
    """
    sources = _sources()
    draft = _draft()
    check = chapter_mod.source_check(draft, sources)
    return {
        "guided_demo": True,
        "synthetic": True,
        "notice": (
            "This is a guided demo with a made-up sample story. "
            "No real story is collected here, nothing you do on "
            "this path is sent to a model, and no share link is "
            "created."
        ),
        "title": TITLE,
        "dedication": DEDICATION,
        "telling": TELLING,
        "photo": PHOTO,
        "outline": {
            "title": TITLE,
            "dedication": DEDICATION,
            "sections": [
                {"heading": s["heading"],
                 "source_ids": [p["source_ids"][0]
                                for p in s["paragraphs"]
                                if p["source_ids"]]}
                for s in draft["sections"]
            ],
        },
        "draft": draft,
        "check": check,
        "planted_detail": "1968",
        "summary_line": SUMMARY_LINE,
        "steps": [
            {"id": "talk", "label": "Talk",
             "detail": "A preloaded, made-up exchange with Liv"},
            {"id": "plan", "label": "Chapter plan",
             "detail": "Title, dedication and sections proposed "
                       "before anything is written"},
            {"id": "draft", "label": "Draft",
             "detail": "Arranged from the sample telling"},
            {"id": "check", "label": "Source-check",
             "detail": "The draft is checked against the "
                       "telling's own words"},
            {"id": "approve", "label": "Approve",
             "detail": "In a real sitting, nothing is shared "
                       "until the storyteller approves"},
            {"id": "keepsake", "label": "Keepsake",
             "detail": "The approved sample chapter, as a "
                       "demo keepsake only"},
        ],
    }
