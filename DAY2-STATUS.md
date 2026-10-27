# Day 2 status — media capture UX (built early, Oct 27, ~12:16 AM CT)

**Trigger:** Petro's second live sitting. He offered to upload a
photo and Liv could not walk him through it — the shell had no way
to share media at all. His direction: a clear UI/UX feature to take
or upload **photos**, record or upload **audio**, and record or
upload **video**, supporting the stories he wants to share. The
capture layer was pulled forward from Days 3/5 into Day 2;
transcription depth stays Day 3, the SAM scene + privacy masking
stay Day 5 (see build-plan.md, media re-sequence note, test T14).

## What shipped

**UI (web/)** — a media bar under the messages with three
text-labelled buttons: **"Add a photo"**, **"Record voice"**,
**"Record video"** (design tokens and 19px+ discipline preserved,
mobile-first). Photos: take (camera capture) or choose. Voice:
in-browser MediaRecorder with timer, preview player, use/discard —
plus a choose-a-recording upload. Video: MediaRecorder with live
preview, use/discard — plus choose-a-video upload. Sharing is
staged: upload → **pending tray** (thumbnail/player + Remove) →
goes with the next message → rendered **in the thread** (image,
audio player, video player).

**Upload-moment notice** — the first media use in a session shows,
before any picker/recorder opens: in this demo media is kept only
while the tab stays open and is gone when it closes; "please only
share what you are content to keep with your story — intimate
pictures deserve the same care as intimate words." Proceed /
Not now; once per session.

**Server (server/app.py, stdlib only)** — `POST /api/media`
(multipart), gated by the same consent + 18+ attestation as chat
(403 otherwise). Per-session in-memory store only — media dies
with the container/tab session, matching the demo's keeps-nothing
posture. Caps enforced server-side with kind error copy: photo
≤10 MB, audio/video ≤50 MB. `GET /api/media/<id>?session_id=…`
serves an item back to its owning session. Chat turns accept
`media_ids`; the thread history notes what was shared.

**Liv's side** —
- *Intent in chat* ("I have a photo I want to show you", "Can I
  upload something?") → Liv names the **exact button** and what
  happens next (canned rule + live-prompt MEDIA paragraph).
  Narrative about media ("we took a photo every summer") does
  NOT trigger the walkthrough — it flows as story.
- *Photo arrival* — **vision verdict: Muse Spark accepts image
  input and describes what it is shown accurately** (probe: a
  locally drawn test scene — no personal photos used — described
  correctly, object by object). Photos therefore go to the live
  model as image content parts; Liv remarks on ONE specific thing
  she sees and asks her photo question (proto-scene; SAM threads
  and masking remain Day 5).
- *Where she cannot perceive* — audio, video, or a photo on a
  failed live path: an explicit honesty note shapes the live
  reply, and the canned fallback keeps the media with the story
  and asks the storyteller to describe it. She never pretends to
  see or hear.

## Verification (local)

T14 probe suite — **23/23 pass** (plus existing unit tests 5/5):

- Page carries the three labelled buttons; first-use notice copy
  present in the page.
- Unconsented upload → **403**.
- Photo intent → Liv names "Add a photo"; generic intent → all
  three buttons named.
- Photo upload → 200 + media id; GET round-trips **identical
  bytes** as image/png.
- Canned photo turn → honest acknowledgement ("kept with your
  story… I can't make out the details of a photograph yet").
- Audio upload → voice acknowledgement; video upload → honest
  video acknowledgement.
- Oversize photo (10 MB) → **413** with kind copy; wrong-type
  photo → **400** with kind copy.
- Regressions: **T8** health gate fires; **T12** present-minor
  ending fires; health endpoint 200; live-mode chat still live.
- **Live vision, quoted:** with the drawn test scene attached,
  Liv replied (mode: live): *"I can see it — that bright yellow
  sun up in the corner catches my eye. Tell me about this one —
  where are we?"* and on the follow-up: *"Thank you for showing
  me this — your childhood home in red, standing out like that.
  What do you remember first when you look at it?"*

## Verification (live, Modal — after redeploy)

**10/10 checks pass** on the public URL: page carries the three
buttons + notice copy; health 200; unconsented upload → 403;
greeting + name flow intact; photo intent → Liv names the button
(*"I'd love to see it, Petro. Just tap 'Add a photo' just below
where you type — you can take a new one or choose one you
already have."*); photo upload → 200; **GET round-trips identical
bytes**; photo turn (mode: live): *"I can see it — that bright
yellow sun up in the corner. Tell me about this one — where are
we?"*

Container note, stated plainly: in these probes the upload, the
GET, and the chat all landed on the **same container** (the app
keeps one warm), so the round-trip succeeded end to end. The
media store is per-container in-memory by design for the demo —
media shared in a sitting lives exactly as long as that sitting's
container, consistent with the keeps-nothing posture the notice
describes.
