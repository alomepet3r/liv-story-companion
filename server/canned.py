"""Development fallback companion.

Honest purpose: while the organizer-delivered Meta Model API credit is
still pending (generation calls return HTTP 402), the Day 1 shell must
still be talkable-to. This module provides warm, patient, rule-based
replies so the consent flow, the conversation UI, and the session shape
can be built and tested end to end. The moment the live model answers,
app.py uses the live model instead — this is scaffolding, not the
product's brain.

Conduct rules (shared with the live system prompt in app.py):
- Never invent facts about the storyteller. Only ask, listen, follow up.
- One short follow-up question at a time. Never rush.
- Reference details the storyteller mentioned earlier in this session.
- Offer the guided themes gently, one at a time, storyteller's choice.
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
    ("family", "your family — someone who shaped who you are"),
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

    def greeting(self):
        # The first message introduces the companion by the chosen name.
        return ("Hello, I’m " + self.name + ". I’m here to listen — "
                "we can go at your pace. "
                "Tell me, where did you grow up?")

    def reply(self, text):
        text = (text or "").strip()
        self.turn += 1
        lowered = text.lower()

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

        # Silence / almost nothing said: patience, no pressure, no question
        # piled on top of another.
        if len(text) < 3:
            return "Take your time. I am here whenever you are ready."

        new_details = [d for d in extract_details(text)
                       if d not in self.details]
        self.details.extend(new_details)

        # Tender topics: plain, warm, unhurried.
        if any(w in lowered for w in _GRIEF_WORDS):
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
        # from this message) — the follow-up remembers.
        earlier = [d for d in self.details if d not in new_details]
        if self.turn % 3 == 0 and earlier:
            detail = earlier[0]
            return (_ack(self.turn) + " Earlier you mentioned " + detail +
                    ". What stayed with you from that?")

        # A fresh detail earns the follow-up.
        if new_details:
            detail = new_details[0]
            return (_ack(self.turn) + " Tell me more about " + detail +
                    " — what do you remember most about it?")

        # Nothing new to follow: gently offer the next guided theme,
        # one at a time, always the storyteller's choice.
        if self.theme_index < len(THEMES):
            _name, description = THEMES[self.theme_index]
            self.theme_index += 1
            return ("Thank you. If you like, we could turn to " +
                    description + ". Or we can stay right where we are — "
                    "what would you like to talk about?")
        return (_ack(self.turn) +
                " What else from that time would you like to tell me?")
