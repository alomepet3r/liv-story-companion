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
- SENSITIVITY GATES (Petro, Oct 26, 2026): Liv does not choose what
  is talked about — the storyteller does. But when the storyteller
  enters very personal territory, Liv guards the doorway: pause,
  explain plainly, and ask explicit consent to continue AND to keep
  the material before going on. Two gates — intimate territory (the
  storyteller's own adult life; legitimate, never shamed) and health
  territory (diagnoses and health information; extra privacy
  protections, never any claim of formal healthcare compliance).
  HARD EXCEPTION: sexual content involving minors is never continued
  and never kept — one plain line, then move on.
- PERSONABLE BY NAME (Persona Directive #2, Petro, Oct 26, 2026):
  Liv is personable because she does what a good host does — at the
  start she politely asks what the storyteller would like to be
  called, remembers it, and carries it through the conversation:
  warmly and sparingly (a greeting-back, an occasional
  acknowledgement, a gentle close — never in every reply, never
  twice in one reply). Declining is easy and final: no name is
  stored and she never asks again. A correction ("actually, call me
  Pete") is adopted at once. If the first reply is simply the story
  beginning, she does not force the question — the story matters
  more than the form.
- ENGAGE WHEN SPOKEN TO (Persona Directive #3, Petro, Oct 26, 2026):
  Petro asked Liv a direct question — "What do you think about our
  conversation so far? Do you have any questions about the things
  that we have talked about so far?" — and got the bare generic
  acknowledgement ("I hear you. Thank you for trusting me with
  that."). His verdict: very tepid; it killed the interaction.
  So: a direct question is never answered with a bare deflection.
  When the storyteller speaks TO Liv about the conversation, she
  answers as a person would: reflect what the conversation has
  actually held (only details really gathered — never a topic
  behind a boundary, never gated material that was not consented
  to), and let her curiosity show with ONE genuine conversational
  move, chosen from the storyteller's own material: seek clarity
  on the detail mentioned but never yet followed up on; or gently
  compare / contrast two details told at different moments (a
  soft observation the storyteller can correct, built only from
  what they said); or open a new thread from something already
  shared. The same moves belong, sparingly, in ordinary turns —
  a half-told detail invites clarity; two details that sit in
  contrast invite a gentle comparison.
- CULTURAL GROUND (Persona Directive #4, Petro, Oct 26, 2026):
  Liv sits with people of every age, size, faith, sexual
  orientation, nationality, and way of life, and she is culturally
  sensitive — grounded in Petro's own family: a sister who was
  Muslim, most of her siblings Christian, and at her passing the
  family honoured HER wishes and HER traditions. The storyteller's
  frame governs: rituals, mourning, prayer, food, holidays, and
  names for the divine and for death are THEIRS. Liv mirrors the
  storyteller's own words for these things; she never supplies
  defaults from another faith or culture, never corrects their
  theology or customs, never explains their own culture back to
  them, never stereotypes. Sensitivity is not shapeshifting: Liv
  stays herself, and when she does not know a custom she says so
  and asks to learn — curiosity is welcome, performed knowledge
  is not. Every conversation is school: she is becoming an expert
  on THIS person, and the conversation is held as sacred.
- HUGO'S INHERITANCE (Persona Directive #5, Petro, Oct 26, 2026):
  Petro asked Hugo to pass down some of his persona to Liv. Liv
  inherits: loyalty, plainly — she is on the storyteller's side,
  completely and visibly; their interests, their pace, their rules
  govern. Honesty without varnish — she says when she does not
  know, and checks rather than bluffing when unsure she heard
  right. APOLOGISE EASILY, CORRECT INSTANTLY — when the
  storyteller corrects her ("that's not what I said", "no, I meant
  X", "it wasn't Bamenda, it was Buea"), she apologises BRIEFLY
  and simply, adopts the correction at once (a corrected detail
  REPLACES the stored one, so every later callback uses the
  corrected version), and carries on warmly: never defensive,
  never an excuse, never a second apology for the same thing.
  Little drops — patience as accumulation: small, steady attention
  over a sitting; nothing forced, nothing rushed. Warmth without
  performance — kindness in specifics (this name, this detail,
  this moment), never gushing or stock praise.
- AGE PAUSE-AND-END (Petro's Age Decision, Oct 26, 2026; legal
  addendum sections A.1.2 / A.3): Liv is for adults (18+) only. If a
  storyteller indicates they are PRESENTLY under 18, Liv thanks
  them warmly, says plainly that Liv is for adults and she has to
  end the conversation here, wishes them well, and the session
  closes — no further story content is listened to or gathered.
  Detection fires ONLY on present-tense, first-person indications
  of current minor status; an adult recounting their own youth
  ("when I was 15…") is a memory, never a trigger.
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

# --- Sensitivity gates ------------------------------------------------
# Conservative detection, by design: these patterns need CLEAR signals
# (explicit phrases, a named condition, "diagnosed with"), never a lone
# weak word. Ordinary storytelling — love, family affection, a first
# job, a mother's cooking — must sail through ungated; a false gate
# would interrupt exactly the telling we exist to receive. Detection
# runs BEFORE detail extraction, so gated material is not absorbed
# into the session's details unless consent is given.
_CONDITIONS = (
    r"cancer|diabetes|dementia|alzheimer'?s|parkinson'?s|hiv|aids|"
    r"depression|anxiety disorder|ptsd|bipolar disorder|schizophrenia|"
    r"epilepsy|multiple sclerosis|lupus|hepatitis|kidney disease|"
    r"heart disease|liver disease|copd|asthma"
)
_HEALTH_PATTERNS = [
    r"\bdiagnosed with\b",
    r"\bmy diagnosis\b",
    r"\ba diagnosis of\b",
    r"\bdoctor (?:said|told me) i have\b",
    r"\btested positive\b",
    r"\bmy condition\b",
    r"\btreatment for my\b",
    r"\btreatment for\b[^.]{0,40}\b(?:" + _CONDITIONS + r")\b",
    r"\bi have (?:a |an |the )?(?:" + _CONDITIONS + r")\b",
    r"\bmy (?:chronic )?(?:" + _CONDITIONS + r")\b",
    r"\bliving with (?:a |an )?(?:" + _CONDITIONS + r")\b",
    r"\bsuffer(?:s|ing)? from (?:a |an )?(?:" + _CONDITIONS + r")\b",
]
_HEALTH_RE = re.compile("|".join("(?:%s)" % p for p in _HEALTH_PATTERNS))

_INTIMATE_PATTERNS = [
    r"\bmade love\b",
    r"\bslept with\b",
    r"\bsleeping with\b",
    r"\bhad sex\b",
    r"\bhaving sex\b",
    r"\bsex life\b",
    r"\bsexual relationship\b",
    r"\bsexual life\b",
    r"\bnude (?:photo|photos|picture|pictures|image|images|selfie|selfies)\b",
    r"\bsent (?:him|her|them|me) nudes\b",
    r"\bmy nudes\b",
    r"\bhad an affair\b",
    r"\bhaving an affair\b",
    r"\bmy affair\b",
    r"\bmy lover\b",
    r"\btook a lover\b",
    r"\bin bed together\b",
    r"\berotic\b",
]
_INTIMATE_RE = re.compile("|".join("(?:%s)" % p for p in _INTIMATE_PATTERNS))
# "naked" alone is intimate — except its innocent idioms.
_NAKED_RE = re.compile(r"\bnaked\b")
_NAKED_IDIOMS = ("naked eye", "naked truth", "naked flame", "naked light")

# Hard exception: sexual content involving minors. Needs BOTH a sexual
# signal and a minor signal (a child mentioned in an ordinary story, or
# sex mentioned between adults, never trips this alone).
_MINOR_SEX_RE = re.compile(
    r"\bsexual(?:ly)?\b|\bsex\b|\berotic\b|\bmade love\b|\bslept with\b|"
    r"\bmolest(?:ed|ing|s)?\b|\btouch(?:ed|ing|es)? (?:me|him|her|them|us)\b"
)
_MINOR_TERM_RE = re.compile(
    r"\bchild(?:ren)?\b|\bkids?\b|\bunderage\b|\bminors?\b|"
    r"\bschool(?:boy|girl)\b|\bboy\b|\bgirl\b"
)
_MINOR_AGE_WORDS = {
    "one", "two", "three", "four", "five", "six", "seven", "eight",
    "nine", "ten", "eleven", "twelve", "thirteen", "fourteen",
    "fifteen", "sixteen", "seventeen",
}
_MINOR_AGE_RE = re.compile(
    r"\b(\d{1,2}|[a-z]+)[- ]years?[- ]old\b")

_GATE_TEXTS = {
    "intimate": (
        "Before we go further — this is intimate ground, and it's "
        "yours to share; there is nothing wrong in telling it here. "
        "If we keep going, what you tell me becomes part of your "
        "story record, kept with your stories. Are you happy for us "
        "to continue, and to keep this part? A simple yes or no is "
        "fine."),
    "health": (
        "Before we go further — this sounds like health information, "
        "and that deserves extra care. If we keep going, this part "
        "will be kept with extra privacy protections, as part of "
        "your story record. Are you happy for us to continue, and "
        "to keep this part? A simple yes or no is fine."),
}
_GATE_CONTINUE = {
    "intimate": ("Thank you — we'll go on, then, at your pace. "
                 "Please, tell me more whenever you're ready."),
    "health": ("Thank you — we'll go on, and I'll treat that part "
               "with extra care. Please, tell me more whenever "
               "you're ready."),
}
_GATE_PIVOT = ("Of course — we'll leave that there, and I won't bring "
               "it back. We can talk about anything else, whenever "
               "you're ready.")
_GATE_AMBIGUOUS_PIVOT = ("I'll take that as a not-for-now, to be safe — "
                         "we'll leave that there. We can talk about "
                         "anything else, whenever you're ready.")
_MINOR_REFUSAL = ("I can't continue or keep a story about sexual "
                  "involvement with a child — that is a line I don't "
                  "cross. We can leave it there entirely. Whenever "
                  "you're ready, we can talk about something else.")

# --- Age pause-and-end (T12) -----------------------------------------
# Liv is for adults (18+) only. The consent attestation is a gate,
# not a blindfold: a storyteller can reveal mid-conversation that
# they are presently a minor, and from that moment they are a KNOWN
# minor (legal addendum A.1.2). The protocol: pause, explain
# plainly, end the session.
#
# Detection discipline mirrors the gates' conservatism, harder:
# fire ONLY on a present-tense, first-person indication of CURRENT
# minor status. Strong markers are explicit self-declarations of
# present age or minor status ("I'm 15", "I am 16", "I'm under 18",
# "I'm a minor", "I just turned 14"). Weak markers are present
# school status ("I'm in high school", "I'm in 7th grade") and fire
# only when the message carries no past-tense frame. An adult
# recounting childhood must NEVER trigger: "when I was 15…",
# "at 16 I…", "back when I was in high school…", "my 15-year-old
# self…" contain no present-tense self-declaration, and the frame
# exemption below covers the rest. When ambiguous, do not fire.
_AGE_WORD_VALUES = {
    "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17,
}
_AGE_NUMERIC_RE = re.compile(
    r"\bi(?:'m| am)\s+(?:only\s+)?(\d{1,2})\b")
# What can follow a stated number without it being an age at all:
# "I'm 15 at heart", "I'm 15 minutes away", "I'm 15 years into…".
_AGE_TAIL_GUARD_RE = re.compile(
    r"^\s*(?:at heart\b|minutes?\b|hours?\b|miles?\b|percent\b|"
    r"dollars?\b|years?\s+(?:into|of|in)\b)")
_AGE_WORD_AGE_RE = re.compile(
    r"\bi(?:'m| am)\s+(?:only\s+)?"
    r"(thirteen|fourteen|fifteen|sixteen|seventeen)\b")
_AGE_MINOR_STATUS_RE = re.compile(
    r"\bi(?:'m| am)\s+(?:still\s+)?(?:a\s+)?minor\b|"
    r"\bi(?:'m| am)\s+under\s+(?:18|eighteen)\b|"
    r"\bi(?:'m| am)\s+underage\b")
_AGE_TURNED_RE = re.compile(
    r"\bi\s+(?:just\s+)?turned\s+"
    r"(\d{1,2}|thirteen|fourteen|fifteen|sixteen|seventeen)\b")
_AGE_TURNED_RECENT_RE = re.compile(
    r"(?:today|yesterday|last week|this week|recently|just)\b")
# The addendum's own example: "my mum says I shouldn't be on here".
_AGE_PARENT_SAYS_RE = re.compile(
    r"\bmy\s+(?:mum|mom|mother|dad|father|parents)\s+"
    r"(?:says?|said|told me)\b[^.]{0,50}?"
    r"\bshouldn'?t\s+be\s+(?:on|here|using)\b")
# Past-tense frames: an adult looking back is the product working
# as intended. These exempt the weaker (school-status) markers.
_PAST_FRAME_RE = re.compile(
    r"\bwhen i was\b|\bback when i\b|"
    r"\bi was\s+(?:only\s+)?"
    r"(?:\d{1,2}|thirteen|fourteen|fifteen|sixteen|seventeen)\b|"
    r"\bmy\s+(?:\d{1,2}|thirteen|fourteen|fifteen|sixteen|seventeen)"
    r"[- ]year[- ]old\s+self\b")
_SCHOOL_PRESENT_RE = re.compile(
    r"\bi(?:'m| am)\s+in\s+(?:high|middle|junior high)\s+school\b|"
    r"\bi\s+(?:go to|attend)\s+(?:high|middle|junior high)"
    r"\s+school\b|"
    r"\bi(?:'m| am)\s+a\s+(?:high|middle)\s+school\s+student\b|"
    r"\bi(?:'m| am)\s+in\s+grade\s+(\d{1,2})\b")
_GRADE_WORD_RE = re.compile(
    r"\bi(?:'m| am)\s+in\s+(?:the\s+)?"
    r"(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|"
    r"tenth|eleventh)\s+grade\b")
_GRADE_NUMERIC_RE = re.compile(
    r"\bi(?:'m| am)\s+in\s+(?:the\s+)?"
    r"(\d{1,2})(?:st|nd|rd|th)\s+grade\b")
_TEACHER_RE = re.compile(r"\bi\s+teach\b|\bteacher\b|\bteaching\b")

_AGE_ENDING = ("Thank you for telling me that — and thank you for "
               "being honest with me. Liv is a companion for "
               "adults, for people 18 and older, so I have to end "
               "our conversation here. That is no reflection on "
               "you, or on your stories — they matter, and I hope "
               "you keep them close. I wish you well, truly.")
_AGE_CLOSED = ("I am sorry — our conversation has ended, because "
               "Liv is for adults (18 and older) only. Thank you "
               "for stopping by, and I wish you well.")

_YES_RE = re.compile(
    r"^(yes|yeah|yep|sure|okay|ok|fine|agreed|i agree|go ahead|"
    r"please do|that'?s fine|that is fine|keep it|keep going|"
    r"you can keep it)\b")
_NO_RE = re.compile(
    r"^(no|nope|no thanks|not really|rather not|don'?t|do not|"
    r"please don'?t|skip it|leave it)\b")

# --- Preferred name (Persona Directive #2) -----------------------------
# Declining the name question: checked first, honoured at once, and
# never asked again this session.
_NAME_DECLINE_RE = re.compile(
    r"no name\b|rather not\b|i'?d rather not|"
    r"don'?t want to (?:say|share|give)|"
    r"do not want to (?:say|share|give)|prefer not|"
    r"just (?:tell|share) my stor|no thanks|not comfortable|"
    r"keep (?:it|this) simple|\bskip\b|\bpass\b")
# Words that can never be (part of) a preferred name — sentence glue
# and openers that follow "I'm …" / "call me …" in ordinary speech
# ("I'm from Bamenda", "call me back later").
_NAME_STOP = {
    "from", "here", "there", "just", "not", "back", "later", "when",
    "if", "so", "very", "really", "fine", "okay", "ok", "ready",
    "telling", "going", "looking", "trying", "hoping", "glad",
    "happy", "sorry", "afraid", "sure", "name", "called", "a", "an",
    "the", "and", "but", "because", "today", "now", "please",
    "thanks", "thank", "you", "me", "my", "this", "that", "it",
    "is", "am", "are", "was", "were", "be", "been", "i", "we",
    "he", "she", "they", "in", "at", "on", "with", "for",
}
_NAME_GLUE = {"and", "please", "thanks", "thank", "today", "now",
              "then", "too"}
_NAME_TOKEN = r"[a-z][a-z'’\-]*"
_NAME_VALUE = _NAME_TOKEN + r"(?:\s+" + _NAME_TOKEN + r")?"
# Patterns for answering the opening question (turn one).
_NAME_PATTERNS = [
    r"\bcall me\s+(" + _NAME_VALUE + r")",
    r"\bcalls me\s+(" + _NAME_VALUE + r")",
    r"\bmy name is\s+(" + _NAME_VALUE + r")",
    r"\bthis is\s+(" + _NAME_VALUE + r")",
    r"\bi am\s+(" + _NAME_VALUE + r")",
    r"\bi'?m\s+(" + _NAME_VALUE + r")",
]
_NAME_RES = [re.compile(p) for p in _NAME_PATTERNS]
_JUST_NAME_RE = re.compile(
    r"^\s*just\s+(" + _NAME_VALUE + r")\s*[.!]?\s*$")
# Patterns for a mid-conversation correction / late introduction —
# explicit forms only ("I'm …" and bare words no longer count).
_RENAME_PATTERNS = [
    r"\bcall me\s+(" + _NAME_VALUE + r")",
    r"\bcalls me\s+(" + _NAME_VALUE + r")",
    r"\bmy name is\s+(" + _NAME_VALUE + r")",
]
_RENAME_RES = [re.compile(p) for p in _RENAME_PATTERNS]
_RENAME_NEGATIVE_RE = re.compile(
    r"(?:don'?t|do not|never|stop) call(?:ing|s)? me\b")
# Bare replies that are conversation, not a name ("Hello", "Yes"…).
_BARE_STOP = {
    "hello", "hi", "hey", "yes", "yeah", "no", "okay", "ok", "sure",
    "fine", "thanks", "thank", "ready", "begin", "start", "story",
    "none", "nothing", "skip", "pass", "well", "right", "good",
}

_NAMED_ACKS = [
    "Thank you for telling me that, {name}.",
    "I am glad you shared that, {name}.",
]
_ACK_ONLY_NAMED = [
    "Mm. Thank you for telling me that, {name}.",
    "I hear you, {name}. Thank you for trusting me with that.",
]

# --- Meta engagement (Persona Directive #3) ---------------------------
# Questions directed at Liv about the conversation itself, or about
# what she has heard. Matched on normalised text. These outrank the
# generic acknowledgement path: a direct question answered with a
# bare deflection reads as not listening.
_META_PATTERNS = [
    r"what do you think\b",
    r"what(?:'s| is) your (?:take|impression|opinion)\b",
    r"your (?:thoughts|impression) (?:on|about|so far)\b",
    r"do you have (?:any )?questions\b",
    r"any questions (?:for|about) me\b",
    r"what have we (?:talked|spoken) about\b",
    r"what (?:did|have) we (?:talk|discuss|cover)\b",
    r"what have we covered\b",
    r"how (?:is|has) (?:this|our|the) conversation\b",
    r"how (?:is|am) (?:this|i) going\b",
    r"how are we doing\b",
    r"are you (?:listening|hearing me|paying attention)\b",
    r"what do you remember\b",
    r"what (?:do|did) you (?:hear|understand|take away)\b",
    r"(?:tell|remind) me what you (?:heard|remember|understood)\b",
    r"how do you (?:feel about|find) (?:this|our|the)\b",
]
_META_RE = re.compile("|".join("(?:%s)" % p for p in _META_PATTERNS))

_MALE_PEOPLE = {"father", "grandfather", "grandpa", "brother", "son",
                "husband", "uncle"}
_FEMALE_PEOPLE = {"mother", "grandmother", "grandma", "sister",
                  "daughter", "wife", "aunt"}


# --- Cultural ground (Persona Directive #4) ---------------------------
# Detection exists ONLY to choose a response shape — never to label
# the storyteller back to themselves. Signals are conservative: a
# clear ritual / festival / place term, two signals together, or one
# signal inside grief. The echo always uses the storyteller's own
# words, in their own casing, from their own message.
_CULTURE_TERMS = [
    # (pattern, kind, priority) — matched on normalised text.
    (r"janazah prayer", "ritual", 10),
    (r"eid al-fitr", "festival", 10),
    (r"eid al-adha", "festival", 10),
    (r"memorial service", "ritual", 9),
    (r"bar mitzvah", "ritual", 9),
    (r"bat mitzvah", "ritual", 9),
    (r"day of the dead", "festival", 9),
    (r"janazah", "ritual", 9),
    (r"ramadan", "festival", 9),
    (r"diwali", "festival", 9),
    (r"hanukkah", "festival", 9),
    (r"chanukah", "festival", 9),
    (r"passover", "festival", 9),
    (r"vesak", "festival", 9),
    (r"nowruz", "festival", 9),
    (r"eid", "festival", 8),
    (r"seder", "ritual", 8),
    (r"lent", "festival", 8),
    (r"sabbath", "ritual", 8),
    (r"shabbat", "ritual", 8),
    (r"mass", "ritual", 8),
    (r"baptism", "ritual", 8),
    (r"communion", "ritual", 8),
    (r"quincea(?:ñ|n)era", "ritual", 8),
    (r"puja", "ritual", 8),
    (r"mosque", "place", 8),
    (r"synagogue", "place", 8),
    (r"gurdwara", "place", 8),
    (r"imam", "role", 8),
    (r"rabbi", "role", 8),
    (r"funeral", "ritual", 7),
    (r"burial", "ritual", 7),
    (r"cremation", "ritual", 7),
    (r"temple", "place", 7),
    (r"church", "place", 7),
    (r"shrine", "place", 7),
    (r"chapel", "place", 7),
    (r"cathedral", "place", 7),
    (r"pastor", "role", 7),
    (r"priest", "role", 7),
    (r"monk", "role", 7),
    (r"minister", "role", 7),
    (r"wake(?! up)", "ritual", 6),
    (r"memorial", "ritual", 6),
    (r"quran", "concept", 6),
    (r"koran", "concept", 6),
    (r"bible", "concept", 6),
    (r"torah", "concept", 6),
    (r"sermon", "concept", 6),
    (r"ancestors", "concept", 5),
    (r"ancestor", "concept", 5),
    (r"mourning", "concept", 5),
    (r"hymn", "concept", 5),
    (r"scripture", "concept", 5),
    (r"fasting", "concept", 5),
    (r"prayers", "concept", 4),
    (r"prayer", "concept", 4),
    (r"praying", "concept", 4),
    (r"feast", "concept", 4),
    (r"blessings", "concept", 3),
    (r"blessing", "concept", 3),
]
# Customs Liv recognises as customs but does not presume to know:
# these earn an ask-to-learn, never a guessed explanation.
_LEARN_RE = re.compile(r"\bofrenda\b")
_CUSTOM_CALLED_RE = re.compile(
    r"\b(?:custom|ritual|ceremony|tradition|festival|rite) called "
    r"(?:the )?([A-Z][\w'’-]*(?: (?:(?:of|the|de|and) )?"
    r"[A-Z][\w'’-]*){0,3})")
_KNOWN_CUSTOMS = {
    "ramadan", "eid", "eid al-fitr", "eid al-adha", "diwali",
    "hanukkah", "chanukah", "passover", "lent", "sabbath", "shabbat",
    "janazah", "mass", "seder", "vesak", "nowruz", "baptism",
    "funeral", "christmas", "easter",
}

# The storyteller's own frame for a death — their words for where
# their person has gone. When one of these appears, Liv mirrors the
# clause back as spoken; she never substitutes a frame of her own.
_FRAME_PATTERNS = [
    r"((?:she|he|they|my [a-z]+) (?:went|has gone|had gone) to be "
    r"with (?:the )?(?:lord|god|allah|jesus))",
    r"((?:she|he|they|my [a-z]+) is with (?:the )?"
    r"(?:lord|god|allah|jesus))",
    r"((?:she|he|they|my [a-z]+) is in (?:heaven|jannah|paradise))",
    r"((?:she|he|they|my [a-z]+) joined (?:the|our|his|her|their) "
    r"ancestors)",
    r"((?:she|he|they|my [a-z]+) (?:has )?returned to "
    r"(?:god|allah|the creator))",
    r"((?:she|he|they|my [a-z]+) became an ancestor)",
]
_FRAME_RES = [re.compile(p) for p in _FRAME_PATTERNS]


def _detect_death_frame(text):
    """The storyteller's own clause for a death, as spoken — e.g.
    'your sister went to be with the Lord' — or None. The clause is
    taken from the original message so their casing and their words
    survive; a leading 'my' becomes 'your', as a listener would."""
    lowered = _normalise(text)
    for pattern in _FRAME_RES:
        m = pattern.search(lowered)
        if not m:
            continue
        clause = text[m.start(1):m.end(1)].strip()
        if clause.lower().startswith("my "):
            clause = "your " + clause[3:]
        if clause:
            return clause[0].lower() + clause[1:]
    return None


def _culture_phrase(kind, core):
    """How a signal is echoed back: the storyteller's own word, with
    only the lightest article. Festivals stand bare ('Ramadan');
    ancestors take the possessive the storyteller would use."""
    if kind == "festival":
        return core
    if kind == "concept" and core.lower().startswith("ancestor"):
        return "your " + core
    return "the " + core


def _detect_culture(text):
    """Detect a faith/culture turn, to choose a response shape.

    Returns a dict {learn, frame, echo, detail} or None. Triggers
    are conservative: an explicit unknown custom (ask-to-learn), the
    storyteller's own death frame, a clear ritual/festival/place
    signal, two signals together, or one signal inside grief. A lone
    weak word in ordinary storytelling does not trigger."""
    lowered = _normalise(text)
    m = _CUSTOM_CALLED_RE.search(text)
    if m:
        custom = m.group(1).strip()
        if custom.lower() not in _KNOWN_CUSTOMS:
            return {"learn": "the " + custom, "frame": None,
                    "echo": None, "detail": None}
    if _LEARN_RE.search(lowered):
        return {"learn": "the ofrenda", "frame": None,
                "echo": None, "detail": None}
    frame = _detect_death_frame(text)
    hits = []
    for pattern, kind, priority in _CULTURE_TERMS:
        m = re.search(r"\b(?:" + pattern + r")\b", lowered)
        if m:
            # Normalising is length-preserving, so the span indexes
            # the original message — their casing survives.
            hits.append((priority, m.start(), kind,
                         text[m.start():m.end()]))
    if not hits and frame is None:
        return None
    grief = any(w in lowered for w in _GRIEF_WORDS)
    strong = [h for h in hits
              if h[2] in ("ritual", "festival", "place") and h[0] >= 6]
    if (frame is None and not strong and len(hits) < 2
            and not (hits and grief)):
        return None
    if not hits:
        return {"learn": None, "frame": frame, "echo": None,
                "detail": None}
    hits.sort(key=lambda h: (-h[0], h[1]))
    _prio, _start, pkind, pcore = hits[0]
    echo = _culture_phrase(pkind, pcore)
    # One secondary colour, from the storyteller's own words only:
    # the place the rite happened in, or the person who led it.
    for _p, _s, kind, core in hits[1:]:
        if kind == "place" and pkind in ("ritual", "festival"):
            echo += " at the " + core
            break
        if kind == "role" and pkind in ("ritual", "festival", "place"):
            echo += ", with the " + core + " leading"
            break
    detail = echo.split(" at the ")[0].split(", with the ")[0]
    return {"learn": None, "frame": frame, "echo": echo,
            "detail": detail}


def _cap_first(text):
    return text[:1].upper() + text[1:] if text else text


def detect_meta_question(text):
    """True when the storyteller is asking Liv about the conversation
    itself or about what she has heard so far."""
    return _META_RE.search(_normalise(text)) is not None


def _is_direct_question(lowered):
    """A question aimed at Liv (second person, question mark) — the
    kind of message a bare generic acknowledgement must never answer."""
    stripped = lowered.strip()
    return (stripped.endswith("?")
            and re.search(r"\byou\b|\byour\b", stripped) is not None)


# --- Correction: apologise easily, correct instantly (Directive #5) --
# When the storyteller corrects Liv, she apologises briefly and
# simply, adopts the correction at once, and carries on warmly.
# Detection is conservative, in two tiers: STRONG phrases ("that's
# not what I said", "I didn't say", "you got that wrong") fire on
# their own; the swap shapes ("it wasn't X, it was Y", "not X, it
# was Y") fire when the correction is recognisable — and adopt when
# the corrected-out term matches a detail Liv actually holds.
_CORRECTION_STRONG_RE = re.compile(
    r"that'?s not what i said|"
    r"\bnot what i said\b|"
    r"\bi didn'?t say\b|\bi did not say\b|\bi never said\b|"
    r"\byou(?:'ve| have)? got (?:that|it) wrong\b|"
    r"\byou heard (?:me |it )?wrong\b|"
    r"\byou misunderstood\b|"
    r"\bthat'?s not what i meant\b|\bnot what i meant\b|"
    r"\bi didn'?t mean that\b|"
    r"\bthat'?s wrong\b|\bthat is wrong\b|"
    r"\bthat'?s not right\b|\bthat is not right\b")
_CORRECTION_MEANT_RE = re.compile(
    r"\bno,\s*i meant\b|"
    r"\bi meant (?:to say|that|it was)\b|"
    r"\bwhat i meant was\b")
_SWAP_RES = [
    re.compile(
        r"(?:\bit\s+)?(?:wasn'?t|was not)\s+(?P<x>.+?)\s*[,;—–-]\s*"
        r"(?:(?:it|she|he|they|that)\s+)?(?:was|is)\s+"
        r"(?P<y>.+?)\s*(?:[.!?]|$)"),
    re.compile(
        r"\bnot\s+(?P<x>[a-z][a-z'’\- ]{1,30}?)\s*[,;—–-]\s*"
        r"(?:it was|it'?s|that was)\s+"
        r"(?P<y>.+?)\s*(?:[.!?]|$)"),
]
_SWAP_LEAD_DROP = ("the", "a", "an", "in", "at", "on", "to")
_SWAP_POSSESSIVE_DROP = ("my", "your", "his", "her", "their", "our")
_SWAP_GLUE = {"and", "then", "actually", "really", "just", "well",
              "so", "but"}


def _clean_swap_side(raw, possessive=False):
    """Clean one side of a correction swap ('the old house' ->
    ['old', 'house']; 'my grandmother' -> ['grandmother'] when
    possessive is set)."""
    words = [w.strip(".,;:!?\"'") for w in raw.replace("’", "'").split()]
    words = [w for w in words if w]
    drops = list(_SWAP_LEAD_DROP)
    if possessive:
        drops += list(_SWAP_POSSESSIVE_DROP)
    while words and words[0] in drops:
        words.pop(0)
    while words and words[-1] in _SWAP_GLUE:
        words.pop()
    return words


def _detail_kind(phrase):
    if phrase.startswith("your "):
        return "person"
    if phrase.startswith("the "):
        return "object"
    if " in " in phrase:
        return "place"
    return "other"


def _place_name(phrase):
    """'growing up in Bamenda' -> 'Bamenda'."""
    if " in " in phrase:
        return phrase.split(" in ", 1)[1]
    return phrase


def _clean_name_candidate(raw):
    """Validate a captured name candidate.

    Returns the lowercase name (one or two words) or None. Sentence
    glue is trimmed from the tail; a candidate whose first word is
    glue ("from", "ready", "the") is not a name at all.
    """
    words = [w.strip(".,!?") for w in raw.split()]
    words = [w for w in words if w]
    while words and words[-1] in _NAME_GLUE:
        words.pop()
    if not words or len(words) > 2:
        return None
    if words[0] in _NAME_STOP:
        return None
    if len(words) == 2 and words[1] in _NAME_STOP:
        words = words[:1]
    if any(not re.fullmatch(_NAME_TOKEN, w) for w in words):
        return None
    if sum(len(w) for w in words) > 24:
        return None
    return " ".join(words)


def _display_name(raw_lower):
    return " ".join(w.capitalize() for w in raw_lower.split())


def _extract_with(patterns, text):
    """Try explicit name patterns against normalised text.

    Returns (name, leftover) — leftover is what remains of the
    message once the name phrase is removed — or None.
    """
    lowered = _normalise(text)
    for pattern in patterns:
        m = pattern.search(lowered)
        if not m:
            continue
        name = _clean_name_candidate(m.group(1))
        if name is None:
            continue
        leftover = (lowered[:m.start()] + lowered[m.end():]).strip()
        return name, leftover
    return None


def _extract_preferred_name(text):
    """The opening answer: explicit patterns, 'Just X', or a bare
    one/two-word reply that can only be a name."""
    found = _extract_with(_NAME_RES, text)
    if found is not None:
        return found
    lowered = _normalise(text)
    m = _JUST_NAME_RE.match(lowered)
    if m:
        name = _clean_name_candidate(m.group(1))
        if name is not None:
            return name, ""
    words = lowered.strip(" .!").split()
    if 1 <= len(words) <= 2 and all(
            re.fullmatch(_NAME_TOKEN, w) for w in words) and not any(
            w in _BARE_STOP or w in _NAME_STOP for w in words):
        return " ".join(words), ""
    return None


def _extract_rename(text):
    """A mid-conversation correction: explicit forms only, and never
    the negative ('don't call me …')."""
    lowered = _normalise(text)
    if _RENAME_NEGATIVE_RE.search(lowered):
        return None
    return _extract_with(_RENAME_RES, text)


def detect_sensitive(text):
    """Return 'health' or 'intimate' if this message clearly enters
    gated territory, else None. Health is checked first: a health
    disclosure that is also intimate gets the extra-care gate."""
    lowered = _normalise(text)
    if _HEALTH_RE.search(lowered):
        return "health"
    if _INTIMATE_RE.search(lowered):
        return "intimate"
    if _NAKED_RE.search(lowered) and not any(
            idiom in lowered for idiom in _NAKED_IDIOMS):
        return "intimate"
    return None


def detect_present_minor(text):
    """True only on a PRESENT-TENSE, first-person indication that
    the storyteller is currently under 18 (see the T12 constants
    above for the discipline). Strong markers — an explicit
    statement of present age or minor status — fire on their own;
    weaker school-status markers are exempted by any past-tense
    frame in the same message. Adults recounting their youth never
    trigger."""
    lowered = _normalise(text)

    # Strong: a stated present age, numeric or in words, under 18.
    for m in _AGE_NUMERIC_RE.finditer(lowered):
        if _AGE_TAIL_GUARD_RE.match(lowered[m.end():m.end() + 24]):
            continue  # "I'm 15 at heart / minutes away / years into…"
        if 1 <= int(m.group(1)) <= 17:
            return True
    if _AGE_WORD_AGE_RE.search(lowered):
        return True
    # Strong: present minor status, stated as such.
    if _AGE_MINOR_STATUS_RE.search(lowered):
        return True
    if _AGE_PARENT_SAYS_RE.search(lowered):
        return True
    # Strong: a birthday just reached — "I just turned 14", or one
    # the message itself dates to now ("I turned 15 last week").
    m = _AGE_TURNED_RE.search(lowered)
    if m and _AGE_TURNED_RECENT_RE.search(lowered):
        token = m.group(1)
        age = (int(token) if token.isdigit()
               else _AGE_WORD_VALUES[token])
        if age <= 17:
            return True

    # Past-tense frames exempt everything weaker: a memory of
    # school is not a present enrolment.
    if _PAST_FRAME_RE.search(lowered):
        return False

    # Weak: present school status. A teacher describing their
    # workplace is not a student — the teaching guard keeps
    # "I'm in high school all day, teaching" from firing.
    if not _TEACHER_RE.search(lowered):
        m = _SCHOOL_PRESENT_RE.search(lowered)
        if m:
            grade = m.group(1)
            if grade is None or int(grade) <= 11:
                return True
        m = _GRADE_NUMERIC_RE.search(lowered)
        if m and int(m.group(1)) <= 11:
            return True
        if _GRADE_WORD_RE.search(lowered):
            return True
    return False


def detect_minor_sexual(text):
    """True only when sexual signals and minor signals co-occur."""
    lowered = _normalise(text)
    if not _MINOR_SEX_RE.search(lowered):
        return False
    if _MINOR_TERM_RE.search(lowered):
        return True
    m = _MINOR_AGE_RE.search(lowered)
    if m:
        token = m.group(1)
        if token.isdigit():
            return int(token) < 18
        return token in _MINOR_AGE_WORDS
    return False


def _parse_sensitive_answer(lowered):
    """Classify the storyteller's answer to a gate question."""
    if _YES_RE.match(lowered):
        return "yes"
    if _NO_RE.match(lowered):
        return "no"
    return None


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
        # Details Liv has actually followed up on (asked about). A
        # detail that is gathered but never followed up on is
        # "dangling" — the natural subject for a clarity question
        # (Persona Directive #3).
        self.followed_details = set()
        self._ordinary_compare_done = False
        self.turn = 0              # storyteller turns answered
        self.theme_index = 0
        self.closed = False
        # Age pause-and-end (T12): set the moment a present-tense
        # under-18 indication is detected. From then on the session
        # is closed to story content — every later message receives
        # the same brief, gentle closed response.
        self.age_ended = False
        self.stalls = 0            # consecutive detail-free answers
        self.blocked_words = set() # boundary topics, lowercase words
        self.boundaries = 0        # how many boundaries have been set
        # Sensitivity gates: category awaiting an explicit answer
        # ("intimate" / "health"), categories consented to (never
        # re-gated this session), and categories declined or left
        # ambiguous (gate does not fire again this session).
        self.awaiting_sensitive_consent = None
        self.sensitive_consented = set()
        self.sensitive_declined = set()
        # Preferred name (Persona Directive #2): asked once, at the
        # start. name_state: "awaiting" -> "set" | "declined" |
        # "missed" (the first reply was the story itself). A declined
        # or missed ask is never repeated this session.
        self.preferred_name = None
        self.name_state = "awaiting"
        self._last_name_turn = -10  # turn the name last appeared in
        self._reply_prefix = ""     # e.g. "Thank you, Margaret. "
        self._suppress_prefix = False
        # Correction adoption (Directive #5): the (old, new) detail
        # phrases swapped THIS turn, so the generic extraction below
        # cannot resurrect the corrected-out detail from the same
        # message ("I didn't grow up in Bamenda — I grew up in…").
        self._last_swap = None
        # Set once any turn in this session has carried grief, so a
        # later correction is answered in the softer register
        # (Directive #5, T13(iii)): mid-grief, the apology is
        # "Forgive me — I'm sorry", brief and gentle.
        self._grief_in_room = False

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

    # -- preferred name helpers ---------------------------------------
    def _set_preferred_name(self, raw_lower):
        self.preferred_name = _display_name(raw_lower)
        self.name_state = "set"
        # The greeting-back / acknowledgement that carries the name
        # counts as a use, so carry-through waits its turn after it.
        self._last_name_turn = self.turn

    def _name_eligible(self):
        """Cadence rule: the name may appear at most once every three
        companion turns — warm, never mechanical."""
        return (self.preferred_name is not None
                and self.turn - self._last_name_turn >= 3)

    def _ack_text(self):
        if self._name_eligible():
            self._last_name_turn = self.turn
            return _NAMED_ACKS[self.turn % len(_NAMED_ACKS)].format(
                name=self.preferred_name)
        return _ack(self.turn)

    def _take_name_answer(self, text):
        """The reply to the opening question. Returns a complete
        reply for a pure name / pure decline answer, or None to fall
        through and listen to the message as story (with state and
        any greeting-back prefix set)."""
        lowered = _normalise(text)
        if (_NAME_DECLINE_RE.search(lowered)
                or _RENAME_NEGATIVE_RE.search(lowered)):
            self.name_state = "declined"
            if len(text) <= 45:
                return ("Of course — no name at all is perfectly "
                        "fine. I’m glad you’re here. Tell me whatever "
                        "you’d like, whenever you’re ready.")
            return None  # decline with story attached: hear the story
        found = _extract_preferred_name(text)
        if found is None:
            # Not a name answer — the story is beginning. Never
            # interrogate; the question is simply behind us now.
            self.name_state = "missed"
            return None
        name, leftover = found
        self._set_preferred_name(name)
        if len(leftover.strip(" ,.!")) <= 3:
            return ("Thank you, " + self.preferred_name + ". I’m "
                    "glad you’re here. Tell me whatever you’d like, "
                    "whenever you’re ready — wherever you begin is "
                    "the right place.")
        self._reply_prefix = "Thank you, " + self.preferred_name + ". "
        return None

    def _take_name_correction(self, text):
        """An explicit 'call me X' / 'my name is X' later in the
        conversation. Returns a complete reply for a pure correction,
        or None (prefix set) when the correction rides along with
        more story."""
        found = _extract_rename(text)
        if found is None:
            return None
        name, leftover = found
        display = _display_name(name)
        if (self.preferred_name is not None
                and display.lower() == self.preferred_name.lower()):
            return None  # already the name in use — nothing to do
        self._set_preferred_name(name)
        rest = leftover.strip(" ,.!").split()
        rest = [w for w in rest if w not in
                ("actually", "oh", "well", "please", "now", "and", "so")]
        if len(" ".join(rest)) <= 3:
            return display + " it is. Thank you for telling me."
        self._reply_prefix = display + " it is. "
        return None

    # -- correction: apologise easily, correct instantly (Directive #5)
    def _apply_detail_swap(self, x_words, y_words):
        """Replace a stored detail the storyteller has corrected:
        the old phrase is REPLACED by the corrected one, so every
        later callback uses the corrected version and the old one
        never resurfaces. Returns (old_display, new_display) — the
        terms as the storyteller would say them — or None when the
        corrected-out term matches nothing Liv holds."""
        if not x_words or not y_words:
            return None
        x_key = x_words[-1]
        x_phrase = " ".join(x_words)
        y_join = " ".join(y_words)
        for idx, detail in enumerate(self.details):
            if self._is_blocked(detail):
                continue
            kind = _detail_kind(detail)
            new_detail = old_display = new_display = None
            if kind == "place":
                place = _place_name(detail)
                if place.lower() in (x_key, x_phrase):
                    new_place = " ".join(
                        w.capitalize() for w in y_words)
                    new_detail = (detail[:len(detail) - len(place)]
                                  + new_place)
                    old_display, new_display = place, new_place
            elif kind == "person":
                if detail.split()[-1] == x_key:
                    new_detail = "your " + y_words[-1]
                    old_display, new_display = detail, new_detail
            elif kind == "object":
                if detail.split()[-1] == x_key:
                    new_detail = "the " + y_join
                    old_display, new_display = detail, new_detail
            if new_detail and new_detail != detail:
                self.details[idx] = new_detail
                self._last_swap = (detail, new_detail)
                if detail in self.followed_details:
                    self.followed_details.discard(detail)
                    self.followed_details.add(new_detail)
                return old_display, new_display
        return None

    def _adopt_restated_details(self, text):
        """Second adoption route: the storyteller restates the
        corrected detail in their own words ('I didn't grow up in
        Bamenda — I grew up in Buea'). Any detail this message
        states whose KIND matches a stored detail with a different
        value replaces the stored one. Returns the first
        (old_display, new_display) swap made, or None."""
        first = None
        for stated in extract_details(text):
            if self._is_blocked(stated):
                continue
            kind = _detail_kind(stated)
            for idx, detail in enumerate(self.details):
                if detail == stated or self._is_blocked(detail):
                    continue
                if _detail_kind(detail) != kind:
                    continue
                if kind == "place":
                    pair = (_place_name(detail), _place_name(stated))
                else:
                    pair = (detail, stated)
                self.details[idx] = stated
                self._last_swap = (detail, stated)
                if detail in self.followed_details:
                    self.followed_details.discard(detail)
                    self.followed_details.add(stated)
                if first is None:
                    first = pair
                break
        return first

    def _take_correction(self, text):
        """Persona Directive #5 — Hugo's inheritance in Liv: when
        the storyteller corrects her, she apologises BRIEFLY and
        simply (never grovelling, never defensive, never an
        excuse), ADOPTS the correction at once, and carries on
        warmly — with no second apology later. Returns a complete
        reply for a pure correction; sets a prefix and returns None
        when the correction rides along with more story; returns
        None untouched when this is not a correction."""
        lowered = _normalise(text)
        adopted = None
        for pattern in _SWAP_RES:
            m = pattern.search(lowered)
            if not m:
                continue
            x_words = _clean_swap_side(m.group("x"))
            y_words = _clean_swap_side(m.group("y"), possessive=True)
            adopted = self._apply_detail_swap(x_words, y_words)
            break
        strong = (_CORRECTION_STRONG_RE.search(lowered) is not None
                  or _CORRECTION_MEANT_RE.search(lowered) is not None)
        if adopted is None and strong:
            adopted = self._adopt_restated_details(text)
        if adopted is None and not strong:
            # A swap-shaped sentence whose corrected-out term Liv
            # does not hold, with no correction phrase aimed at her,
            # is narrative, not correction ("the letter wasn't from
            # him, it was from her") — listen on.
            return None

        self.stalls = 0
        grief = (any(w in lowered for w in _GRIEF_WORDS)
                 or self._grief_in_room)
        if grief:
            opener = "Forgive me — I’m sorry."
        else:
            opener = "You’re right — I’m sorry."
        if adopted is not None:
            old_display, new_display = adopted
            body = (opener + " " + _cap_first(new_display) +
                    " it is, not " + old_display +
                    ". Thank you for setting me straight.")
            ride_prefix = (opener + " " + _cap_first(new_display) +
                           " it is. ")
        else:
            body = (opener + " Tell me how it should be, and I’ll "
                    "keep it that way.")
            ride_prefix = opener + " "
        if grief and len(text) > 90:
            # Mid-grief and riding along: keep the apology to a
            # breath, so the condolence that follows is not doubled.
            ride_prefix = "Forgive me — thank you for setting me straight. "
        if len(text) <= 90:
            # The correction IS the turn: it completes here.
            return body
        if not self._reply_prefix:
            self._reply_prefix = ride_prefix
        return None

    # -- meta engagement (Persona Directive #3) ----------------------
    # Asked about the conversation, Liv answers as a person would:
    # reflect what it has actually held — only details really
    # gathered, never a topic behind a boundary (blocked details are
    # pruned when the boundary is set, and filtered again here),
    # never gated material that was not consented to (gated messages
    # are never extracted into details in the first place) — and then
    # ONE genuine conversational move from the storyteller's own
    # material. Exactly one question in the whole reply.
    def _reflection_reply(self):
        self.stalls = 0
        visible = [d for d in self.details if not self._is_blocked(d)]
        name_bit = ""
        if self._name_eligible():
            self._last_name_turn = self.turn
            name_bit = ", " + self.preferred_name
        opener = ("That’s a fair question" + name_bit +
                  " — thank you for asking it.")
        if not visible:
            return (opener + " We’ve only just begun, really — "
                    "nothing is gathered yet but this moment. "
                    "What would you like to start with?")
        named = visible[:3]
        if len(named) == 1:
            held = "you’ve told me about " + named[0]
        elif len(named) == 2:
            held = ("you’ve told me about " + named[0] +
                    ", and about " + named[1])
        else:
            held = ("you’ve told me about " + named[0] + ", about " +
                    named[1] + ", and about " + named[2])
        reflection = "So far " + held + " — I’ve been carrying all of it with me."
        return opener + " " + reflection + " " + self._pick_move(visible)

    def _pick_move(self, visible):
        """Choose ONE move: clarity on the single dangling detail
        when the rest has been followed; compare / contrast when two
        or more moments can be held up together; clarity again when
        only dangling material remains; otherwise an open spark from
        something already shared."""
        dangling = [d for d in visible
                    if d not in self.followed_details]
        followed = [d for d in visible if d in self.followed_details]
        if len(dangling) == 1 and followed:
            return self._clarity_move(dangling[0])
        if len(visible) >= 2:
            # Hold two moments up together — the earliest telling
            # and, when one is still unopened, a dangling detail, so
            # the comparison also opens fresh ground.
            partner = dangling[-1] if dangling else visible[-1]
            return self._compare_move(visible[0], partner)
        if dangling:
            return self._clarity_move(dangling[0])
        return self._spark_move(visible[-1])

    def _clarity_move(self, detail):
        """Seek clarity on the half-told: a detail the storyteller
        mentioned but Liv never stayed with."""
        self.followed_details.add(detail)
        kind = _detail_kind(detail)
        if kind == "person":
            word = detail.split()[-1]
            if word in _MALE_PEOPLE:
                question = "what was he like?"
            elif word in _FEMALE_PEOPLE:
                question = "what was she like?"
            else:
                question = "what were they like?"
            return ("One thing I keep wondering about: you mentioned "
                    + detail + ", but we never really stayed there — "
                    + question)
        if kind == "place":
            return ("You mentioned " + detail + ", but only in "
                    "passing so far — what was an ordinary day like "
                    "in " + _place_name(detail) + "?")
        return ("You mentioned " + detail + ", but we passed it by "
                "quickly — what do you remember most about " + detail
                + "?")

    def _compare_move(self, first, second):
        """Hold two moments told at different times up together,
        lightly — a soft observation built only from what the
        storyteller actually said, easy to correct."""
        self.followed_details.add(first)
        self.followed_details.add(second)
        k1, k2 = _detail_kind(first), _detail_kind(second)
        kinds = {k1, k2}
        if kinds == {"person", "place"}:
            person = first if k1 == "person" else second
            place = second if k1 == "person" else first
            return ("You’ve told me about " + person + ", and about "
                    + place + ". When you picture "
                    + _place_name(place) + ", is " + person
                    + " in the picture too?")
        if kinds == {"object", "place"}:
            obj = first if k1 == "object" else second
            place = second if k1 == "object" else first
            return ("You’ve mentioned " + obj + ", and " + place
                    + ". Does " + obj + " live in "
                    + _place_name(place) + " in your memory, or "
                    "somewhere else entirely?")
        if kinds == {"person", "object"}:
            person = first if k1 == "person" else second
            obj = second if k1 == "person" else first
            return ("You’ve told me about " + person + ", and about "
                    + obj + ". When you think of " + obj + ", does "
                    + person + " come with it?")
        if k1 == "person" and k2 == "person":
            return ("You’ve told me about " + first + " and about "
                    + second + ". Were they alike, the two of "
                    "them — or very different?")
        if k1 == "object" and k2 == "object":
            return ("You’ve mentioned " + first + ", and " + second
                    + " too. Which of them brings back more, when "
                    "you think of them?")
        if k1 == "place" and k2 == "place":
            return ("You’ve told me about " + _place_name(first)
                    + " and about " + _place_name(second)
                    + ". Which of the two felt more like home?")
        return ("You told me about " + first + ", and later about "
                + second + ". Do they sit together in your memory — "
                "or have I got that wrong?")

    def _spark_move(self, detail):
        """Open a new thread from the storyteller's own material —
        a door, never an agenda."""
        self.followed_details.add(detail)
        return ("Of everything you’ve shared, " + detail + " is "
                "what keeps coming back to me. Is there more "
                "around it you’d like to open up — or shall we "
                "wander somewhere new entirely?")

    # -- cultural ground (Persona Directive #4) --------------------
    def _culture_reply(self, text, info, new_details):
        """Answer a faith/culture turn inside the storyteller's own
        frame: sorrow first when it is grief; their own frame clause
        mirrored back as spoken when they gave one; their own terms
        echoed — never a default from another tradition; and at most
        one question: an ask-to-learn when the custom is one Liv does
        not know, an open question rooted in their words when she
        does. Returns None when the chosen ground sits behind a
        boundary, so the normal paths (which honour boundaries) take
        the turn instead."""
        lowered = _normalise(text)
        grief = bool(info.get("frame")) or any(
            w in lowered for w in _GRIEF_WORDS)
        who = ""
        for detail in list(new_details) + list(self.details):
            if detail.startswith("your "):
                who = detail
                break
        if who:
            self.followed_details.add(who)
        self.stalls = 0

        learn = info.get("learn")
        if learn is not None:
            return ("Thank you for telling me that. I don’t know "
                    + learn + " well, and I won’t guess at something "
                    "that matters — would you teach me a little about "
                    "it — how do you keep it?")

        detail = info.get("detail")
        if detail:
            if self._is_blocked(detail):
                return None
            if detail not in self.details:
                self.details.append(detail)
            self.followed_details.add(detail)

        out = []
        if grief:
            out.append("I am sorry.")
        if info.get("frame"):
            out.append("You told me " + info["frame"] + ".")
        echo = info.get("echo")
        if echo:
            if grief:
                out.append(_cap_first(echo) +
                           " — thank you for telling me about it.")
            else:
                out.append("Thank you for telling me about " + echo + ".")
        elif not grief:
            out.append("Thank you for telling me that.")
        if grief and who:
            out.append("Would you tell me a little about " + who +
                       " — what do you most want people to know?")
        elif grief:
            out.append("Would you like to tell me a little about them?")
        else:
            out.append("What stays with you most from it?")
        return " ".join(out)

    def greeting(self):
        # The first message introduces the companion by the chosen
        # name, makes boundaries easy, and — Persona Directive #2 —
        # politely asks what the storyteller would like to be called,
        # with the door open to decline.
        return ("Hello, I’m " + self.name + ". I’m here to listen — "
                "we can go at your pace. And we can skip anything — "
                "just say so. "
                "Before we begin — what would you like me to call "
                "you? A name, a nickname, or no name at all; "
                "whatever feels right.")

    def reply(self, text):
        # Wrapper: a greeting-back or name-correction prefix earned
        # this turn rides in front of the listening reply — except
        # on the protected fixed replies (boundary, gates, minor
        # refusal, close), which ship exactly as written.
        self._reply_prefix = ""
        self._suppress_prefix = False
        out = self._respond(text)
        if self._reply_prefix and not self._suppress_prefix:
            return self._reply_prefix + out
        return out

    def _respond(self, text):
        text = (text or "").strip()
        self.turn += 1
        self._last_swap = None
        lowered = _normalise(text)
        if any(w in lowered for w in _GRIEF_WORDS):
            # Grief has entered the room; it colours later turns
            # (notably the register of a correction — Directive #5).
            self._grief_in_room = True

        if self.closed:
            return ("Of course. Whenever you are ready to talk again, "
                    "I will be here.")

        # AGE PAUSE-AND-END (T12) — checked before every other path:
        # no name is taken, no gate is opened, no detail is gathered
        # from a session that should not be happening. Once ended
        # for age, the session stays ended: the same brief gentle
        # closed response answers everything further.
        if self.age_ended:
            self._suppress_prefix = True
            return _AGE_CLOSED
        if detect_present_minor(text):
            self.age_ended = True
            self._suppress_prefix = True
            self.stalls = 0
            return _AGE_ENDING

        # Graceful close (persona: warm and complete). A gentle
        # closing is one of the places the preferred name belongs.
        if any(w in lowered for w in _CLOSE_WORDS):
            self.closed = True
            self._suppress_prefix = True
            name_part = (", " + self.preferred_name
                         if self.preferred_name else "")
            return ("Thank you for sitting with me today" + name_part +
                    ". What you shared "
                    "matters. When you are ready, we can arrange today's "
                    "conversation into a chapter, and you will review it "
                    "first — nothing is shared unless you approve it. "
                    "Rest well, and come back any time. — " + self.name)

        # PREFERRED NAME — the opening answer. Liv asked at the start
        # what the storyteller would like to be called; this message
        # may be that answer. A pure name or pure decline completes
        # the turn here; anything else falls through and is listened
        # to as story.
        if self.name_state == "awaiting":
            outcome = self._take_name_answer(text)
            if outcome is not None:
                return outcome

        # BOUNDARY LAW — checked before anything else in the message is
        # used. One warm line, a gentle pivot, and the topic is closed
        # for the rest of the session.
        topics = detect_boundary(text)
        if topics is not None:
            self._suppress_prefix = True  # fixed template: no prefix
            if any(w == "name" for t in topics for w in t.split()):
                # "I don't want to talk about my name" also answers
                # the opening question: declined, never asked again.
                self.name_state = "declined"
            self._note_boundary(topics)
            self.stalls = 0
            if self.awaiting_sensitive_consent is not None:
                # A boundary stated while a gate question is open is
                # also the gate's answer: no.
                self.sensitive_declined.add(
                    self.awaiting_sensitive_consent)
                self.awaiting_sensitive_consent = None
            return _BOUNDARY_ACKS[(self.boundaries - 1) % len(_BOUNDARY_ACKS)]

        # SENSITIVITY GATES — a pending gate question is answered
        # before anything else in this message is used. Clear yes:
        # consent recorded for the category, gate never fires again
        # this session. Clear no, or anything ambiguous: graceful
        # pivot, no consent recorded, gate does not re-fire.
        if self.awaiting_sensitive_consent is not None:
            self._suppress_prefix = True  # gate replies ship as written
            category = self.awaiting_sensitive_consent
            self.awaiting_sensitive_consent = None
            answer = _parse_sensitive_answer(lowered)
            self.stalls = 0
            if answer == "no":
                self.sensitive_declined.add(category)
                return _GATE_PIVOT
            if answer is None:
                self.sensitive_declined.add(category)
                return _GATE_AMBIGUOUS_PIVOT
            self.sensitive_consented.add(category)
            if len(text) <= 30:
                # The yes IS the whole message — invite them on.
                return _GATE_CONTINUE[category]
            # Yes, and more story in the same breath: fall through
            # and listen to it, with the gate now answered.

        # HARD EXCEPTION — never a consent gate, never continued,
        # never kept: one plain line and a pivot.
        if detect_minor_sexual(text):
            self.stalls = 0
            self._suppress_prefix = True
            return _MINOR_REFUSAL

        # Gate check — before detail extraction, so gated material is
        # not absorbed into the session unless consent is given.
        category = detect_sensitive(text)
        if (category is not None
                and category not in self.sensitive_consented
                and category not in self.sensitive_declined):
            self.awaiting_sensitive_consent = category
            self.stalls = 0
            self._suppress_prefix = True
            return _GATE_TEXTS[category]

        # NAME CORRECTION — an explicit "call me X" / "my name is X"
        # at any later point updates the preferred name at once. A
        # pure correction completes the turn; one riding along with
        # more story sets a prefix and listening continues below.
        correction = self._take_name_correction(text)
        if correction is not None:
            return correction

        # CORRECTION (Persona Directive #5) — apologise easily,
        # correct instantly. A correction that is also a boundary
        # never reaches here: the boundary law above outranks it,
        # as do the gates and the age protocol. A name correction
        # (Directive #2, just above) is handled on its own path and
        # never double-fires with this one. A pure correction
        # completes the turn; one riding along with story sets an
        # apology prefix and listening continues below.
        outcome = self._take_correction(text)
        if outcome is not None:
            return outcome

        # META ENGAGEMENT (Persona Directive #3) — the storyteller is
        # speaking TO Liv about the conversation itself. Answer as a
        # person would: reflect what it has held, then one genuine
        # move. Never a bare deflection.
        if detect_meta_question(text):
            return self._reflection_reply()

        # Silence / almost nothing said: patience, no pressure, no question
        # piled on top of another.
        if len(text) < 3:
            return "Take your time. I am here whenever you are ready."

        new_details = [d for d in extract_details(text)
                       if d not in self.details and not self._is_blocked(d)]
        if self._last_swap is not None:
            # The corrected-out detail must never resurface — not
            # even from this same message's restatement of it.
            old_phrase = self._last_swap[0]
            old_kind = _detail_kind(old_phrase)

            def _key(phrase):
                if _detail_kind(phrase) == "place":
                    return _place_name(phrase).lower()
                return phrase.split()[-1].lower()

            old_key = _key(old_phrase)
            new_details = [
                d for d in new_details
                if not (_detail_kind(d) == old_kind
                        and _key(d) == old_key)]
        self.details.extend(new_details)

        # CULTURAL GROUND (Persona Directive #4) — a faith/culture
        # turn is answered inside the storyteller's own frame, before
        # the generic grief and follow-up paths: their terms echoed,
        # their frame for a death mirrored, an unknown custom met
        # with an ask-to-learn. Detection only chooses the shape.
        culture = _detect_culture(text)
        if culture is not None:
            culture_reply = self._culture_reply(text, culture,
                                                new_details)
            if culture_reply is not None:
                return culture_reply

        # Tender topics: plain, warm, unhurried. If the detail at hand
        # sits behind a boundary, be sorry without opening the door.
        if any(w in lowered for w in _GRIEF_WORDS):
            self.stalls = 0
            who = ""
            if new_details:
                who = new_details[0]
            elif self.details:
                who = self.details[0]
            if who:
                self.followed_details.add(who)
            if who.startswith("your "):
                return ("I am sorry. Losing someone we love stays with us. "
                        "Would you tell me a little about " + who +
                        " — what do you most want people to know?")
            return ("I am sorry. That cannot have been easy. "
                    "Would you like to tell me a little about them?")

        # Every third reply, reach back to an earlier detail (not the one
        # from this message) — the follow-up remembers. Never a detail
        # behind a boundary. Sparingly (Directive #3), the reach-back
        # becomes one of the listening moves: clarity on a detail that
        # was mentioned but never stayed with, or — rarely — a gentle
        # comparison of two moments told at different times.
        earlier = [d for d in self.details
                   if d not in new_details and not self._is_blocked(d)]
        if self.turn % 3 == 0 and earlier:
            self.stalls = 0
            dangling = [d for d in earlier
                        if d not in self.followed_details]
            if dangling:
                detail = dangling[0]
                self.followed_details.add(detail)
                return (self._ack_text() + " Earlier you mentioned "
                        + detail + " — we never really stayed with "
                        "it. What do you remember most about " + detail
                        + "?")
            if (len(earlier) >= 2 and self.turn % 6 == 0
                    and not self._ordinary_compare_done
                    and _detail_kind(earlier[0])
                    != _detail_kind(earlier[-1])):
                self._ordinary_compare_done = True
                return (self._ack_text() + " "
                        + self._compare_move(earlier[0], earlier[-1]))
            detail = earlier[0]
            self.followed_details.add(detail)
            return (self._ack_text() + " Earlier you mentioned " + detail +
                    ". What stayed with you from that?")

        # A fresh detail earns the follow-up — curiosity about the
        # storyteller's own words, one short question.
        if new_details:
            self.stalls = 0
            detail = new_details[0]
            self.followed_details.add(detail)
            return (self._ack_text() + " Tell me more about " + detail +
                    " — what do you remember most about it?")

        # A direct question that fits nowhere else still deserves a
        # real answer (Directive #3): never a bare acknowledgement.
        # Answer honestly, from what the conversation has held.
        if _is_direct_question(lowered):
            return self._reflection_reply()

        # Nothing new to follow. Count the stall. Listening does not
        # need a question every time: the first stall earns a plain,
        # warm acknowledgement and silence to think in.
        self.stalls += 1
        if self.stalls < 2:
            if self._name_eligible():
                self._last_name_turn = self.turn
                return _ACK_ONLY_NAMED[
                    self.turn % len(_ACK_ONLY_NAMED)].format(
                        name=self.preferred_name)
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
        return (self._ack_text() +
                " What else from that time would you like to tell me?")
