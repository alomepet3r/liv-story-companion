"""Development fallback companion.

Honest purpose: while the organizer-delivered Meta Model API credit is
still pending (generation calls return HTTP 402), the Day 1 shell must
still be talkable-to. This module provides warm, patient, rule-based
replies so the consent flow, the conversation UI, and the session shape
can be built and tested end to end. The moment the live model answers,
app.py uses the live model instead — this is scaffolding, not the
product's brain.

Stance — LISTENER FIRST (Persona Directive #1, Petro, Oct 26, 2026):
Petro's first feedback was that the companion felt like it was walking
him through telling his story. It must not. This companion is a great
listener: patient, curious about what the storyteller offers, and
boundaried. Concretely:
- No itinerary. Follow-ups grow only out of the storyteller's own
  words. A warm acknowledgement is a complete reply; at most ONE short
  question, never stacked.
- Guided themes are for those who need the walker: they are offered
  only after repeated stalls (very short or detail-free answers),
  framed as an open door the storyteller can ignore — never as the
  next item on a list.
- BOUNDARY LAW: if the storyteller sets a boundary ("I don't want to
  talk about X", "skip that", "not today"), acknowledge it warmly in
  one line, move on, and never return to that topic — not in follow-ups,
  not in callbacks, not via theme offers — for the rest of the session.
- Never invent facts about the storyteller. Only ask, listen, follow up.
- Meet tender topics plainly — no morbidity, no forced cheer.
"""
import re

# The companion has a name, chosen by the storyteller (Petro's decision,
# Oct 26, 2026): Livio, Livia, or Liv — Liv is the default.
COMPANION_NAMES = ("Livio", "Livia", "Liv")
DEFAULT_COMPANION_NAME = "Liv"


def normalize_companion_name(value):
    """Return the canonical companion name, or the default.

    Anything that is not one of the three offered names falls back to
    the default, so a session always carries a valid name.
    """
    if isinstance(value, str):
        candidate = value.strip()
        for name in COMPANION_NAMES:
            if candidate.lower() == name.lower():
                return name
    return DEFAULT_COMPANION_NAME


THEMES = [
    ("childhood", "your childhood — the place and people you grew up with"),
    ("family", "your family — the people who shaped who you are"),
    ("lessons learned", "a lesson life taught you that you would pass on"),
    ("love", "love — someone, or something, you have loved"),
    ("wishes", "a wish you hold for the people you love"),
]

_ACKS = [
    "Thank you for telling me that.",
    "I am glad you shared that.",
    "What a memory to hold on to.",
    "I can picture that as you tell it.",
]

# Acknowledgement-only replies — no question at all. Listening,
# complete as they are.
_ACK_ONLY = [
    "Mm. Thank you for telling me that.",
    "I hear you. Thank you for trusting me with that.",
    "What a thing to carry with you. Thank you for saying it out loud.",
]

_PLACE_PATTERNS = [
    (r"\bgrew up in ([A-Z][\w'’-]*(?: [A-Z][\w'’-]*){0,2})", "growing up in {0}"),
    (r"\bborn in ([A-Z][\w'’-]*(?: [A-Z][\w'’-]*){0,2})", "being born in {0}"),
    (r"\blived in ([A-Z][\w'’-]*(?: [A-Z][\w'’-]*){0,2})", "living in {0}"),
    (r"\bfrom ([A-Z][\w'’-]*(?: [A-Z][\w'’-]*){0,2})", "being from {0}"),
]

_PEOPLE_PATTERN = re.compile(
    r"\bmy (father|mother|grandfather|grandmother|grandpa|grandma|"
    r"brother|sister|uncle|aunt|husband|wife|son|daughter|friend)\b",
    re.IGNORECASE,
)

_OBJECT_WORDS = [
    "elevator", "house", "home", "farm", "school", "church", "river",
    "bicycle", "car", "train", "boat", "market", "village", "garden",
    "kitchen", "photo", "photograph", "letter", "book", "song",
]

_GRIEF_WORDS = [
    "died", "passed away", "funeral", "gone now", "miss him", "miss her",
    "miss them", "buried", "lost my", "lost his", "lost her",
]

_CLOSE_WORDS = [
    "finish", "goodbye", "bye", "that's all", "thats all", "i am done",
    "i'm done", "stop for today", "enough for today",
]

# --- Boundary signals -------------------------------------------------
# The storyteller closing a door. Matched on normalised text (curly
# apostrophes folded to straight). Order matters: check BEFORE detail
# extraction, so a boundary message never becomes a "detail" to follow
# up on later.
_BOUNDARY_PATTERNS = [
    r"don'?t want to talk about",
    r"do not want to talk about",
    r"don'?t want to discuss",
    r"do not want to discuss",
    r"rather not talk about",
    r"rather not discuss",
    r"not talk about",
    r"won'?t talk about",
    r"can'?t talk about",
    r"cannot talk about",
    r"don'?t ask (?:me )?about",
    r"do not ask (?:me )?about",
    r"never ask (?:me )?about",
    r"no more about",
    r"leave that (?:alone|be|there)",
    r"leave it (?:alone|there)",
    r"skip (?:that|this|it|the question)",
    r"not today",
    r"drop (?:that|it|the subject)",
]
_BOUNDARY_RE = re.compile("|".join("(?:%s)" % p for p in _BOUNDARY_PATTERNS))

# After "about X" — capture up to three topic words, stopping at
# punctuation or common glue.
_TOPIC_RE = re.compile(
    r"\babout\s+(?:my\s+|the\s+|that\s+)?"
    r"([a-z][a-z'’-]*(?:\s+[a-z][a-z'’-]*){0,2})"
)
_TOPIC_STOP = {
    "today", "now", "anymore", "any", "more", "right", "just", "please",
    "and", "or", "because", "so", "then",
}

_BOUNDARY_ACKS = [
    ("Of course — we won't go there. Thank you for saying so. "
     "Whenever you're ready, we can talk about whatever you'd like."),
    ("Of course. That's completely fine, and we won't go there. "
     "I'm here — we can talk about anything else, in your own time."),
]


def _normalise(text):
    return text.replace("’", "'").replace("‘", "'").lower()


def detect_boundary(text):
    """Return a list of blocked topic words if this message sets a
    boundary, else None.

    The topic is the noun phrase near the boundary when one is easily
    extractable ("my mother" -> "mother"); otherwise the list just
    holds a marker and the boundary itself is still honoured.
    """
    lowered = _normalise(text)
    if not _BOUNDARY_RE.search(lowered):
        return None
    topics = []
    m = _TOPIC_RE.search(lowered)
    if m:
        words = [w for w in m.group(1).replace("’", "'").split()
                 if w not in _TOPIC_STOP]
        if words:
            topics.append(words[0])
            if len(words) > 1:
                topics.append(" ".join(words))
    person = _PEOPLE_PATTERN.search(text)
    if person:
        topics.append(person.group(1).lower())
    return topics or ["(unspecified)"]


def _clean_place(raw):
    raw = raw.strip().rstrip(".,!?")
    # Drop trailing lowercase glue words the pattern may have caught.
    parts = raw.split()
    while parts and parts[-1].lower() in ("and", "the", "with", "when"):
        parts.pop()
    return " ".join(parts)


def extract_details(text):
    """Pull simple, storyteller-stated details out of one message.

    Only what the storyteller actually said — nothing inferred.
    Returns a list of short phrases like 'growing up in Bamenda'.
    """
    found = []
    for pattern, template in _PLACE_PATTERNS:
        m = re.search(pattern, text)
        if m:
            place = _clean_place(m.group(1))
            if place:
                found.append(template.format(place))
    m = _PEOPLE_PATTERN.search(text)
    if m:
        found.append("your " + m.group(1).lower())
    lowered = text.lower()
    for word in _OBJECT_WORDS:
        if re.search(r"\b" + word + r"\b", lowered):
            found.append("the " + word)
            break
    # De-duplicate, keep order.
    seen = set()
    out = []
    for item in found:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _ack(turn):
    return _ACKS[turn % len(_ACKS)]


class CannedCompanion:
    """One storyteller session, held in memory only."""

    def __init__(self, name=DEFAULT_COMPANION_NAME):
        self.name = normalize_companion_name(name)
        self.details = []          # phrases the storyteller stated, in order
        self.turn = 0              # storyteller turns answered
        self.theme_index = 0
        self.closed = False
        self.stalls = 0            # consecutive detail-free answers
        self.blocked_words = set() # boundary topics, lowercase words
        self.boundaries = 0        # how many boundaries have been set

    # -- boundary helpers ------------------------------------------------
    def _is_blocked(self, phrase):
        lowered = phrase.lower()
        return any(w in lowered for w in self.blocked_words)

    def _note_boundary(self, topics):
        self.boundaries += 1
        for topic in topics:
            for word in topic.split():
                self.blocked_words.add(word.lower())
        # A boundary reaches backwards too: a detail already gathered
        # about this topic is never followed up on again.
        self.details = [d for d in self.details if not self._is_blocked(d)]

    def greeting(self):
        # The first message introduces the companion by the chosen name
        # and makes boundaries easy from the very start.
        return ("Hello, I’m " + self.name + ". I’m here to listen — "
                "we can go at your pace. And we can skip anything — "
                "just say so. "
                "Tell me, where did you grow up?")

    def reply(self, text):
        text = (text or "").strip()
        self.turn += 1
        lowered = _normalise(text)

        if self.closed:
            return ("Of course. Whenever you are ready to talk again, "
                    "I will be here.")

        # Graceful close (persona: warm and complete).
        if any(w in lowered for w in _CLOSE_WORDS):
            self.closed = True
            return ("Thank you for sitting with me today. What you shared "
                    "matters. When you are ready, we can arrange today's "
                    "conversation into a chapter, and you will review it "
                    "first — nothing is shared unless you approve it. "
                    "Rest well, and come back any time. — " + self.name)

        # BOUNDARY LAW — checked before anything else in the message is
        # used. One warm line, a gentle pivot, and the topic is closed
        # for the rest of the session.
        topics = detect_boundary(text)
        if topics is not None:
            self._note_boundary(topics)
            self.stalls = 0
            return _BOUNDARY_ACKS[(self.boundaries - 1) % len(_BOUNDARY_ACKS)]

        # Silence / almost nothing said: patience, no pressure, no question
        # piled on top of another.
        if len(text) < 3:
            return "Take your time. I am here whenever you are ready."

        new_details = [d for d in extract_details(text)
                       if d not in self.details and not self._is_blocked(d)]
        self.details.extend(new_details)

        # Tender topics: plain, warm, unhurried. If the detail at hand
        # sits behind a boundary, be sorry without opening the door.
        if any(w in lowered for w in _GRIEF_WORDS):
            self.stalls = 0
            who = ""
            if new_details:
                who = new_details[0]
            elif self.details:
                who = self.details[0]
            if who.startswith("your "):
                return ("I am sorry. Losing someone we love stays with us. "
                        "Would you tell me a little about " + who +
                        " — what do you most want people to know?")
            return ("I am sorry. That cannot have been easy. "
                    "Would you like to tell me a little about them?")

        # Every third reply, reach back to an earlier detail (not the one
        # from this message) — the follow-up remembers. Never a detail
        # behind a boundary.
        earlier = [d for d in self.details
                   if d not in new_details and not self._is_blocked(d)]
        if self.turn % 3 == 0 and earlier:
            self.stalls = 0
            detail = earlier[0]
            return (_ack(self.turn) + " Earlier you mentioned " + detail +
                    ". What stayed with you from that?")

        # A fresh detail earns the follow-up — curiosity about the
        # storyteller's own words, one short question.
        if new_details:
            self.stalls = 0
            detail = new_details[0]
            return (_ack(self.turn) + " Tell me more about " + detail +
                    " — what do you remember most about it?")

        # Nothing new to follow. Count the stall. Listening does not
        # need a question every time: the first stall earns a plain,
        # warm acknowledgement and silence to think in.
        self.stalls += 1
        if self.stalls < 2:
            return _ACK_ONLY[self.turn % len(_ACK_ONLY)]

        # Only after repeated stalls may a theme be offered — as an
        # open door for those who want the walker, easy to ignore,
        # never a list to march through. A theme that would steer back
        # behind a boundary is skipped entirely.
        while self.theme_index < len(THEMES):
            _key, description = THEMES[self.theme_index]
            self.theme_index += 1
            if self._is_blocked(description):
                continue
            self.stalls = 0
            return ("We can go anywhere you'd like from here. Some "
                    "people enjoy talking about " + description +
                    " — and some would rather go somewhere else "
                    "entirely. What is on your mind?")
        return (_ack(self.turn) +
                " What else from that time would you like to tell me?")
