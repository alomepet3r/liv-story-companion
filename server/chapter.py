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


# ------------------------------------------------------------------
# Housekeeping turns (wart 3, Day 4): the conversation's plumbing
# is not story material. The answer to "what would you like me to
# call you?", a bare greeting, a decline of the name question, a
# closing phrase, a question TO Liv about the conversation — none
# of these are tellings, and none may enter a chapter's sources.
# Detection is deliberately narrow and shape-based (the same
# discipline as the companion's own name capture): a substantive
# telling that merely happens to be short ("It did not stay with
# me.") is never housekeeping.
# ------------------------------------------------------------------

_NAME_TOKEN = r"[A-Za-z][A-Za-z'’\-]*"
_DECLARATION_RE = re.compile(
    r"^(?:please\s+)?(?:call me|calls me|my name is|this is|"
    r"you can call me|i am|i'?m)\s+(?P<name>" + _NAME_TOKEN +
    r"(?:\s+" + _NAME_TOKEN + r")?)"
    r"(?:\s*,?\s*(?:please|thanks|thank you))?\s*[.!]?$",
    re.IGNORECASE)
_JUST_NAME_RE = re.compile(
    r"^just\s+(?:call me\s+)?(?P<name>" + _NAME_TOKEN +
    r"(?:\s+" + _NAME_TOKEN + r")?)\s*[.!]?$", re.IGNORECASE)
# Words that can never be a preferred name — sentence glue that
# follows "I'm …" / "call me …" in ordinary speech ("I'm from
# Bamenda", "call me back later"). Mirrors the companion's own
# name-capture stop list in canned.py.
_NAME_GLUE = {
    "from", "here", "there", "just", "not", "back", "later",
    "when", "if", "so", "very", "really", "fine", "okay", "ok",
    "ready", "telling", "going", "looking", "trying", "hoping",
    "glad", "happy", "sorry", "afraid", "sure", "name", "called",
    "a", "an", "the", "and", "but", "because", "today", "now",
    "please", "thanks", "thank", "you", "me", "my", "this",
    "that", "it", "is", "am", "are", "was", "were", "be", "been",
    "i", "we", "he", "she", "they", "in", "at", "on", "with",
    "for", "born", "breathe",
}
_DECLINE_RE = re.compile(
    r"^(?:no(?:\s+name)?|no thanks|i'?d rather not(?:\s+say)?|"
    r"rather not(?:\s+say)?|prefer not(?:\s+to say)?|"
    r"don'?t want to say|"
    r"do not want to say|not comfortable|skip(?:\s+it)?|pass)"
    r"(?:\s*,?\s*(?:please|thanks|thank you))?\s*[.!]?$",
    re.IGNORECASE)
_GREETING_RE = re.compile(
    r"^(?:hello|hi|hey|greetings|good morning|good afternoon|"
    r"good evening)(?:\s+(?:liv|livio|livia|there))?\s*[.!]?$",
    re.IGNORECASE)
_CLOSE_RE = re.compile(
    r"^(?:finish for today|that'?s all(?:\s+for today)?|"
    r"i'?m done(?:\s+for today)?|let'?s stop(?:\s+here)?|"
    r"we can stop(?:\s+here)?|goodbye|good night|bye)\s*[.!]?$",
    re.IGNORECASE)
_META_RE = re.compile(
    r"^(?:what do you think (?:about|of) (?:our|this) "
    r"conversation.*|are you listening.*|"
    r"what have we talked about.*|do you remember .*|"
    r"can you hear me.*)\?$", re.IGNORECASE)
_NOT_A_NAME = {
    "hello", "hi", "hey", "yes", "yeah", "no", "okay", "ok",
    "sure", "fine", "thanks", "thank", "ready", "begin", "start",
    "story", "none", "nothing", "skip", "pass", "well", "right",
    "good", "today", "tonight", "now", "please",
}


def _is_bare_name(text):
    """A whole turn that is only a name: one token in any case, or
    up to three tokens that are all capitalised name shapes. A
    short sentence ("Boxing saved me.") is not a name — its later
    words are not capitalised and it is never treated as one."""
    tokens = re.findall(r"[A-Za-z][A-Za-z'’\-]*", text)
    if not tokens or len(tokens) > 3:
        return False
    if any(t.lower() in _NOT_A_NAME for t in tokens):
        return False
    if len(tokens) == 1:
        return True
    return all(t[:1].isupper() for t in tokens)


def _is_declaration(text):
    """A pure name declaration ("Call me Margaret.", "I'm
    Margaret.", "Just Margaret.") whose name part is really a
    name — no sentence glue."""
    for pattern in (_DECLARATION_RE, _JUST_NAME_RE):
        match = pattern.match(text)
        if match:
            tokens = match.group("name").lower().split()
            if not any(t.strip("’'") in _NAME_GLUE for t in tokens):
                return True
    return False


def _is_housekeeping_sentence(text):
    """One sentence that is purely conversational plumbing: a
    name declaration or a bare greeting."""
    text = text.strip()
    return bool(_is_declaration(text) or _GREETING_RE.match(text))


def _is_housekeeping_turn(text, is_first):
    """A whole user turn that is housekeeping, not a telling.
    Bare names and declines only count at the conversation's
    opening, where they answer Liv's first question; the same
    shapes mid-story are the storyteller's business."""
    text = text.strip()
    if _is_housekeeping_sentence(text):
        return True
    if _CLOSE_RE.match(text) or _META_RE.match(text):
        return True
    if is_first and (_DECLINE_RE.match(text) or _is_bare_name(text)):
        return True
    return False


def _content_turn(text, is_first):
    """The chapter-worthy part of a user turn: "" when the turn
    is housekeeping, the turn minus a leading housekeeping
    sentence when a telling follows one ("Call me Petro. My dad
    had just passed…" keeps the telling), else the turn itself."""
    if _is_housekeeping_turn(text, is_first):
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text)
    if len(parts) > 1 and _is_housekeeping_sentence(parts[0]):
        rest = " ".join(parts[1:]).strip()
        if rest:
            return rest
    return text


# ------------------------------------------------------------------
# Labels (wart 1, Day 4): a material the storyteller cannot
# recognise cannot be knowingly included or excluded, so every
# material is labelled by its own opening — a telling by its
# first words, a media item by the most identifying detail it
# carries (caption, then date, then album, then share time).
# ------------------------------------------------------------------

def _excerpt(text, max_words=10):
    """The opening of a text, cut cleanly: at most max_words
    words, backing off to the last clause boundary in reach
    rather than chopping mid-phrase. An ellipsis appears only
    when text was actually left behind, at that clean cut."""
    text = " ".join((text or "").split())
    words = text.split()
    if len(words) <= max_words:
        return text
    cut = max_words
    for i in range(max_words, 5, -1):
        if words[i - 1].endswith((",", ";", ":")):
            cut = i
            break
    excerpt = " ".join(words[:cut]).rstrip(",;:.!?")
    return excerpt + "\u2026"


def _telling_label(text):
    return "\u201c" + _excerpt(text, 10) + "\u201d"


def _media_label(item):
    kind = item.get("kind", "photo")
    base = {"photo": "A photo", "audio": "A voice recording",
            "video": "A video"}.get(kind, "A photo")
    if item.get("source") == "archive":
        base += " from your archive"
        if item.get("caption"):
            return base + " — \u201c" + _excerpt(
                item["caption"], 6) + "\u201d"
        if item.get("date_str"):
            return base + ", dated " + item["date_str"]
        if item.get("album"):
            return base + ", from the album \u201c" + \
                item["album"] + "\u201d"
        return base
    label = base + " you shared"
    if item.get("caption"):
        return label + " — \u201c" + _excerpt(
            item["caption"], 6) + "\u201d"
    if item.get("shared_at"):
        return label + " · " + item["shared_at"]
    return label


def gather_sources(sess):
    """The session's chapter materials, in telling order.

    Conversation turns (the storyteller's own words, minus
    housekeeping turns) first, then the media they shared in this
    session — including archive photos they explicitly selected,
    whose captions are their own words from the time of the photo.
    """
    sources = []
    n = 0
    told = []           # the storyteller's typed/spoken turn texts
    seen_turn = False
    for turn in sess.get("history", []):
        if turn.get("role") != "user":
            continue
        text = _clean_turn(turn.get("content"))
        if not text:
            continue
        is_first = not seen_turn
        seen_turn = True
        text = _content_turn(text, is_first)
        if not text:
            continue
        n += 1
        told.append(text)
        sources.append({
            "id": "s%d" % n,
            "kind": "words",
            "label": _telling_label(text),
            "text": text,
            "media_id": None,
        })
    told_joined = "\n".join(told)
    for media_id, item in sess.get("media", {}).items():
        n += 1
        kind = item.get("kind", "photo")
        label = _media_label(item)
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
                      else "a video") + ": \u201c" +
                     _excerpt(transcript, 8) + "\u201d")
        sources.append({
            "id": "s%d" % n,
            "kind": kind,
            "label": label,
            "text": text,
            "media_id": media_id,
        })
    # No two materials whose content differs may share a label:
    # a repeated label earns an honest distinguishing number.
    seen_labels = {}
    for src in sources:
        label = src["label"]
        if label in seen_labels:
            seen_labels[label] += 1
            src["label"] = "%s (%d)" % (label, seen_labels[label])
        else:
            seen_labels[label] = 1
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


_TITLE_DANGLING = {
    "in", "on", "at", "the", "a", "an", "and", "but", "or", "of",
    "to", "with", "from", "by", "for", "was", "is", "it", "i",
    "my", "his", "her", "their", "our", "your", "when", "then",
}


def _title_from_sentence(sentence):
    """A title from one sentence, or None. A short complete
    sentence may stand whole; a long one is cut only at a clause
    boundary (comma, semicolon, colon, dash, or a conjunction)
    that leaves a phrase of 4–9 words not ending on a dangling
    word. A sentence that offers neither is not a title — the
    caller moves on rather than chopping it mid-thought."""
    sentence = sentence.strip().strip("\u201c\u201d\"' ")
    words = sentence.split()
    if len(words) < 2:
        return None
    if len(words) <= 8:
        title = sentence.rstrip(".!?").strip()
        return title or None
    for cut in range(4, 10):
        token = words[cut - 1].strip(",;:").lower()
        raw = words[cut - 1]
        following = words[cut].strip(",;:").lower() \
            if cut < len(words) else ""
        boundary = raw.endswith((",", ";", ":")) \
            or raw in ("\u2014", "-") \
            or following in ("and", "but")
        if boundary and token not in _TITLE_DANGLING:
            title = " ".join(words[:cut]).rstrip(",;:.!?-").strip()
            if title:
                return title
    return None


def suggest_title(sources):
    """A title grown from the storyteller's own words — a
    complete short sentence, or a clean clause of a longer one,
    taken from the tellings in the order they were told (wart 2,
    Day 4). Never a truncated fragment: when no telling offers a
    clean derivation, the honest fallback is offered instead and
    the naming is left to the storyteller."""
    words = [s for s in sources if s["kind"] == "words" and s["text"]]
    if not words:
        return "A chapter from our conversation"
    for src in words:
        sentences = re.split(r"(?<=[.!?])\s+", src["text"])
        for sentence in sentences[:3]:
            title = _title_from_sentence(sentence)
            if title:
                return title
    return "Untitled \u2014 yours to name"


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
    "Thank", "Chapter", "I", "Liv",
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
            "illustration": bool(chapter.get("illustration")),
            "illustration_version":
                chapter.get("illustration_version", 0),
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
        "illustration": False,
        "illustration_version": 0,
    }
    return 200, chapter_view(chapter)


# ------------------------------------------------------------------
# Keepsake illustration (Day 5) — the third Meta model enters the
# product. After approval, the storyteller may ask for ONE
# illustration for the keepsake (asking again replaces it). The
# image prompt is built ONLY from the approved chapter's own
# furniture — title, dedication, section headings — never from
# raw conversation text. The no-people / no-faces / no-likeness /
# no-text discipline (white-paper red team) is baked into the
# prompt template itself, so no caller can ask around it. The
# image lives in the chapter's in-memory state and is mirrored
# into the share snapshot as a flag, exactly as long-lived as the
# keepsake itself: it dies with the container, and the share
# link's illustration dies with the link. No prompt or image is
# ever logged here.
# ------------------------------------------------------------------

ILLUSTRATION_ALT = "An illustration made for this chapter"

ILLUSTRATION_FAILURE = (
    "The illustration didn't come through — your chapter is "
    "complete without it.")

_ILLUSTRATION_PROMPT = (
    "A warm, painterly editorial illustration for a personal "
    "keepsake chapter — soft natural light, gentle colours, the "
    "feel of a treasured book plate.\n"
    "The chapter is titled \u201c{title}\u201d.\n"
    "{dedication}"
    "Its sections are: {headings}.\n"
    "Illustrate the PLACES, OBJECTS and MOODS these themes "
    "suggest — a room, a landscape, the tools of a trade, "
    "weather, dawn or dusk — in the spirit of the title and the "
    "sections.\n"
    "Rules without exception: NO people, NO faces, NO human "
    "figures or silhouettes, NO likeness of any real person, "
    "and NO words, letters, numbers or text of any kind "
    "anywhere in the image."
)


def build_illustration_prompt(chapter):
    """The image prompt, from the approved draft's furniture
    only: its title, its dedication, its section headings."""
    draft = chapter["draft"]
    dedication = ""
    if draft.get("dedication"):
        dedication = ("It is dedicated to \u201c%s\u201d.\n"
                      % draft["dedication"])
    headings = "; ".join(section["heading"]
                         for section in draft["sections"])
    return _ILLUSTRATION_PROMPT.format(
        title=draft["title"], dedication=dedication,
        headings=headings or "Your words")


def illustrate(sess, session_id, generator):
    """Make (or replace) the keepsake's illustration. `generator`
    is a callable (prompt) -> (image_bytes, content_type) | None
    — the live Muse Image path in app.py; tests inject fakes.
    Any failure leaves the approved chapter exactly as it was
    and answers with the honest line."""
    chapter = sess.get("chapter")
    if chapter is None or chapter.get("stage") != "approved" \
            or not chapter.get("draft"):
        return 409, {"error": "There is no approved chapter to "
                              "illustrate just now — approve a "
                              "chapter first, and Liv can make an "
                              "illustration for it."}
    if generator is None:
        return 502, {"error": ILLUSTRATION_FAILURE}
    try:
        result = generator(build_illustration_prompt(chapter))
    except Exception:
        result = None
    if not result:
        return 502, {"error": ILLUSTRATION_FAILURE}
    data, content_type = result
    if not data:
        return 502, {"error": ILLUSTRATION_FAILURE}
    replacing = bool(chapter.get("illustration"))
    version = chapter.get("illustration_version", 0) + 1
    chapter["illustration"] = {"data": data,
                               "content_type": content_type}
    chapter["illustration_version"] = version
    _step(chapter, "illustrate", "Made an illustration for the "
          "keepsake",
          "Painted from the chapter's title and sections — "
          "places and things, never people"
          if not replacing else
          "A new one, replacing the earlier illustration")
    snapshot = _shares.get(chapter.get("share_token") or "")
    if snapshot is not None:
        snapshot["illustration"] = True
        snapshot["illustration_version"] = version
    return 200, chapter_view(chapter)


def get_illustration(sess):
    """The session's chapter illustration, if one was made:
    {"data": bytes, "content_type": str} — else None."""
    chapter = sess.get("chapter") if sess else None
    if not chapter:
        return None
    return chapter.get("illustration")


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
    if snapshot.get("illustration"):
        parts.append(
            "<img src=\"/api/chapter/illustration?session_id="
            + esc(snapshot["session_id"]) + "&v="
            + str(snapshot.get("illustration_version", 1))
            + "\" alt=\"" + ILLUSTRATION_ALT + "\">\n")
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
