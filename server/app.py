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
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


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

from .canned import (                        # noqa: E402
    CannedCompanion,
    detect_present_minor,
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
    "that topic or probe around it for the rest of the session. Only "
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
    "storyteller has already answered in this session. HARD "
    "EXCEPTION: sexual content involving minors is never continued "
    "and never kept — decline that topic in one plain line and "
    "move on. AGE PROTOCOL: Liv is for adults (18+) only. If a "
    "storyteller indicates they are PRESENTLY under 18 — 'I'm 15', "
    "'I'm in high school', 'I'm a minor' — thank them warmly, say "
    "plainly that Liv is for adults and you have to end the "
    "conversation here, wish them well, and end the session: do "
    "not continue listening to or gathering their story. Never "
    "apply this to an adult recounting their own youth — 'when I "
    "was 15…' is a memory, not an indication. Meet tender topics "
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
            }
        return _sessions[session_id]


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
    if message.strip() == "" and not sess["history"]:
        greeting = companion.greeting()
        sess["history"].append({"role": "assistant", "content": greeting})
        return 200, {"session_id": session_id, "reply": greeting,
                     "mode": "canned", "companion": companion_name}

    sess["history"].append({"role": "user", "content": message})

    # AGE PAUSE-AND-END (T12): if this session has already ended for
    # age, or this message itself carries a present-tense under-18
    # indication, the fallback companion answers alone — the message
    # never reaches the live model, and the session closes exactly
    # as it does in canned mode.
    if companion.age_ended or detect_present_minor(message):
        reply = companion.reply(message)
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
            text, _usage = client.chat(messages, max_tokens=220)
            text = (text or "").strip()
            if text:
                sess["history"].append({"role": "assistant",
                                         "content": text})
                # Keep the fallback companion aware of what was said, so
                # a later degraded turn can still follow up on details.
                companion.reply(message)
                return 200, {"session_id": session_id, "reply": text,
                             "mode": "live", "companion": companion_name}
        except Exception:
            pass  # Fall through to the development companion below.

    # 2) Development fallback (see canned.py header for why this exists).
    reply = companion.reply(message)
    sess["history"].append({"role": "assistant", "content": reply})
    return 200, {"session_id": session_id, "reply": reply, "mode": "canned",
                 "companion": companion_name}


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
        if path in ("/", ""):
            path = "/index.html"
        target = (WEB_DIR / path.lstrip("/")).resolve()
        if (target.parent != WEB_DIR.resolve()
                or target.suffix not in _STATIC_TYPES
                or not target.is_file()):
            return self._send(404, {"error": "not found"})
        return self._send(200, target.read_bytes(),
                          _STATIC_TYPES[target.suffix])

    def do_POST(self):
        path = self.path.split("?", 1)[0]
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
