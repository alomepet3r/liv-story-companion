"""Chapter slice — talk -> chapter -> keepsake (Day 4, pulled
forward to Day 2 under the skunkworks freeze + Petro's order to
incorporate the Oct 27 Agents-101 workshop value-adds).

The five workshop principles, as built here:

1. SHOW THE WORK — every stage records step events that correspond
   to REAL operations performed in this module (gather the session's
   materials, propose an outline, re-plan, write the draft, check
   the draft, storyteller approval). The UI renders exactly the
   steps the server returns; nothing is staged for show.
2. CHECKLIST + EVIDENCE RECORD — the chapter carries a checklist
   whose states are derived from what has actually happened, and
   an evidence record linking each draft paragraph to the source
   (a conversation turn, a caption) it was arranged from.
3. UNVERIFIED UNTIL APPROVED — a draft is born "unverified"; only
   the storyteller's approval flips it, and the single share link
   exists only after approval. Before a draft is presented, a
   local source-check looks for names, dates and places in the
   draft that do NOT appear in the storyteller's own words and
   flags them for the storyteller to check. This is a grounding
   check on the arrangement — it makes no claim about the chapter
   beyond "arranged from your conversation, checked against your
   words", which is the sanctioned wording everywhere.
4. PLAN BEFORE WRITE — outline first (title, dedication, which
   materials go in); the storyteller may edit the dedication or
   title, exclude materials, and ask for a re-plan; drafting is a
   separate, later step that only runs on an approved outline.
5. GROUNDING DISCIPLINE — the live arrangement prompt instructs
   the model to use only this session's sources, to anchor each
   paragraph to its source labels, and to leave out anything it is
   unsure of. The canned path arranges deterministically from the
   transcript under the same scaffolding, and the SAME source-check
   runs on both paths.

State is per-session in-memory, like the rest of the demo: a
chapter dies with its session's container. The share-token map is
likewise in-memory (see approve()) — the known multi-container
caveat applies to chapters exactly as it does to sessions; the
deploy keeps one warm container for the event window.

Stdlib only. No storyteller content is ever logged here.
"""
import html
import re
import secrets

# ------------------------------------------------------------------
# Sources
# ------------------------------------------------------------------

_BRACKET_NOTE_RE = re.compile(r"\s*\[[^\]]*\]")


def _clean_turn(text):
    """A history user-turn minus the server's bracket annotations
    (media notes) — what the storyteller actually said."""
    return _BRACKET_NOTE_RE.sub("", text or "").strip()


def gather_sources(sess):
    """The session's chapter materials, in telling order.

    Conversation turns (the storyteller's own words) first, then
    the media they shared in this session — including archive
    photos they explicitly selected, whose captions are their own
    words from the time of the photo.
    """
    sources = []
    n = 0
    told = []           # the storyteller's typed/spoken turn texts
    for turn in sess.get("history", []):
        if turn.get("role") != "user":
            continue
        text = _clean_turn(turn.get("content"))
        if not text:
            continue
        n += 1
        told.append(text)
        sources.append({
            "id": "s%d" % n,
            "kind": "words",
            "label": "Something you told Liv",
            "text": text,
            "media_id": None,
        })
    told_joined = "\n".join(told)
    for media_id, item in sess.get("media", {}).items():
        n += 1
        kind = item.get("kind", "photo")
        if item.get("source") == "archive":
            label = "A photo from your archive"
            if item.get("date_str"):
                label += ", dated " + item["date_str"]
            if item.get("caption"):
                label += " — \u201c" + item["caption"] + "\u201d"
        elif kind == "photo":
            label = "A photo you shared"
        elif kind == "audio":
            label = "A voice recording you shared"
        else:
            label = "A video you shared"
        text = item.get("caption") or ""
        # Day 3: a transcript IS a telling. When a recording's
        # words already ride in the conversation turns above (they
        # do — app.py writes them into the turn), the media source
        # must not double them; when they somehow did not (a
        # recording shared but never sent with a message), the
        # transcript is this source's text, so a spoken story can
        # still become a chapter. Either way it joins the
        # source-check corpus through the sources list.
        transcript = (item.get("transcript") or "").strip()
        if transcript and transcript not in told_joined:
            text = transcript
            label = ("Words you spoke in " +
                     ("a recording" if kind == "audio"
                      else "a video") + " you shared")
        sources.append({
            "id": "s%d" % n,
            "kind": kind,
            "label": label,
            "text": text,
            "media_id": media_id,
        })
    return sources


def story_word_count(sources):
    return sum(len(s["text"].split()) for s in sources
               if s["kind"] == "words")


# ------------------------------------------------------------------
# Outline (plan before write)
# ------------------------------------------------------------------

_SECTION_HEADINGS = {
    1: ["Your words"],
    2: ["The beginning", "Where it rests"],
    3: ["The beginning", "The heart of it", "Where it rests"],
}


def suggest_title(sources):
    """A title grown from the storyteller's own longest telling —
    the first words of its first sentence, offered as a suggestion
    they can change."""
    words = [s for s in sources if s["kind"] == "words" and s["text"]]
    if not words:
        return "A chapter from our conversation"
    longest = max(words, key=lambda s: len(s["text"]))
    first = re.split(r"(?<=[.!?])\s+", longest["text"])[0].strip()
    tokens = first.split()
    if len(tokens) > 7:
        first = " ".join(tokens[:7]) + "\u2026"
    return first or "A chapter from our conversation"


def build_outline(sources, excluded=()):
    """Group the included word-sources under simple headings and
    list every included material. Deterministic — the outline is a
    plan, not prose, so it never needs a model."""
    excluded = set(excluded)
    included = [s for s in sources if s["id"] not in excluded]
    word_ids = [s["id"] for s in included if s["kind"] == "words"]
    if len(word_ids) <= 1:
        groups = [word_ids] if word_ids else []
    elif len(word_ids) == 2:
        groups = [[word_ids[0]], [word_ids[1]]]
    else:
        groups = [[word_ids[0]], word_ids[1:-1], [word_ids[-1]]]
    headings = _SECTION_HEADINGS.get(len(groups), _SECTION_HEADINGS[3])
    sections = [{"heading": headings[i], "source_ids": group}
                for i, group in enumerate(groups)]
    return {
        "title": suggest_title(included),
        "dedication": "",
        "materials": [{"id": s["id"], "kind": s["kind"],
                       "label": s["label"]} for s in included],
        "sections": sections,
    }


# ------------------------------------------------------------------
# Drafting
# ------------------------------------------------------------------

def canned_draft(sources_by_id, outline):
    """Deterministic arrangement: the storyteller's own tellings,
    in order, under the outline's headings. Media shared in the
    session is kept with the chapter as a closing gallery."""
    sections = []
    for spec in outline["sections"]:
        paragraphs = []
        for sid in spec["source_ids"]:
            src = sources_by_id.get(sid)
            if src and src["text"]:
                paragraphs.append({"text": src["text"],
                                   "source_ids": [sid]})
        sections.append({"heading": spec["heading"],
                         "paragraphs": paragraphs, "media_ids": []})
    media_ids = [sources_by_id[m["id"]]["media_id"]
                 for m in outline["materials"]
                 if sources_by_id.get(m["id"], {}).get("media_id")]
    if media_ids:
        if not sections:
            sections.append({"heading": "Your words", "paragraphs": [],
                             "media_ids": []})
        sections[-1]["media_ids"] = media_ids
    return {"title": outline["title"],
            "dedication": outline["dedication"],
            "mode": "canned", "sections": sections}


_ARRANGEMENT_INSTRUCTIONS = (
    "You are arranging one storyteller's conversation into a "
    "chapter they will review. Follow these rules without "
    "exception:\n"
    "- Use ONLY the material in the sources below. Invent nothing: "
    "no new names, dates, places, events, or details of any kind.\n"
    "- If you are unsure whether something is in the sources, "
    "leave it out.\n"
    "- Keep the storyteller's own meaning and order. You may "
    "arrange their words under the section headings; do not add "
    "commentary, lessons, or colour of your own.\n"
    "- End every paragraph with the label(s) of the source(s) it "
    "is arranged from, like [S2] or [S1, S3].\n"
    "- Answer in exactly this shape, and nothing else:\n"
    "SECTION: <heading>\n"
    "<paragraph> [S#]\n"
    "<paragraph> [S#]\n"
    "SECTION: <next heading>\n"
    "<paragraph> [S#]"
)


def build_arrangement_messages(sources, outline, companion_name="Liv"):
    """The live drafting call's messages (principle 5). Sources
    are labelled S1..Sn to match the storyteller-facing s1..sn."""
    lines = [_ARRANGEMENT_INSTRUCTIONS, "", "The chapter outline:"]
    for spec in outline["sections"]:
        lines.append("- " + spec["heading"])
    if outline.get("dedication"):
        lines.append("The chapter is for: " + outline["dedication"])
    lines.append("")
    lines.append("The sources — everything you may use:")
    by_id = {s["id"]: s for s in sources}
    for spec in outline["sections"]:
        for sid in spec["source_ids"]:
            src = by_id.get(sid)
            if src and src["text"]:
                lines.append("[%s] %s" % (sid.upper(), src["text"]))
    for mat in outline["materials"]:
        src = by_id.get(mat["id"])
        if src and src["kind"] != "words":
            note = "[%s] (%s)" % (mat["id"].upper(), mat["label"])
            if src["text"]:
                note += " Its caption, in the storyteller's words: " \
                        + src["text"]
            lines.append(note)
    return [
        {"role": "system",
         "content": "You are " + companion_name + ", arranging a "
                    "storyteller's conversation into a chapter for "
                    "their review. Nothing is shared unless the "
                    "storyteller approves it."},
        {"role": "user", "content": "\n".join(lines)},
    ]


_LABEL_TAIL_RE = re.compile(r"\s*\[([Ss]\d+(?:\s*,\s*[Ss]\d+)*)\]\s*$")


def parse_live_draft(text, sources, outline):
    """Parse the model's SECTION-shaped answer into a draft.
    Returns None if the shape is not there — the caller then falls
    back to the deterministic arrangement."""
    if not text:
        return None
    by_label = {s["id"].upper(): s["id"] for s in sources}
    sections = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("SECTION:"):
            current = {"heading": line.split(":", 1)[1].strip()
                       or "Your words",
                       "paragraphs": [], "media_ids": []}
            sections.append(current)
            continue
        if current is None:
            continue
        source_ids = []
        match = _LABEL_TAIL_RE.search(line)
        if match:
            for label in match.group(1).split(","):
                sid = by_label.get(label.strip().upper())
                if sid:
                    source_ids.append(sid)
            line = _LABEL_TAIL_RE.sub("", line).strip()
        if line:
            current["paragraphs"].append({"text": line,
                                          "source_ids": source_ids})
    sections = [s for s in sections if s["paragraphs"]]
    if not sections:
        return None
    by_id = {s["id"]: s for s in sources}
    media_ids = [m["id"] for m in outline["materials"]
                 if by_id.get(m["id"], {}).get("media_id")]
    media_ids = [by_id[m]["media_id"] for m in media_ids]
    if media_ids:
        sections[-1]["media_ids"] = media_ids
    return {"title": outline["title"],
            "dedication": outline["dedication"],
            "mode": "live", "sections": sections}


# ------------------------------------------------------------------
# Source-check (principle 3) — local string work, no model calls.
# ------------------------------------------------------------------

_MONTHS = ("January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November",
           "December")
_MONTH_ALT = "|".join(_MONTHS)
_DATE_RES = [
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:%s)\s+"
               r"\d{4}\b" % _MONTH_ALT),
    re.compile(r"\b(?:%s)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b"
               % _MONTH_ALT),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
]
_YEAR_RE = re.compile(r"\b(?:1[5-9]\d\d|20\d\d)\b")
_PHRASE_RE = re.compile(r"\b(?:[A-Z][a-z]+\s+){0,2}[A-Z][a-z]+\b")
_STOP_WORDS = {
    "The", "A", "An", "And", "But", "When", "Then", "So", "He",
    "She", "It", "We", "They", "My", "His", "Her", "This", "That",
    "There", "Here", "Now", "After", "Before", "For", "In", "On",
    "At", "To", "With", "From", "One", "Every", "What", "Who",
    "If", "As", "By", "You", "Your", "Our", "Their", "Tell",
    "Thank", "Chapter", "I", "Liv", "Livio", "Livia",
} | set(_MONTHS)


def _corpus(sources, extra_texts=()):
    parts = [s["text"] for s in sources if s.get("text")]
    parts.extend(t for t in extra_texts if t)
    return " ".join(parts).lower()


def _grounded(candidate, corpus):
    lowered = candidate.lower()
    if lowered in corpus:
        return True
    words = [w for w in lowered.split() if len(w) > 2]
    return bool(words) and all(w in corpus for w in words)


def source_check(draft, sources):
    """Names, dates and places in the draft that do NOT appear in
    the storyteller's own words (their tellings + captions + the
    dedication they typed). Returns {"checked": n, "flags": [...]}.
    A flag means "please check this" — never an accusation."""
    corpus = _corpus(sources, [draft.get("dedication", "")])
    found = []          # (text, kind) in draft order
    seen = set()

    def note(text, kind):
        key = text.lower()
        if key not in seen:
            seen.add(key)
            found.append((text, kind))

    for section in draft["sections"]:
        for para in section["paragraphs"]:
            text = para["text"]
            spans = []
            for pattern in _DATE_RES:
                for match in pattern.finditer(text):
                    spans.append(match.span())
                    note(match.group(0), "date")
            for match in _YEAR_RE.finditer(text):
                if any(a <= match.start() < b for a, b in spans):
                    continue  # already inside a full date
                note(match.group(0), "date")
            for match in _PHRASE_RE.finditer(text):
                phrase = match.group(0).strip()
                words = phrase.split()
                if words[0] in _STOP_WORDS:
                    if len(words) == 1:
                        continue
                    phrase = " ".join(words[1:])
                    if phrase.split()[0] in _STOP_WORDS:
                        continue
                if len(phrase) < 3:
                    continue
                note(phrase, "name or place")
    checked = len(seen)
    flags = [{"text": text, "kind": kind} for text, kind in found
             if not _grounded(text, corpus)]
    return {"checked": checked, "flags": flags}


# ------------------------------------------------------------------
# Chapter state + flow operations
# ------------------------------------------------------------------

_CHECKLIST = [
    ("materials", "Materials gathered"),
    ("outline", "Outline proposed"),
    ("outline_ok", "Outline approved by you"),
    ("draft", "Draft written"),
    ("check", "Checked against your words"),
    ("approved", "Approved by you"),
]


def _step(chapter, step_id, label, detail):
    chapter["steps"].append({
        "id": step_id, "label": label, "detail": detail,
        "n": len(chapter["steps"]) + 1,
    })


def _checklist(chapter):
    done = {
        "materials": chapter is not None,
        "outline": bool(chapter and chapter.get("outline")),
        "outline_ok": bool(chapter and chapter.get("outline_approved")),
        "draft": bool(chapter and chapter.get("draft")),
        "check": bool(chapter and chapter.get("check")),
        "approved": bool(chapter and chapter.get("stage") == "approved"),
    }
    return [{"id": key, "label": label, "done": done[key]}
            for key, label in _CHECKLIST]


def chapter_view(chapter):
    """Everything the UI renders — steps, checklist, outline,
    draft, flags, evidence, share link (only once approved)."""
    if chapter is None:
        return {"chapter": None, "checklist": _checklist(None),
                "steps": []}
    sources_by_id = {s["id"]: s for s in chapter["sources"]}
    evidence = []
    draft = chapter.get("draft")
    if draft:
        for si, section in enumerate(draft["sections"]):
            for para in section["paragraphs"]:
                evidence.append({
                    "section": si,
                    "text_start": para["text"][:80],
                    "sources": [
                        {"id": sid,
                         "label": sources_by_id[sid]["label"]}
                        for sid in para["source_ids"]
                        if sid in sources_by_id
                    ],
                })
            for media_id in section["media_ids"]:
                label = next(
                    (s["label"] for s in chapter["sources"]
                     if s.get("media_id") == media_id), "A photo")
                evidence.append({"section": si, "text_start": "",
                                 "sources": [{"id": media_id,
                                              "label": label}]})
    return {
        "chapter": {
            "stage": chapter["stage"],
            "outline": chapter["outline"],
            "draft": draft,
            "check": chapter.get("check"),
            "excluded": sorted(chapter["excluded"]),
            "materials_all": [
                {"id": s["id"], "kind": s["kind"], "label": s["label"],
                 "included": s["id"] not in chapter["excluded"]}
                for s in chapter["sources"]
            ],
        },
        "checklist": _checklist(chapter),
        "steps": chapter["steps"],
        "evidence": evidence,
        "share_url": ("/keepsake/" + chapter["share_token"]
                      if chapter.get("share_token") else None),
    }


def _materials_detail(sources):
    words = sum(1 for s in sources if s["kind"] == "words")
    media = len(sources) - words
    parts = []
    if words:
        parts.append("%d thing%s you told Liv"
                     % (words, "" if words == 1 else "s"))
    if media:
        parts.append("%d thing%s you shared"
                     % (media, "" if media == 1 else "s"))
    return " · ".join(parts) or "nothing yet"


def start_outline(sess):
    """Gather + propose. Returns (status, view_or_error)."""
    sources = gather_sources(sess)
    if story_word_count(sources) == 0:
        return 400, {"error": "Tell Liv a little of your story "
                              "first — then we can arrange it into "
                              "a chapter together."}
    chapter = {
        "stage": "outline",
        "sources": sources,
        "excluded": set(),
        "outline": build_outline(sources),
        "outline_approved": False,
        "draft": None,
        "check": None,
        "steps": [],
        "share_token": None,
    }
    _step(chapter, "gather", "Gathered what you shared",
          _materials_detail(sources))
    _step(chapter, "plan", "Proposed an outline",
          "%d section%s under the title \u201c%s\u201d"
          % (len(chapter["outline"]["sections"]),
             "" if len(chapter["outline"]["sections"]) == 1 else "s",
             chapter["outline"]["title"]))
    sess["chapter"] = chapter
    return 200, chapter_view(chapter)


def replan(sess, title=None, dedication=None, exclude_ids=None):
    """Apply the storyteller's changes and re-propose the outline.
    Only while the chapter is still at the outline stage."""
    chapter = sess.get("chapter")
    if chapter is None or chapter["stage"] != "outline":
        return 400, {"error": "There is no outline to change just "
                              "now — ask Liv to propose one first."}
    if isinstance(exclude_ids, list):
        chapter["excluded"] = {str(x) for x in exclude_ids}
    chapter["outline"] = build_outline(chapter["sources"],
                                       chapter["excluded"])
    if title is not None and str(title).strip():
        chapter["outline"]["title"] = str(title).strip()[:120]
    if dedication is not None:
        chapter["outline"]["dedication"] = str(dedication).strip()[:120]
    kept = chapter["outline"]
    _step(chapter, "replan", "Re-planned the outline",
          "Now %d section%s, with %d material%s"
          % (len(kept["sections"]),
             "" if len(kept["sections"]) == 1 else "s",
             len(kept["materials"]),
             "" if len(kept["materials"]) == 1 else "s"))
    return 200, chapter_view(chapter)


def make_draft(sess, drafter=None):
    """Approve-the-outline + write + check, as one honest sequence
    of real operations. `drafter` is an optional callable
    (sources, outline) -> draft|None for the live model path; any
    failure or empty result falls back to the deterministic
    arrangement, and the mode is recorded on the draft."""
    chapter = sess.get("chapter")
    if chapter is None or chapter["stage"] != "outline":
        return 400, {"error": "There is no approved outline to "
                              "write from just now."}
    chapter["outline_approved"] = True
    included = [s for s in chapter["sources"]
                if s["id"] not in chapter["excluded"]]
    draft = None
    if drafter is not None:
        try:
            draft = drafter(included, chapter["outline"])
        except Exception:
            draft = None
    if draft is None:
        by_id = {s["id"]: s for s in included}
        draft = canned_draft(by_id, chapter["outline"])
    chapter["draft"] = draft
    _step(chapter, "draft", "Wrote the draft chapter",
          "Arranged from %d source%s"
          % (len(included), "" if len(included) == 1 else "s"))
    chapter["check"] = source_check(draft, included)
    flags = chapter["check"]["flags"]
    _step(chapter, "check", "Checked it against your words",
          ("%d names, dates and places checked — all found in "
           "your words" % chapter["check"]["checked"])
          if not flags else
          ("%d names, dates and places checked — %d to look at "
           "together"
           % (chapter["check"]["checked"], len(flags))))
    chapter["stage"] = "review"
    return 200, chapter_view(chapter)


# ------------------------------------------------------------------
# Approval + the one share link
# ------------------------------------------------------------------

# token -> approved keepsake snapshot. In-memory, like sessions:
# a share link lives exactly as long as the container that served
# the approval (the deploy keeps one warm container for the event
# window). Nothing is in this map before approval — that is the
# point of it.
_shares = {}


def approve(sess, session_id):
    """The storyteller's approval: the ONLY door to a share link."""
    chapter = sess.get("chapter")
    if chapter is None or chapter["stage"] != "review" \
            or not chapter.get("draft"):
        return 400, {"error": "There is no draft waiting for your "
                              "approval just now."}
    chapter["stage"] = "approved"
    _step(chapter, "approve", "You approved this chapter",
          "It is now your keepsake — the link below is the only "
          "way in")
    token = secrets.token_urlsafe(18)
    chapter["share_token"] = token
    draft = chapter["draft"]
    _shares[token] = {
        "title": draft["title"],
        "dedication": draft["dedication"],
        "sections": draft["sections"],
        "session_id": session_id,
    }
    return 200, chapter_view(chapter)


def get_share(token):
    return _shares.get(str(token))


def drop_shares_for_session(session_id):
    """End-of-session eviction (Day 4 truth pass): remove every
    keepsake snapshot minted by a session, so its share links die
    with it. Returns how many were dropped."""
    doomed = [token for token, snap in _shares.items()
              if snap.get("session_id") == session_id]
    for token in doomed:
        del _shares[token]
    return len(doomed)


def render_keepsake_html(snapshot):
    """The shareable keepsake page: the approved chapter only,
    read-only, no controls, nothing unapproved reachable."""
    def esc(text):
        return html.escape(text or "", quote=True)

    parts = [
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, "
        "initial-scale=1\">\n"
        "<title>" + esc(snapshot["title"]) + "</title>\n"
        "<style>"
        "body{margin:0;background:#FBF7EF;color:#2B2622;"
        "font-family:Georgia,serif;font-size:19px;line-height:1.65}"
        "main{max-width:42rem;margin:0 auto;padding:3rem 1.25rem 4rem}"
        "h1{font-size:2.2rem;line-height:1.2;margin:0 0 .5rem}"
        "h2{font-size:1.5rem;margin:2.2rem 0 .6rem}"
        ".for{font-style:italic;font-size:1.25rem;margin:0 0 1rem}"
        ".note{color:rgba(43,38,34,.78);font-size:1rem}"
        "img{max-width:100%;border-radius:10px;margin:.6rem 0}"
        "hr{border:none;border-top:1px solid rgba(43,38,34,.25);"
        "margin:2rem 0}"
        "</style>\n</head>\n<body>\n<main>\n",
        "<h1>" + esc(snapshot["title"]) + "</h1>\n",
    ]
    if snapshot.get("dedication"):
        parts.append("<p class=\"for\">For "
                     + esc(snapshot["dedication"]) + "</p>\n")
    parts.append("<p class=\"note\">Arranged from a conversation "
                 "with Liv, and approved by the storyteller before "
                 "it was shared.</p>\n<hr>\n")
    for section in snapshot["sections"]:
        parts.append("<h2>" + esc(section["heading"]) + "</h2>\n")
        for para in section["paragraphs"]:
            parts.append("<p>" + esc(para["text"]) + "</p>\n")
        for media_id in section["media_ids"]:
            parts.append(
                "<img src=\"/api/media/" + esc(media_id)
                + "?session_id=" + esc(snapshot["session_id"])
                + "\" alt=\"A photo kept with this chapter\">\n")
    parts.append("</main>\n</body>\n</html>")
    return "".join(parts)
