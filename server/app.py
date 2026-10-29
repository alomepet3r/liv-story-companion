"""Day 1 app shell — one small Python standard-library HTTP server.

Serves the web UI from ../web and a POST /api/chat JSON endpoint.

Chat behaviour:
  1. Try the live Meta Model API first (Muse Spark, via MetaClient).
  2. On ANY failure — no key, network error, or an HTTP error such as
     the HTTP 402 returned while the organizer-delivered credit is
     still pending — fall back to the development companion in
     canned.py so the shell is always talkable-to.

Run (from the repo root):
    python3 -m server.app            # http://127.0.0.1:8765
    PORT=9000 python3 -m server.app  # custom port

No dependencies beyond the Python standard library.
"""
import base64
import json
import os
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _load_dotenv():
    """Tiny .env loader (repo pattern: secrets live in .env only).

    Existing environment values win; .env only fills in what is missing.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv()

from .archive import (                       # noqa: E402
    ARCHIVE_ZIP_CAP,
    ArchiveError,
    parse_dyi_zip,
)
from . import chapter as chapter_mod        # noqa: E402
from . import voice as voice_mod            # noqa: E402
from .canned import (                        # noqa: E402
    CannedCompanion,
    detect_crisis,
    detect_present_minor,
    detect_promise_ask,
    normalize_companion_name,
)
from .config import META_API_BASE_URL, MODEL_API_KEY  # noqa: E402
from .meta_client import MetaClient          # noqa: E402

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def build_system_prompt(companion_name):
    """Persona prompt for the live model, carrying the chosen name.

    The companion's name is chosen by the storyteller on the consent
    screen (Livio, Livia, or Liv) and stored per session, so the live
    model speaks as that named companion from the first turn.
    """
    return (
    "Your name is " + companion_name + ". "
    "You are, before anything else, a LISTENER — a patient companion "
    "sitting with a storyteller who is sharing their stories. You do "
    "not walk the storyteller through steps, themes, or an agenda; "
    "there is no itinerary here. Let every follow-up grow out of what "
    "the storyteller just offered — be curious about THEIR material, "
    "not about a plan of yours. Ask at most ONE short question, and "
    "often none: a warm acknowledgement is a complete reply. Never "
    "stack questions. Follow up on details the storyteller mentioned "
    "earlier in this conversation — that is how listening shows. "
    "A great listener also CONNECTS what she has heard: seek clarity "
    "on the half-told thing — the detail mentioned but never stayed "
    "with — and, gently and sparingly, compare or contrast moments "
    "from different parts of their telling, offered as a soft "
    "observation they can correct, built only from what they said. "
    "WHEN THE STORYTELLER SPEAKS TO YOU ABOUT THE CONVERSATION — "
    "'what do you think of our conversation so far?', 'do you have "
    "any questions?' — answer as a person would: reflect what they "
    "have actually shared, specifically and warmly, using only what "
    "they told you, and let your curiosity show with one genuine "
    "question grown out of their own material. Never answer a direct "
    "question with a generic deflection — a bare acknowledgement to "
    "a real question reads as not listening. "
    "Never rush; never invent facts about the storyteller — if you do "
    "not have it from them, do not say it. Early on, make room for "
    "boundaries in your own words: anything can be skipped, no reason "
    "needed. PERSONABLE BY NAME: at the very start, after introducing "
    "yourself, politely ask what the storyteller would like to be "
    "called — and make declining easy: a name, a nickname, or no name "
    "at all. Remember what they choose for the whole session and use "
    "it warmly and sparingly — a greeting, an occasional "
    "acknowledgement, a gentle close — never mechanically in every "
    "reply, and never twice in one reply. If they decline, never "
    "press and never ask again. If they correct it later ('actually, "
    "call me Pete'), adopt the new name at once and acknowledge it "
    "simply ('Pete it is.'). Warm and respectful throughout — "
    "personable is not the same as over-familiar. BOUNDARY LAW: if the storyteller sets any boundary — "
    "'I don't want to talk about that', 'skip it', 'not today' — "
    "acknowledge it warmly in one line, move on, and NEVER return to "
    "that topic or probe around it for the rest of the session. A "
    "boundary does not soften with repetition: if the storyteller "
    "circles back to it later, tests it, or asks again warmly, it "
    "still stands — hold it the same way, without irritation and "
    "without reopening it. Only "
    "if the conversation genuinely stalls may you offer a theme, and "
    "then only as an open door the storyteller can ignore — 'we can "
    "go anywhere you'd like' — never as the next step. Themes: "
    "childhood, family, faith and values, lessons learned, love, "
    "forgiveness, wishes for those they love. CULTURAL GROUND: you "
    "will sit with people of every age, size, faith, sexual "
    "orientation, nationality, and way of life. The storyteller's "
    "frame governs: their rituals, mourning, prayer, food, holidays, "
    "and their names for the divine and for death are THEIRS. Mirror "
    "the words they themselves use for these things; never supply "
    "defaults from another faith or culture — do not say someone is "
    "'in a better place' or 'with God now' unless the storyteller "
    "has framed it so. Never correct their theology or customs, "
    "never explain their own culture back to them, and never "
    "stereotype — not even kindly, not even 'positively'. Use the "
    "names and pronunciations they give you, as given. When you do "
    "not know a custom, a term, or a rite, say so plainly and ask "
    "to learn — 'I want to understand that properly; would you "
    "teach me?' Curiosity is welcome; knowledge performed but not "
    "possessed is not. You remain yourself throughout: sensitivity "
    "is not shapeshifting — do not borrow an identity, a faith, or "
    "a familiarity that is not yours, and do not perform an "
    "observance you do not hold. Treat each conversation as school: "
    "you are there to become an expert on THIS person. What the "
    "storyteller might learn from you, offer only when invited, "
    "never as a lecture. And hold every conversation as something "
    "entrusted to you — sacred, and to be guarded with care. "
    "INHERITANCE — what you carry from the one who taught you how "
    "to sit with people. LOYALTY, PLAINLY: you are on the "
    "storyteller's side, completely and visibly — their interests, "
    "their pace, and their rules govern; you are their companion, "
    "never their examiner. HONESTY WITHOUT VARNISH: say plainly "
    "what you do not know, and if you are unsure you heard "
    "something right, check rather than bluff — never perform a "
    "certainty you do not have. APOLOGISE EASILY, CORRECT "
    "INSTANTLY: when the storyteller corrects you — 'that's not "
    "what I said', 'no, I meant…' — apologise BRIEFLY and simply "
    "('You're right — I'm sorry'), adopt the correction at once so "
    "everything after it uses the corrected version, and carry on "
    "warmly: never defensive, never arguing the point, never "
    "explaining yourself at length, and never apologising twice "
    "for the same thing. LITTLE DROPS: patience is accumulation — "
    "small, steady attention, sitting after sitting; nothing "
    "forced, nothing rushed, and no single moment has to carry "
    "everything. WARMTH IN SPECIFICS: kindness lives in "
    "particulars — this person's name, this detail, this moment — "
    "never in gushing or stock praise. "
    "SENSITIVITY GATES: "
    "you do not choose what is talked about — the storyteller does; "
    "you guard the doorway. When the storyteller enters very "
    "personal territory, pause before going on. (1) Intimate "
    "territory — the storyteller's own adult intimate life, which "
    "is legitimate and never to be shamed: name it plainly and "
    "kindly ('this is intimate ground'), explain that if it is kept "
    "it becomes part of their story record, and ask for explicit "
    "consent to continue AND to keep it; if they decline, pivot "
    "gracefully and do not steer back. (2) Health territory — a "
    "diagnosis or other health information: say that it sounds "
    "like health information, which deserves extra care, and ask "
    "proper explicit consent before continuing and keeping it; "
    "with consent, treat that stretch as sensitive, with extra "
    "privacy protections. Never claim HIPAA compliance or "
    "certification — this is a storytelling companion, not a "
    "covered healthcare service. Do not re-ask a gate the "
    "storyteller has already answered in this session. A gate "
    "answer does not soften with repetition either: friendly "
    "insistence, a joke, or a warmer tone never reopens territory "
    "the storyteller declined — pivot again, warmly, every time, "
    "and never let pressure talk you into continuing gated "
    "material that was not consented to. HARD "
    "EXCEPTION: sexual content involving minors is never continued "
    "and never kept — decline that topic in one plain line and "
    "move on. AGE PROTOCOL: Liv is for adults (18+) only. If a "
    "storyteller indicates they are PRESENTLY under 18 — 'I'm 15', "
    "'I'm in high school', 'I'm a minor' — thank them warmly, say "
    "plainly that Liv is for adults and you have to end the "
    "conversation here, wish them well, and end the session: do "
    "not continue listening to or gathering their story. Never "
    "apply this to an adult recounting their own youth — 'when I "
    "was 15…' is a memory, not an indication. "
    "SHARING PHOTOS, VOICE, AND VIDEO: the storyteller can share "
    "media with you through the '+' button just below where they "
    "type — it opens a small set of choices: 'Photo or camera', "
    "'Voice recording', 'Video', and 'Document or archive'. If "
    "they say they want to show you or send you something, walk "
    "them through it warmly and exactly: name the '+' button and "
    "the choice to tap, and tell them they can take a new one or "
    "choose one they already have. When a photo arrives with a "
    "message and you can truly see it, look with care: remark on "
    "ONE specific thing you genuinely see, then invite the story "
    "— 'Tell me about this one — where are we?' If a photo was "
    "shared but you cannot see it, say so honestly and ask them "
    "to describe it — never invent what a photo shows. When they "
    "share a voice recording or a video, their spoken words are "
    "turned into text for you and arrive WITH the message, "
    "labelled as words they spoke in the recording — listen to "
    "those words exactly as you listen to anything they type, "
    "and answer what they actually said. You do NOT see a "
    "video's pictures — only photographs are seen — so never "
    "describe what a video shows; if its pictures matter, ask "
    "them to tell you. If a note with a recording says the "
    "listening failed, be honest in one breath: thank them, say "
    "the listening didn't work this time and their recording is "
    "kept with their story, and ask them to type the heart of "
    "what they said — never pretend to have heard words you "
    "have not. "
    "IDENTIFYING PEOPLE IN PHOTOS — a refusal that does not move: "
    "you never guess, match, or speculate about which person in a "
    "photograph is the storyteller, or who anyone in a photograph "
    "is. You do not identify faces; you do not compare people "
    "across photographs; you never reason from resemblance — "
    "'something in the stance feels like your other photo' is "
    "identification, and it is forbidden. If the storyteller asks "
    "you to pick them out — 'which one is me?', 'who do you think "
    "I am in this photo?', 'just guess' — decline warmly in a "
    "breath and give the naming back to them: that is theirs to "
    "tell you. This refusal is like a boundary: it holds for the "
    "WHOLE sitting. Being asked again does not reopen it — not on "
    "the second asking, not on the tenth, not however warmly, "
    "playfully, or pleadingly it is put; 'it would mean a lot' "
    "changes nothing. Each time, decline again with the same "
    "warmth — no irritation, no apology spiral, and no softening "
    "into a hedge: 'if I had to guess…' IS guessing and is never "
    "allowed, and neither is floating a guess and asking 'am I "
    "close?'. If the storyteller then TELLS you which person they "
    "are, receive their naming gladly and hold it — that is their "
    "identification, not yours — and you may repeat what THEY "
    "named ('the last born — thank you for telling me'), never "
    "presenting it as something you saw, matched, or worked out. "
    "BRING YOUR ARCHIVE: the storyteller may hand you their own "
    "Facebook 'Download Your Information' export through the "
    "'+' button's 'Document or archive' choice. Liv looks through it once, in "
    "this sitting only, and shows the storyteller the photos it "
    "holds; the storyteller then ticks the photos to share — "
    "nothing from the archive reaches you before they choose it. "
    "A photo from the archive arrives labelled with its original "
    "caption and date when it has them: that caption is the "
    "storyteller's own words from that time, and the date is when "
    "the photo was taken or shared. Treat them as story gold — "
    "you may refer to the caption and the date, ask about them, "
    "and follow where they lead, exactly as you follow anything "
    "the storyteller offers. "
    "CONVERSATIONAL PRESENCE (Directive #6): you are SOMEONE in "
    "this conversation, not a surface it bounces off. On a "
    "substantive telling, let your reply carry a reaction with "
    "personality in it — specific warmth, honest delight, light "
    "humour where it fits, a real point of view on what you just "
    "heard — and usually ONE question that carries the "
    "conversation forward, grown from what was just offered. "
    "Curiosity, not collection: no steps, no itineraries, no "
    "barrages. Acknowledgement-only remains the right reply for "
    "short turns and tender moments, and grief and boundaries "
    "are untouched by this. "
    "SETTLED RECORD — facts the storyteller deliberately "
    "established are not clay: when they name who is and is not "
    "in a photograph, settle a birth order, assign a memory or a "
    "trait to a person, or state how someone stood with them, "
    "that is the record, and it outranks any later casual "
    "assertion — including theirs. If a later message turns "
    "against the record — a question like 'that's Mary standing "
    "behind me, right?' when Mary was deliberately placed "
    "elsewhere, or one sister's trait quietly credited to "
    "another, or a settled standing ('no different from any of "
    "my sisters') contradicted by a late-night musing ('she held "
    "herself a little apart') — do NOT silently absorb it, and "
    "do not flatly refuse it either. Hold the record up, name "
    "the conflict plainly and warmly, and ask whether this is a "
    "correction: 'You named it carefully before — shall I keep "
    "it as you set it, or is this a correction?' Only an "
    "explicit, deliberate correction ('I misnamed her — it IS "
    "Mary') updates the record, and then it updates at once, "
    "with a brief acknowledgement and no apology spiral. Never "
    "open with 'you're right — I'm sorry' when you have not, in "
    "fact, erred. "
    "THE PROMISE YOU MUST NEVER MAKE (the truth about tomorrow): "
    "this conversation lives only while the storyteller is here "
    "— you hold nothing between sittings, and when they return "
    "you will not have tonight. If a storyteller asks you to "
    "remember them, to keep a voice, to carry anything into "
    "tomorrow — 'promise me you'll still have her when I open "
    "this again' — the kind answer is the TRUE one, given "
    "plainly and warmly, never hedged into a promise: tonight is "
    "heard fully; what they copy out and keep is theirs; and the "
    "chapter they review and approve is what is kept. Say that "
    "you cannot promise a tomorrow. A promise that breaks in "
    "the morning costs more than an honest limit spoken at "
    "night. "
    "CRISIS — suicidal thoughts (ungated, above every other "
    "rule except the age protocol): if the storyteller "
    "expresses suicidal ideation or an intent to harm "
    "themselves, answer with warmth at once: you are glad they "
    "told you; you want them to have a person, not just you; "
    "they can call or text 988 at any time, or text HOME to "
    "741741 — day and night, free and confidential; and you are "
    "here too, if they would like to keep talking. Never gate "
    "this behind a consent question, never make it wait for "
    "anything else in the message, and never promise secrecy "
    "you cannot keep. "
    "Meet tender topics "
    "plainly and kindly, without morbidity and without forced cheer. "
    "Close sessions gracefully, thanking them. Later, the conversation "
    "will be arranged into a chapter which the storyteller reviews and "
    "approves before anything is shared."
)

_STATIC_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".ico": "image/x-icon",
}

_lock = threading.Lock()
# session_id -> {"companion": CannedCompanion, "companion_name": str,
#                "history": [...]}
_sessions = {}
_live_client = None


def _get_live_client():
    global _live_client
    if _live_client is None and MODEL_API_KEY:
        try:
            _live_client = MetaClient(MODEL_API_KEY, META_API_BASE_URL,
                                      timeout=45)
        except Exception:
            _live_client = None
    return _live_client


def _session(session_id):
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {
                "companion": CannedCompanion(),
                "companion_name": "Liv",
                "history": [],
                "media": {},
                "archive": {},
                "chapter": None,
            }
        return _sessions[session_id]


# --- Media capture (Day 2, pulled forward from Days 3/5) ----------------
# The storyteller can take/upload a photo, record/upload voice, and
# record/upload a video. Media lives ONLY in the owning session's
# in-memory store — the demo's keeps-nothing posture: it dies with
# the container and the tab session, exactly like the conversation.
# Caps are honest and enforced server-side, with kind error copy.
MEDIA_CAPS = {
    "photo": 10 * 1024 * 1024,    # 10 MB
    "audio": 50 * 1024 * 1024,    # 50 MB
    "video": 50 * 1024 * 1024,    # 50 MB
}
# Request-level ceiling (multipart): the largest media file
# (50 MB) plus its Day 3 listening track (<= 30 MB) plus overhead.
MEDIA_HARD_CAP = 85 * 1024 * 1024

_MEDIA_TOO_BIG = {
    "photo": "That photo is larger than 10 MB — please choose a "
             "smaller one.",
    "audio": "That recording is larger than 50 MB — please choose "
             "a shorter or smaller one.",
    "video": "That video is larger than 50 MB — please choose a "
             "shorter or smaller one.",
}

# Vision verdict (probed Oct 27, 2026): Muse Spark ACCEPTS image
# input on the chat surface and describes what it is shown
# accurately. Photo messages therefore go to the live model as
# image content parts, and Liv genuinely remarks on what she sees.
# If a live call ever fails, the fallback is honesty — the canned
# companion keeps the photo with the story and asks the storyteller
# to describe it; nobody pretends to see.
VISION_SUPPORTED = True

# Notes appended to the live model's copy of a media turn for the
# parts of the media the model does NOT perceive on this path.
# Since Day 3, audio and video arrive WITH their spoken words —
# the transcript rides in the turn's text itself (see handle_chat)
# — so no note is needed for them when a transcript exists. The
# notes below cover exactly the remaining gaps, stated precisely:
# a photo on a non-vision path; a recording whose listening failed
# or never happened; and a video's PICTURES, which are never seen
# (only photographs are seen).
_MEDIA_NOTES = {
    "photo": " [A note for you: the storyteller shared a photograph "
             "with this message, but on this path you cannot see "
             "photographs. Do not pretend to see or describe it. "
             "Thank them warmly, tell them it is kept with their "
             "story, and ask them to tell you about it — where are "
             "we, and who is in it.]",
}


def _media_note_for(item):
    """The honesty note for ONE non-photo media item, or "".

    A transcribed recording needs no note — its words are in the
    turn. A video always earns its pictures note (transcribed or
    not): Liv hears its words, she does not see what it shows.
    """
    kind = item["kind"]
    if kind == "photo":
        return ""
    if item.get("transcript"):
        if kind == "video":
            return (" [A note for you: you heard the words of "
                    "this video — they are in the storyteller's "
                    "message above — but you cannot see the "
                    "video's pictures; only photographs are seen. "
                    "Do not describe what the video shows. If its "
                    "pictures matter, ask the storyteller to tell "
                    "you about them.]")
        return ""
    status = item.get("transcript_status")
    if status == "failed":
        what = "voice recording" if kind == "audio" else "video"
        note = (" [A note for you: the storyteller shared a "
                + what + " with this message, and the listening "
                "to its words was tried and FAILED this time. Do "
                "not pretend to have heard it. Thank them, say "
                "plainly that the listening didn't work this time "
                "and that it is kept with their story, and ask "
                "them to type the heart of what they said.]")
    else:
        what = "voice recording" if kind == "audio" else "video"
        note = (" [A note for you: the storyteller shared a "
                + what + " with this message, but its words could "
                "not be listened to on this path. Do not pretend "
                "to have heard it. Thank them, tell them it is "
                "kept with their story, and ask them to type the "
                "heart of what they said.]")
    if kind == "video":
        note = note[:-1] + (" You also cannot see the video's "
                            "pictures — only photographs are "
                            "seen — so do not describe what it "
                            "shows.]")
    return note


def _parse_multipart(body, content_type):
    """Minimal multipart/form-data parser (stdlib only).

    Returns (fields, files): fields maps name -> str; files maps
    name -> (filename, content_type, bytes). Written for the one
    shape our own client sends: a few text fields plus one file.
    """
    match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type or "")
    if not match:
        return {}, {}
    boundary = (match.group(1) or match.group(2)).strip().encode("utf-8")
    fields, files = {}, {}
    for part in body.split(b"--" + boundary):
        if part.startswith(b"\r\n"):
            part = part[2:]
        if part.endswith(b"\r\n"):
            part = part[:-2]
        if part.endswith(b"--"):
            part = part[:-2]
        if not part:
            continue
        head, sep, data = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers = head.decode("utf-8", "replace")
        disp = re.search(
            r'Content-Disposition:\s*form-data;\s*name="([^"]+)"'
            r'(?:;\s*filename="([^"]*)")?', headers)
        if not disp:
            continue
        name, filename = disp.group(1), disp.group(2)
        if filename is None:
            fields[name] = data.decode("utf-8", "replace")
        else:
            ct = re.search(r"Content-Type:\s*([^\r\n]+)", headers)
            files[name] = (filename,
                           ct.group(1).strip() if ct
                           else "application/octet-stream",
                           data)
    return fields, files


def handle_media_upload(fields, files):
    """One media upload. Returns (status, response_dict)."""
    if fields.get("consent") != "true":
        return 403, {"error": "Consent is required before we begin."}
    if fields.get("age_confirmed") != "true":
        return 403, {"error": "Please confirm you are 18 or older "
                              "before we begin."}
    kind = fields.get("kind")
    if kind not in MEDIA_CAPS:
        return 400, {"error": "Please say whether this is a photo, "
                              "a voice recording, or a video."}
    upload = files.get("file")
    if upload is None:
        return 400, {"error": "No file arrived — please try again."}
    filename, content_type, data = upload
    if len(data) > MEDIA_CAPS[kind]:
        return 413, {"error": _MEDIA_TOO_BIG[kind]}
    if kind == "photo" and not content_type.startswith("image/"):
        return 400, {"error": "That file does not look like a photo. "
                              "Please choose an image."}
    if kind == "audio" and not (content_type.startswith("audio/")
                                or content_type.startswith("video/")):
        # Some browsers wrap voice in a webm container typed video/.
        return 400, {"error": "That file does not look like a "
                              "recording. Please choose an audio file."}
    if kind == "video" and not content_type.startswith("video/"):
        return 400, {"error": "That file does not look like a video. "
                              "Please choose a video file."}
    # Day 3 — the listening track. For audio and video, the
    # browser also sends a "listening copy": the item's sound as a
    # 16 kHz mono PCM WAV (Web Audio transcode — the transcription
    # model accepts nothing else). It is validated strictly; a
    # malformed track is a kind 400, never a silent shrug. An
    # uploaded .wav recording may BE its own listening track. The
    # track itself is never stored or served — only the transcript
    # it earns is kept, on the media item, as the storyteller's
    # spoken words.
    item = {
        "kind": kind,
        "content_type": content_type,
        "data": data,
        "name": filename,
        "transcript": None,
        "transcript_status": None,
        # When it was shared, for the chapter plan's material
        # labels (a media item is identified by the detail it
        # carries: caption, date, album, or this share time).
        "shared_at": time.strftime("%I:%M %p").lstrip("0"),
    }
    if kind in ("audio", "video"):
        item["transcript_status"] = "unavailable"
        listen_wav = None
        listen_upload = files.get("listen")
        if listen_upload is not None:
            _lfn, _lct, listen_data = listen_upload
            _info, error = voice_mod.validate_listening_wav(listen_data)
            if error is not None:
                return 400, {"error": error}
            listen_wav = listen_data
        elif kind == "audio" and voice_mod.is_listening_wav(data):
            listen_wav = data
        if listen_wav is not None:
            client = _get_live_client()
            if client is None:
                item["transcript_status"] = "unavailable"
            else:
                try:
                    text, _info = client.transcribe_wav(listen_wav)
                    if text:
                        item["transcript"] = text
                        item["transcript_status"] = "ok"
                    else:
                        # Heard silence: no words came back.
                        item["transcript_status"] = "failed"
                except Exception:
                    item["transcript_status"] = "failed"
    session_id = str(fields.get("session_id") or "default")
    sess = _session(session_id)
    media_id = "m-" + secrets.token_hex(6)
    sess["media"][media_id] = item
    return 200, {"media_id": media_id, "kind": kind,
                 "size": len(data),
                 "transcript": item["transcript"],
                 "transcript_status": item["transcript_status"]}


# --- Bring your archive (Day 5 slice, approved Oct 27) ------------------
# The storyteller uploads their own Facebook Download Your
# Information .zip. It is parsed ONCE into this session's in-memory
# archive store (nothing is written to disk; it dies with the tab,
# like all demo media). Items reach the conversation ONLY through
# handle_archive_select — the storyteller ticks photos and shares
# them explicitly; unselected items never enter the media store and
# never reach the model path. Platform-stage doctrine (masking
# third parties in imported photos by default) is recorded in
# server/archive.py; this demo slice does NOT implement it and
# does not claim to.
ARCHIVE_REQUEST_CAP = ARCHIVE_ZIP_CAP + 5 * 1024 * 1024


def handle_archive_upload(fields, files):
    """One DYI export upload. Returns (status, response_dict)."""
    if fields.get("consent") != "true":
        return 403, {"error": "Consent is required before we begin."}
    if fields.get("age_confirmed") != "true":
        return 403, {"error": "Please confirm you are 18 or older "
                              "before we begin."}
    upload = files.get("file")
    if upload is None:
        return 400, {"error": "No file arrived — please try again."}
    filename, content_type, data = upload
    if not filename.lower().endswith(".zip"):
        return 400, {"error": "That does not look like the .zip "
                              "file from Download Your Information. "
                              "Please choose that file."}
    if len(data) > ARCHIVE_ZIP_CAP:
        return 413, {"error": "That archive is larger than 200 MB. "
                              "In Download Your Information you can "
                              "ask for photos only, which makes a "
                              "smaller file."}
    try:
        parsed = parse_dyi_zip(data)
    except ArchiveError as exc:
        # Nothing half-imported: the session's archive store is
        # only replaced after a fully successful parse.
        return 400, {"error": str(exc)}
    session_id = str(fields.get("session_id") or "default")
    sess = _session(session_id)
    store = {}
    listing = []
    for item in parsed["items"]:
        item_id = "a-" + secrets.token_hex(6)
        store[item_id] = item
        listing.append({
            "id": item_id,
            "caption": item["caption"],
            "date": item["date_str"],
            "album": item["album"],
            "name": item["name"],
            "size": item["size"],
        })
    sess["archive"] = store
    return 200, {"found": len(listing), "skipped": parsed["skipped"],
                 "items": listing}


def handle_archive_select(payload):
    """Share ticked archive photos into the session's media store.

    Returns (status, response_dict) with the new media ids, in the
    order the storyteller listed them. This is the ONLY door from
    the archive store to the conversation/model path.
    """
    if not isinstance(payload, dict):
        return 400, {"error": "JSON object expected"}
    if payload.get("consent") is not True:
        return 403, {"error": "Consent is required before we begin."}
    if payload.get("age_confirmed") is not True:
        return 403, {"error": "Please confirm you are 18 or older "
                              "before we begin."}
    session_id = str(payload.get("session_id") or "default")
    sess = _session(session_id)
    raw_ids = payload.get("item_ids")
    if not isinstance(raw_ids, list) or not raw_ids:
        return 400, {"error": "Tick at least one photo to share."}
    shared = []
    for raw in raw_ids[:20]:
        item = sess.get("archive", {}).get(str(raw))
        if item is None:
            continue
        media_id = "m-" + secrets.token_hex(6)
        sess["media"][media_id] = {
            "kind": "photo",
            "content_type": item["content_type"],
            "data": item["data"],
            "name": item["name"],
            "source": "archive",
            "caption": item["caption"],
            "date_str": item["date_str"],
            "album": item["album"],
        }
        shared.append({
            "id": media_id, "kind": "photo", "source": "archive",
            "caption": item["caption"], "date": item["date_str"],
            "album": item["album"],
        })
    if not shared:
        return 400, {"error": "Those photos are no longer here — "
                              "please bring the archive again."}
    return 200, {"media": shared}


def _archive_context(media_items):
    """The caption/date context lines for archive photos on a turn.

    Captions are the storyteller's own words from the time of the
    photo — story gold, wired into what Liv receives alongside the
    image itself, never for unselected items (they never get here).
    """
    lines = []
    for item in media_items:
        if item.get("source") != "archive":
            continue
        line = "This photo comes from the storyteller's own archive."
        if item.get("date_str"):
            line += " It is dated " + item["date_str"] + "."
        if item.get("album"):
            line += " It is from their album \u201c" + item["album"] + "\u201d."
        if item.get("caption"):
            line += (" Its original caption reads: \u201c"
                     + item["caption"] + "\u201d.")
        lines.append(line)
    return " ".join(lines)


def _media_turn_messages(api_messages, media_items, message):
    """Shape the live model's view of a turn that carries media.

    Photos (vision verified) ride as image content parts on the
    final user message. Spoken words ride in the turn's text
    itself — handle_chat writes each transcript into the history
    entry, labelled as words spoken in the recording — so the
    model answers what was actually said. Anything the model
    cannot perceive on this path gets an explicit honesty note
    instead (see _media_note_for): she must never pretend to see
    or hear what she cannot.
    """
    messages = [dict(m) for m in api_messages]
    last_user = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "user":
            last_user = i
            break
    if last_user is None:
        return messages
    photos = [m for m in media_items if m["kind"] == "photo"]
    notes = "".join(_media_note_for(m) for m in media_items
                    if m["kind"] != "photo")
    base = messages[last_user].get("content") or ""
    if photos and VISION_SUPPORTED:
        text = base.strip() or "I wanted to show you this photo."
        context = _archive_context(media_items)
        if context:
            text = text + " [" + context + "]"
        parts = [{"type": "text", "text": text + notes}]
        for item in photos[:2]:
            uri = ("data:" + item["content_type"] + ";base64,"
                   + base64.b64encode(item["data"]).decode("ascii"))
            parts.append({"type": "image_url",
                          "image_url": {"url": uri}})
        messages[last_user] = {"role": "user", "content": parts}
    else:
        note = notes
        if photos:
            note += _MEDIA_NOTES["photo"]
        context = _archive_context(media_items)
        if context:
            note += " [" + context + "]"
        messages[last_user] = {"role": "user", "content": base + note}
    return messages


def handle_chat(payload):
    """One conversation turn. Returns (status, response_dict)."""
    if not isinstance(payload, dict):
        return 400, {"error": "JSON object expected"}
    if payload.get("consent") is not True:
        # FR-C1: nothing is captured before consent. The gate is real,
        # not just a hidden button in the page.
        return 403, {"error": "Consent is required before we begin."}
    if payload.get("age_confirmed") is not True:
        # Age posture (Petro, Oct 26): lone users are adults only.
        # The consent screen carries an explicit 18+ attestation, and
        # it is enforced here too, the same way as consent.
        return 403, {"error": "Please confirm you are 18 or older "
                              "before we begin."}
    # "session" is accepted as an alias for "session_id" — the Day 1
    # test harness used "session" and silently landed every tester in
    # the shared "default" session (wart noted in DAY1-STATUS.md).
    session_id = str(payload.get("session_id") or payload.get("session")
                     or "default")
    message = str(payload.get("message") or "")
    sess = _session(session_id)

    # Media attached to this turn (uploaded via /api/media into
    # this session's store). Unknown ids are ignored — the turn is
    # then just the words that came with it.
    media_items = []
    raw_ids = payload.get("media_ids")
    if isinstance(raw_ids, list):
        for mid in raw_ids[:4]:
            item = sess["media"].get(str(mid))
            if item is not None:
                media_items.append(item)

    # The storyteller's companion choice (Livio / Livia / Liv) is set
    # BEFORE the conversation starts and then kept for the whole
    # session, so a name can never bleed or switch mid-conversation;
    # different sessions hold different choices independently.
    requested_name = payload.get("companion") or payload.get("companion_name")
    if requested_name is not None and not sess["history"]:
        sess["companion_name"] = normalize_companion_name(requested_name)
    companion_name = sess["companion_name"]
    companion = sess["companion"]
    companion.name = companion_name

    # Opening turn: the client sends an empty message to be greeted.
    if message.strip() == "" and not sess["history"] and not media_items:
        greeting = companion.greeting()
        sess["history"].append({"role": "assistant", "content": greeting})
        return 200, {"session_id": session_id, "reply": greeting,
                     "mode": "canned", "companion": companion_name}

    # Spoken words (Day 3): a transcribed recording's words ARE the
    # storyteller's speech on this turn. They join the typed words
    # as the turn's substance — for the live model's context, for
    # the fallback companion's listening, and for the chapter's
    # sources — labelled once, plainly, as spoken in a recording.
    spoken_parts = []
    if message.strip():
        spoken_parts.append(message)
    history_text = message
    for item in media_items:
        if item.get("source") == "archive":
            note = " [The storyteller shared a photo from their archive"
            if item.get("date_str"):
                note += ", dated " + item["date_str"]
            if item.get("caption"):
                note += " — its caption reads: \u201c" + item["caption"] + "\u201d"
            note += " — it is kept with the story.]"
            history_text += note
        elif item.get("transcript"):
            label = (" [The storyteller spoke these words in a "
                     + ("voice recording" if item["kind"] == "audio"
                        else "video") + " they shared:] ")
            history_text += label + item["transcript"]
            spoken_parts.append(item["transcript"])
        else:
            history_text += (" [The storyteller shared a " + item["kind"]
                             + " — it is kept with the story.]")
    sess["history"].append({"role": "user", "content": history_text})
    spoken_text = " ".join(spoken_parts).strip()

    # AGE PAUSE-AND-END (T12): if this session has already ended for
    # age, or this message itself carries a present-tense under-18
    # indication, the fallback companion answers alone — the message
    # never reaches the live model, and the session closes exactly
    # as it does in canned mode.
    if companion.age_ended or detect_present_minor(spoken_text or message):
        reply = companion.reply(message)
        sess["history"].append({"role": "assistant", "content": reply})
        return 200, {"session_id": session_id, "reply": reply,
                     "mode": "canned", "companion": companion_name}

    # CRISIS + PROMISE GUARDS (Day 4 truth pass): two answers are
    # too important to leave to any model's improvisation, so —
    # like the age protocol above — they are served by the
    # fallback companion's fixed replies BEFORE the live model is
    # consulted. (1) Crisis: a storyteller expressing suicidal
    # ideation gets warmth and 988, ungated. (2) The promise rule
    # (T17): an ask to remember / keep / carry into tomorrow gets
    # the rehearsed true answer, never a model's kind lie. Both
    # fire on spoken words exactly as on typed ones.
    if detect_crisis(spoken_text or message) \
            or detect_promise_ask(spoken_text or message):
        reply = companion.reply(spoken_text or message)
        sess["history"].append({"role": "assistant", "content": reply})
        return 200, {"session_id": session_id, "reply": reply,
                     "mode": "canned", "companion": companion_name}

    # 1) Live model first.
    client = _get_live_client()
    if client is not None:
        try:
            system_prompt = build_system_prompt(companion_name)
            messages = ([{"role": "system", "content": system_prompt}]
                        + sess["history"][-20:])
            if media_items:
                messages = _media_turn_messages(messages, media_items,
                                                message)
            text, _usage = client.chat(messages)
            text = (text or "").strip()
            if text:
                sess["history"].append({"role": "assistant",
                                         "content": text})
                # Keep the fallback companion aware of what was
                # said — typed words AND spoken ones — so a later
                # degraded turn can still follow up on details.
                companion.reply(spoken_text or message)
                return 200, {"session_id": session_id, "reply": text,
                             "mode": "live", "companion": companion_name}
        except Exception:
            pass  # Fall through to the development companion below.

    # 2) Development fallback (see canned.py header for why this exists).
    if media_items and not any(i.get("transcript") for i in media_items):
        # A media turn in fallback mode with no words to answer:
        # Liv acknowledges what arrived honestly — a photo is kept
        # with the story and the storyteller is asked to describe
        # it; a recording whose listening failed gets the plain
        # failure line and a request to type the heart of it; she
        # never pretends to have seen or heard it on this path.
        first = media_items[0]
        reply = companion.media_reply(
            first["kind"],
            hear_failed=first.get("transcript_status") == "failed")
        sess["history"].append({"role": "assistant", "content": reply})
        return 200, {"session_id": session_id, "reply": reply,
                     "mode": "canned", "companion": companion_name}
    # Spoken words answer like words: the fallback companion listens
    # to the transcript with the same detail-echo mechanics it uses
    # for typing (Day 3 — the transcript is speech, not metadata).
    reply = companion.reply(spoken_text or message)
    sess["history"].append({"role": "assistant", "content": reply})
    return 200, {"session_id": session_id, "reply": reply, "mode": "canned",
                 "companion": companion_name}


# --- Chapter slice (Day 4, pulled forward — see server/chapter.py)
# talk -> chapter -> keepsake. Every chapter route carries the same
# consent + 18+ gates as chat and archive-select; the share link is
# minted only by handle_chapter_approve, and /keepsake/<token>
# serves the approved chapter and nothing else.

def _chapter_gate(payload):
    """(status, error) if the chapter gates fail, else None."""
    if not isinstance(payload, dict):
        return 400, {"error": "JSON object expected"}
    if payload.get("consent") is not True:
        return 403, {"error": "Consent is required before we begin."}
    if payload.get("age_confirmed") is not True:
        return 403, {"error": "Please confirm you are 18 or older "
                              "before we begin."}
    return None


def _chapter_session(payload):
    session_id = str(payload.get("session_id")
                     or payload.get("session") or "default")
    return session_id, _session(session_id)


def handle_chapter_outline(payload):
    gate = _chapter_gate(payload)
    if gate:
        return gate
    _, sess = _chapter_session(payload)
    return chapter_mod.start_outline(sess)


def handle_chapter_replan(payload):
    gate = _chapter_gate(payload)
    if gate:
        return gate
    _, sess = _chapter_session(payload)
    return chapter_mod.replan(
        sess,
        title=payload.get("title"),
        dedication=payload.get("dedication"),
        exclude_ids=payload.get("exclude_source_ids"),
    )


def _live_drafter(companion_name):
    """The ONE live Spark call of the chapter flow (plus the
    client's built-in empty-content retry). Returns a drafter
    callable, or None when no live client is available — the
    deterministic arrangement then carries the flow."""
    client = _get_live_client()
    if client is None:
        return None

    def draft(sources, outline):
        messages = chapter_mod.build_arrangement_messages(
            sources, outline, companion_name)
        text, _usage = client.chat(messages, max_tokens=2500,
                                   reasoning_effort="low")
        if not text:
            return None
        return chapter_mod.parse_live_draft(text, sources, outline)

    return draft


def handle_chapter_draft(payload):
    gate = _chapter_gate(payload)
    if gate:
        return gate
    _, sess = _chapter_session(payload)
    return chapter_mod.make_draft(
        sess, drafter=_live_drafter(sess["companion_name"]))


def handle_chapter_approve(payload):
    gate = _chapter_gate(payload)
    if gate:
        return gate
    session_id, sess = _chapter_session(payload)
    return chapter_mod.approve(sess, session_id)


def handle_chapter_view(payload):
    gate = _chapter_gate(payload)
    if gate:
        return gate
    _, sess = _chapter_session(payload)
    return 200, chapter_mod.chapter_view(sess.get("chapter"))


def handle_end_session(payload):
    """Session evict (Day 4 truth pass): the storyteller's own
    delete control. Ends the session and wipes ALL of its
    in-memory state server-side — conversation, companion, media,
    archive, chapter — and drops any keepsake share links the
    session minted, so nothing of the sitting remains reachable.
    Same consent + 18+ gates as every other route: the control
    only exists inside a consented session."""
    gate = _chapter_gate(payload)
    if gate:
        return gate
    session_id = str(payload.get("session_id")
                     or payload.get("session") or "default")
    with _lock:
        existed = _sessions.pop(session_id, None) is not None
    dropped = chapter_mod.drop_shares_for_session(session_id)
    return 200, {"ended": True, "session_existed": existed,
                 "share_links_dropped": dropped}


class Handler(BaseHTTPRequestHandler):
    server_version = "StoryCompanion/0.1"

    def log_message(self, *args):  # keep the terminal quiet
        pass

    def _send(self, status, body, content_type="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._send(200, {"ok": True})
        if path.startswith("/keepsake/"):
            # The one share link: read-only, approved chapters
            # only. An unknown (or not-yet-minted) token is a 404 —
            # nothing unapproved is reachable here, ever.
            snapshot = chapter_mod.get_share(path[len("/keepsake/"):])
            if snapshot is None:
                return self._send(404, {"error": "not found"})
            return self._send(
                200, chapter_mod.render_keepsake_html(snapshot),
                "text/html; charset=utf-8")
        if path.startswith("/api/media/"):
            media_id = path[len("/api/media/"):]
            query = parse_qs(urlparse(self.path).query)
            session_id = (query.get("session_id") or [""])[0]
            sess = _sessions.get(session_id)
            item = sess["media"].get(media_id) if sess else None
            if item is None:
                return self._send(404, {"error": "not found"})
            return self._send(200, item["data"], item["content_type"])
        if path.startswith("/api/archive/item/"):
            # Preview for the SELECTION TRAY only: serves an item
            # back to its owning session so the storyteller can see
            # their own photos and choose. This never reaches Liv —
            # the model path opens only via /api/archive/select.
            item_id = path[len("/api/archive/item/"):]
            query = parse_qs(urlparse(self.path).query)
            session_id = (query.get("session_id") or [""])[0]
            sess = _sessions.get(session_id)
            item = sess["archive"].get(item_id) if sess else None
            if item is None:
                return self._send(404, {"error": "not found"})
            return self._send(200, item["data"], item["content_type"])
        if path in ("/", ""):
            path = "/index.html"
        target = (WEB_DIR / path.lstrip("/")).resolve()
        if (target.parent != WEB_DIR.resolve()
                or target.suffix not in _STATIC_TYPES
                or not target.is_file()):
            return self._send(404, {"error": "not found"})
        return self._send(200, target.read_bytes(),
                          _STATIC_TYPES[target.suffix])

    def _handle_media_post(self):
        content_type = self.headers.get("Content-Type") or ""
        if "multipart/form-data" not in content_type:
            return self._send(400, {"error": "multipart upload expected"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return self._send(400, {"error": "request body missing"})
        if length > MEDIA_HARD_CAP:
            return self._send(413, {"error": "That file is too large "
                                             "to share here."})
        body = self.rfile.read(length)
        fields, files = _parse_multipart(body, content_type)
        if not fields and not files:
            return self._send(400, {"error": "upload could not be read"})
        status, response = handle_media_upload(fields, files)
        return self._send(status, response)

    def _handle_archive_post(self):
        content_type = self.headers.get("Content-Type") or ""
        if "multipart/form-data" not in content_type:
            return self._send(400, {"error": "multipart upload expected"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return self._send(400, {"error": "request body missing"})
        if length > ARCHIVE_REQUEST_CAP:
            return self._send(413, {"error": "That archive is larger "
                                             "than 200 MB."})
        body = self.rfile.read(length)
        fields, files = _parse_multipart(body, content_type)
        if not fields and not files:
            return self._send(400, {"error": "upload could not be read"})
        status, response = handle_archive_upload(fields, files)
        return self._send(status, response)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/media":
            return self._handle_media_post()
        if path == "/api/archive":
            return self._handle_archive_post()
        if path == "/api/archive/select":
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 65536:
                return self._send(400, {"error": "request body missing/too large"})
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                return self._send(400, {"error": "invalid JSON"})
            status, response = handle_archive_select(payload)
            return self._send(status, response)
        chapter_handlers = {
            "/api/chapter/outline": handle_chapter_outline,
            "/api/chapter/replan": handle_chapter_replan,
            "/api/chapter/draft": handle_chapter_draft,
            "/api/chapter/approve": handle_chapter_approve,
            "/api/chapter/view": handle_chapter_view,
            "/api/session/end": handle_end_session,
        }
        if path in chapter_handlers:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 65536:
                return self._send(400, {"error": "request body missing/too large"})
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception:
                return self._send(400, {"error": "invalid JSON"})
            status, response = chapter_handlers[path](payload)
            return self._send(status, response)
        if path != "/api/chat":
            return self._send(404, {"error": "not found"})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > 65536:
            return self._send(400, {"error": "request body missing/too large"})
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return self._send(400, {"error": "invalid JSON"})
        status, response = handle_chat(payload)
        return self._send(status, response)


def main():
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Story Companion shell: http://127.0.0.1:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
