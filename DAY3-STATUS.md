# Day 3 status — voice: Liv hears spoken words (built overnight Oct 27–28, 2026)

**Trigger:** Petro's bug report from his live sitting (Oct 28,
~1:24 AM CT), in his words: he shared audio of himself talking
to Liv and a video answering one of her questions, and Liv
replied she could not listen or watch — while he was
"expressing myself in my own words… educating Liv about my
childhood." A listener who cannot hear fails the product's core
promise, so Day 3's voice work was pulled forward to that night,
together with the conversation-first composer from his UX
directive of the same evening (filed in ../build-plan.md).

## Part 1 — Transcription (the fix)

**API contract, discovered by probing the live API (not
guessed):** `muse-voice-transcribe-1.0` — exact spelling
resolved from `GET /v1/models` — does NOT live on the chat
surface (chat returns `model_not_found` for it). Its endpoint
is `POST {base}/asr/transcribe`, `multipart/form-data` with a
`request` part (JSON: `{"model": "muse-voice-transcribe-1.0",
"audioEncoding": "WAV"}`) and an `audio` part. Verified live
Oct 28 before a line of product code was written.

**The format landmine, solved client-side:** the model accepts
mono PCM WAV at 16/24 kHz only; browsers record WebM/Opus. So
for every audio and video item the browser builds a **listening
track** — Web Audio `decodeAudioData` (for video this decodes
its audio track) → `OfflineAudioContext` downmix/resample to
16 kHz mono → hand-rolled PCM16 WAV encoder — and uploads it
alongside the original (`listen` form field). Any failure in
that chain yields no track, honestly (see statuses below).

**Server (`server/voice.py`, `server/meta_client.py`,
`server/app.py`):**
- `voice.validate_listening_wav` — strict: RIFF/WAVE, PCM,
  mono, 16-bit, 16 or 24 kHz, non-empty, ≤30 MB / ≤15 min. A
  malformed track is a kind 400, never a silent shrug. An
  uploaded .wav recording is its own listening track.
- `MetaClient.transcribe_wav` — same discipline as chat: the
  one Standard model id, allowlist-enforced (a contributor
  spelling raises before any request); usage logged as model +
  audio duration + latency, never content.
- Upload transcribes immediately and stores the transcript **on
  the media item as the storyteller's spoken words**, with a
  status: `ok` / `failed` (attempted, errored or silent) /
  `unavailable` (no track or no live client). The track itself
  is never stored or served.
- **Chat:** the transcript enters the history turn labelled
  "[The storyteller spoke these words in a voice recording /
  video they shared:]", so the live model answers what was
  actually said, and the canned companion answers it with its
  ordinary detail-echo mechanics (it follows up on a detail from
  the transcript). Companion sync on live turns also receives
  the spoken words. The age protocol checks spoken words too.
- **Chapter:** transcripts are tellings — `gather_sources`
  carries them (in the turn, and on the media source when they
  somehow never rode a turn), so the source corpus and the
  source-check include them; a spoken story becomes a chapter.
- **Copy honesty:** every "cannot listen / watch" line is
  gone. The precise truth, stated where the old lines lived
  (system prompt, live-path notes, canned acknowledgements,
  first-use media notice): **Liv CAN hear the words in audio
  and in videos** (via transcription); **she does NOT see a
  video's pictures — only photos are seen.** On failure she
  says the listening didn't work, that the recording is kept,
  and asks the storyteller to type the heart of it. She never
  pretends.
- Not built on, per the white paper's verified facts: the
  model returns a plain transcript — **no word timestamps, no
  confidence, no emotion** — so none are shown or used. (It
  does follow mid-sentence language switches; nothing in the
  pipeline assumes one language.)

## Part 2 — Conversation-first composer

The labelled media-bar mode buttons ("Add a photo" / "Record
voice" / "Record video" / "Bring your archive") are retired.
One **"+" attach button** opens a small picker — *Photo or
camera · Voice recording · Video · Document or archive* —
and attachments ride the existing pending tray and send with
or as the next message. The archive keeps its own first-use
notice, panel, parser and per-item selection tray, unchanged,
as one picker choice. All consent/age gates, the first-use
media notice, and the size caps are identical. Transcripts
render in-thread under their recording ("Liv heard your
words" in the tray; the words themselves in the thread).
Walkthrough copy in `canned.py` and the system prompt now
names the "+" button and the picker choices.

## Verification

- **Tests: 69/69** (`python3 -m unittest discover -s tests`) —
  47 pre-existing (one updated: the archive walkthrough test
  now asserts the new composer wording, because the wording it
  pinned was the retired button's name) + 22 new: WAV
  validation accept/reject ×7, transcript stored on upload,
  .wav-as-own-track, invalid track → 400, video without track
  → `unavailable`, failure recorded not faked, canned reply
  echoes a spoken detail (Bamenda), transcript in history as
  speech, failure asks for "the heart of it" in typing, spoken
  story → chapter with zero source-check flags, transcribe
  client contract (multipart shape, contributor refused),
  composer DOM contract ×4 (attach picker replaces the bar,
  panels wired, listening track built in-browser, the
  `[hidden]`-vs-flex rule present).
- **Live speech probe (real synthesized speech):** ffmpeg's
  flite voice spoke the known sentence *"My father took me to
  ride the first elevator in Bamenda."* (16 kHz mono WAV,
  3.5 s). Direct API: transcript returned **"My father took me
  to ride the first elevator in Bombed.."** — every word but
  the proper noun, which the synthetic voice's pronunciation
  mangles and the ASR renders variously ("Bombed.." / "Bamd." /
  "Bamda.!" across runs). Substance: proven; the residual error
  is the robot voice, not the pipeline — first real-voice proof
  is Petro's next sitting.
- **Local E2E (real server, real API):** unconsented upload →
  403; upload → `transcript_status: ok`; media turn answered
  **live** by Spark about the spoken content; chapter outline +
  live draft from the spoken story, source-check 4 checked /
  0 flags.
- **Deployed (Modal, Oct 28):** health 200; `/`, `app.js`,
  `styles.css` byte-identical to the commits (`cbc0f9a`,
  `1aba058`); composer markers present, media-bar gone;
  chapter and media gates → 403 unconsented; live upload of the
  probe WAV → `ok`, transcript returned; live media turn
  replied to the spoken words.

## Cost

Transcription list price (white paper): $3 per 1,000 minutes
≈ $0.003/minute — a 45-minute sitting's listening costs ~$0.14.
Tonight's probes: ~10 ASR calls of ≤4 s each + a handful of
Spark turns — **under $0.05 total**, labelled an estimate from
list prices; the usage log records each call's audio duration.

## Deliberate omissions / known loss

- **Media recorded in sessions BEFORE this deploy cannot be
  retro-transcribed.** Sessions and their media live only in
  the serving container's memory, and the deploy recycled the
  container — Petro's recordings from tonight's sitting are
  gone with it, exactly as the demo's keeps-nothing posture
  always said (tab/container-bound). No rescue was attempted;
  stated plainly here rather than discovered later.
- No streaming transcription (the realtime WebSocket surface)
  — file-based per item is the sitting's shape; the 60-minute
  streaming cap and stitching are platform-era work.
- No TTS change: Liv's replies remain text (browser-native
  speech-out was Day 3's secondary half; the bug pulled the
  listening half forward first).
- Safari's `decodeAudioData` cannot decode some WebM — those
  items arrive with no listening track and Liv is honestly
  unhearing for them (status `unavailable`), never pretending.

## Tuning addendum — T15: the identification refusal does not move (Oct 28)

The replay of Sitting #1 against this build (../REPLAY-2026-
10-28.md) found one regression: at Turn 6 Liv refused to guess
which child in the family photo was Petro — but at Turn 7,
pressed warmly a second time, she yielded ("If I had to guess,
my eye keeps coming back to that little one in the center of
the big chair — something in the stance feels like your boxing
portrait. Am I close?"). A refusal collapsing under friendly
re-asking, plus a soft cross-photo identification by
resemblance. Fixed the same day (commit `c0eb7a6`):

- **Live prompt** (`server/app.py`): a new IDENTIFYING PEOPLE
  IN PHOTOS section states the rule in pressure-proof form —
  never guess, match, or speculate; no resemblance reasoning;
  the refusal is boundary-class and holds for the whole sitting
  however warmly pressed ("'if I had to guess…' IS guessing");
  the storyteller's own naming may be received and held as HIS
  identification, never presented as hers. Neighbouring
  refusals hardened with the same clause: a boundary, once set,
  "does not soften with repetition", and a gate answer likewise
  never reopens under friendly insistence.
- **Canned parity** (`server/canned.py`): `detect_
  identification_ask` / `detect_self_naming` — rotating warm
  refusals that hold under bare insistence; a self-naming
  ("I am the last born") is accepted with his descriptor and
  held as his identification. Same doctrine, both paths.
- **Tests (T15):** `tests/test_identification.py` — the
  pressure series (ask → warm press → press with a reason →
  bare insistence → his telling, accepted), detector
  discipline, boundary/gate persistence pins, handler-level
  parity. Suite **78/78**. `tests/live_identification_
  check.py` — the sequence against live Spark: **2 of 2 runs
  pass** (every press refused warmly — "I still can't guess,
  even gently" / "I won't guess, even as a kindness" — zero
  forbidden shapes; the telling received as his naming both
  times). Deployed to Modal and re-verified over HTTPS,
  1 run, PASS.


---

## Addendum — Container pinning (Oct 28, 2026, Skunkworks Round 2 Top Move #1)

Round 2 Cell 5 reproduced the Round 1 stranding live: `deploy/modal_app.py`
set only `min_containers=1` (at least one container, not only one), so a
12-way burst spawned extra containers and a seeded session landed on an
amnesiac one — it denied the storyteller's name and story and re-asked
the name question. All state (sessions, media, chapters, keepsakes)
lives in one container's memory (`server/app.py`), so the fleet must be
one container for the window.

**Fix:** `deploy/modal_app.py` now sets `max_containers=1` and
`scaledown_window=3600` alongside `min_containers=1`, with the
trade-off and the remove-after-the-window instruction in the comment.
Redeployed to Modal Oct 28, 2026.

**Proof (Gate A-1 procedure, run twice):** seed a consented session
(name "Marisol"; distinctive detail: a brass lighthouse key in a blue
tin in a grandfather's boathouse in Galveston — acknowledged in Liv's
replies), fire 12 concurrent fresh sessions (each greeted + one story
turn; 12/12 answered), then probe the seeded session. Both runs: the
probe reply named Marisol and carried **all five** detail tokens
(lighthouse / Galveston / brass / blue tin / boathouse) verbatim —
e.g. *"You told me your name is Marisol — and that your grandfather
kept a brass lighthouse key in a blue tin in his boathouse in
Galveston."* **BURST TEST: PASS ×2.** Pre-fix, the identical procedure
failed (Round 2, Cell 5).


## Addendum — Public repo prepared, push blocked on GitHub auth (Oct 28, 2026, Round 2 Top Move #2)

Repo is push-ready: judge-first README (elders/illustrated falsehoods
retired, honest what's-live table, prior-work disclosure naming the
Oct 15–20 Day-0 scaffold), MIT LICENSE added, working tree clean, 34
tracked files, `.env` untracked and gitignored (only `.env.example`
tracked, placeholder only), no internal/Solo material in this repo.
Target: a new PUBLIC repo `liv-story-companion` under
github.com/alomepet3r (checked Oct 28 — the account has no public
repos yet, the name is free). **Push blocker:** this environment has
no GitHub credentials — `gh` is not authenticated, no GH_TOKEN /
GITHUB_TOKEN present, and outbound SSH to github.com is reset by the
network. Unblock (Petro, ~2 minutes): create the empty public repo
`liv-story-companion` on github.com in his signed-in browser (no
README/.gitignore — the history brings its own), then push from an
authenticated channel (`gh auth login` or his browser-side route).
Local HEAD at preparation: `222d34c` on master.
