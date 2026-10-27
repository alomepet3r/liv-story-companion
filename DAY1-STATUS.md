# Day 1 Status — App Shell (Mon Oct 26, 2026)

Built at Petro's go-ahead ("start the shell + consent + canned chat
build now"). Verified locally the same afternoon.

## What was built

- **`server/app.py`** — one small Python standard-library HTTP server
  (no new dependencies, no framework). Serves the UI from `web/` and a
  `POST /api/chat` JSON endpoint. Loads the repo `.env` (existing
  pattern) so the run command stays one line.
- **`server/canned.py`** — the development fallback companion. Warm,
  patient, rule-based replies used while the Meta API credit is
  pending: acknowledges what the storyteller said, asks ONE short
  follow-up at a time, remembers details stated earlier in the same
  session (in memory only) and refers back to them, gently offers the
  guided themes (childhood, family, lessons learned, love, wishes),
  meets tender topics plainly, and closes gracefully. Conduct rule in
  code: it never invents facts about the storyteller — it only asks,
  listens, and follows up.
- **`web/index.html` / `styles.css` / `app.js`** — Screen 1: consent
  gate. Screen 2: conversation. Design tokens per the brief (cream
  `#FBF7EF`, charcoal `#2B2622`, ember red `#9D2224` primary action
  only, serif display + readable sans, 19px+ body, one primary action
  per screen). In-app header is the neutral label **"Story
  Companion"** — no uncleared product name appears in the app.

## Chat behaviour

1. `/api/chat` refuses to capture anything before consent
   (`consent: true` required — verified: HTTP 403 without it).
2. Each turn tries the live Meta Model API first (Muse Spark via the
   existing `MetaClient`, with a conduct system prompt mirroring the
   conduct rules above).
3. On any failure it degrades automatically to the fallback companion.
   During today's verification the live call still returned HTTP 402
   (credit not yet delivered), so **every test reply below ran in
   fallback mode, as expected** — the shell is talkable-to tonight,
   and swaps to the live model with no code change once the credit
   lands.

## How to run it

From the repo root:

```
python3 -m server.app
```

Then open http://127.0.0.1:8765 — consent screen first, then the
conversation. Custom port: `PORT=9000 python3 -m server.app`.
Stop with Ctrl+C.

## Verification evidence (Oct 26, ~4:10 PM CT, port 18765)

- `GET /` → **HTTP 200**; page contains the consent copy, the line
  "Yours. Always. Delete anything, anytime", and the begin button.
- `POST /api/chat` without consent → **HTTP 403** "Consent is required
  before we begin."
- Turn 1 — storyteller: "I grew up in Bamenda, and my father took me
  to ride the first elevator in our town." → companion: "I am glad you
  shared that. Tell me more about growing up in Bamenda — what do you
  remember most about it?" (mode: canned)
- Turn 3, after neutral replies → companion reached back on its own:
  "Earlier you mentioned growing up in Bamenda. What stayed with you
  from that?" — session memory working.
- Tender topic, fresh session — "My mother died many years ago…" →
  "I am sorry. Losing someone we love stays with us. Would you tell
  me a little about your mother — what do you most want people to
  know?" (plain, no forced cheer)
- "Finish for today" → graceful close carrying the sanctioned
  framing: the conversation can be arranged into a chapter, the
  storyteller reviews it first, nothing is shared unless approved.
- Static files serve (CSS/JS HTTP 200); path traversal to `.env`
  blocked (HTTP 404). Existing offline unit tests still pass (3/3).
- Copy check: grep for the banned claim terms (per the repo IP
  boundary) across all Day 1 files → **no hits**.

## Still pending (not done today, by design)

- **Hosting / deployment: NOT deployed anywhere.** Runs locally only.
  Hosting target and the Day 1 "deployed, even if empty" item from
  the build plan remain open.
- Live Spark replies — blocked on the organizer-delivered credit
  (HTTP 402); escalation draft sits with Petro to send.
- Voice loop is Day 3; chapter arrangement is Day 4; photo scene is
  Day 5 — none started.

## Deployment — LIVE (Oct 26, 2026, evening)
- **URL:** https://alomepe--story-companion-serve.us-east.modal.run (Modal, workspace `alomepe`, Starter; app `story-companion`; one container pinned warm)
- **Auth path that worked:** Petro completed Google sign-in in person in the live browser and clicked Authorize on the token-flow page (~6:36 PM CT) — CLI token verified against workspace `alomepe`. (Split-machine token flows sent to Petro's own browser had expired 4x earlier; same-machine approval is the working pattern.)
- **Secret:** `meta-model-api` Modal Secret created from the repo .env programmatically; no value printed or logged.
- **Bug found + fixed same evening:** first deploy crash-looped — the wrapper called the app's blocking serve_forever() in-process; Modal logs demanded a non-blocking start. Wrapper now launches the app via subprocess.Popen (app code still untouched). Redeployed and verified.
- **Live verification (from outside, after fix):** GET / → 200 in ~1s with consent copy + "Yours. Always. Delete anything, anytime"; GET /api/health → {"ok": true}; POST /api/chat without consent → 403 "Consent is required before we begin."; with consent → warm canned replies (Meta credit still 402 → canned mode, as designed) including an earlier-detail callback (a later reply referenced "the elevator" from an earlier turn).
- **Session note:** the test harness's `session` field was ignored by the API (it keys to "default") — session handling to tighten on Day 2 with persona work.
- **Open:** Modal budget/spend cap is a dashboard-side setting (Settings/Billing in Petro's account) — not yet set; expected usage is a few dollars of the $30 Starter credit.

## Companion naming — Liv / Livio / Livia (Oct 26, 2026, evening)

- **Decision (Petro):** the companion has a name, chosen by the
  storyteller, replacing the generic "companion" / "Story Companion"
  label in the app's copy and headers. Petro on the name: "Liv sits
  one breath away from 'live'."
- **Model:** **Liv** is the family/default name — generic references
  and every fallback use Liv. **Livio = male voice** and
  **Livia = female voice**: the picked form maps to the companion's
  voice, which becomes functional on Day 3 (voice); the choice is
  recorded now, on the consent screen.
- **Consent screen:** a warm choice before the agree button — "Who
  would you like to talk with?" — three large radio cards labelled
  exactly "Livio / male voice", "Livia / female voice", "Liv / keep
  it simple", Liv preselected, plus a plain note explaining the voice
  mapping. The chosen name updates the consent copy live (lede, choice
  text, read-aloud script) via `.js-companion-name` spans.
- **Conversation screen:** header reads "Talking with {name}"; the
  companion's messages are labelled with the name; the first message
  is the introduction — e.g. "Hello, I'm Livia. I'm here to listen —
  we can go at your pace. Tell me, where did you grow up?" The canned
  companion signs its graceful close with the name; otherwise it stays
  in first person without name-dropping.
- **Plumbing:** the front end sends `companion` with every
  `/api/chat` call; the server validates it against the three names
  (anything else falls back to Liv), stores it per session, and only
  accepts a (re)choice before the conversation starts — a name can't
  switch or bleed mid-conversation, and parallel sessions hold
  different names independently. Every response carries the session's
  `companion` name back. The live path builds its system prompt per
  session: "Your name is {name}. You are a warm storytelling
  companion…" so Muse Spark speaks as the named companion when the
  credit lands.
- **Session wart fixed:** the API now accepts `session` as an alias
  for `session_id` (the Day 1 harness used `session` and silently
  landed in the shared "default" session — see the session note in
  the deployment section above, now superseded).
- **Verification (local port 18766, then live after redeploy):**
  GET / → 200 with all three choices + voice descriptors + the
  sovereignty line; POST without consent → 403; session with
  companion=Livia opens "Hello, I'm Livia…" and stays Livia on the
  next turn; a fresh session with companion=Livio opens "Hello, I'm
  Livio…"; a session sending no name defaults to Liv. Live checks on
  https://alomepe--story-companion-serve.us-east.modal.run returned
  the same results (page 200 in ~0.7s). Existing unit tests pass
  (3/3). Banned-term grep across all touched files → no hits.
- Redeployed to Modal (app `story-companion`, workspace `alomepe`);
  Modal app name and URL unchanged.

## Persona Directive #1 — listener first (Petro, Oct 26, ~8:23 PM CT)

- **His feedback:** after his first real session, the companion felt
  like it was *walking him through* telling his story. His standard:
  a great listener — "like myself" — patient, curious, with proper
  boundaries if requested. Matches his standing principle: guided for
  those who need the walker, free for those who do not.
- **Live prompt (`server/app.py`):** `build_system_prompt` rewritten
  listener-first. Liv does not walk the storyteller through steps,
  themes, or an agenda; follow-ups grow only out of what the
  storyteller just offered; at most one short question, often none —
  a warm acknowledgement is a complete reply; themes only on a
  genuine stall, as an ignorable open door. Boundary law stated
  outright: acknowledge warmly in one line, move on, never return to
  the topic or probe around it for the rest of the session.
- **Fallback engine (`server/canned.py`):** retuned to match.
  Marching/step framing removed; first detail-free answer earns a
  plain acknowledgement with no question; a theme is offered only
  after 2+ consecutive stalls, door-shaped ("We can go anywhere you'd
  like from here… What is on your mind?"). Boundary handling added:
  phrase patterns ("don't want to talk about…", "skip that", "not
  today", "leave that alone"…) are checked BEFORE detail extraction;
  the reply is a warm one-line acknowledgement + pivot; the topic is
  recorded in session state, details already gathered about it are
  dropped, and callbacks/theme offers are filtered so the session
  never steers back.
- **Microcopy (`web/index.html`):** consent intro now carries "And we
  can skip anything — just say so." The greeting carries the same
  line. All consent substance, names, design unchanged.
- **Docs:** `../build-plan.md` Day 2 gained Persona Directive #1 plus
  tests **T6 (Boundary)** and **T7 (No walkthrough)** alongside
  T1–T5; `../MISSION-LAYER.md` M3 gained the listener-first stance
  and boundary law.
- **Verification:** unit tests 3/3. Scripted probes, local then live:
  (a) boundary probe — "I don't want to talk about my mother." →
  "Of course — we won't go there. Thank you for saying so…" and no
  later turn (callback, acknowledgement, theme offer) returned to the
  topic; (b) walkthrough probe — 6 rich turns → zero marching
  phrases, 6/6 replies agenda-free, every reply cited a stated
  detail, no stacked questions; (c) consent gate still 403; (d) skip
  line present on the page and in the greeting. Redeployed to Modal;
  live probes (a)–(d) all pass at the same URL. Banned-term grep on
  touched files: zero new hits (counts identical to baseline).

## Sensitivity gates — Liv guards the doorway (Oct 26, 2026, evening)

- **Petro's principle:** "Liv does not choose what is talked about — the end user does." Automatic triggers fire when a storyteller enters very personal territory: Liv pauses, explains plainly, and asks explicit consent before continuing AND before keeping the material in the story record.
- **Intimate gate** (storyteller's own adult intimate life — legitimate, never banned or shamed): canned detection is conservative (explicit phrases only — "made love", "slept with", "sex life", "had an affair", nude-image mentions, "naked" minus its idioms) so ordinary affection/family storytelling never trips it. Gate reply names it kindly ("this is intimate ground"), explains it becomes part of the story record, asks yes/no.
- **Health gate** (diagnoses/health information — "diagnosed with", "my diagnosis", "doctor said I have", "tested positive", named conditions in possessive/first-person patterns): reply says it sounds like health information deserving extra care, kept with "extra privacy protections" — honest phrasing only, NEVER a claim of HIPAA compliance or certification. With consent, the category is flagged sensitive for the session.
- **Answer handling:** gate sets `awaiting_sensitive_consent` on the session (in memory only, nothing persisted/logged). Clear yes → category consented, never re-gated this session; if the yes carries more story, listening continues in the same turn. Clear no OR ambiguous → graceful pivot, no consent recorded, gate does not re-fire. Detection runs BEFORE detail extraction, so gated material is not absorbed into session details unless consent is given.
- **Hard exception (not a consent gate):** sexual content involving minors (requires BOTH a sexual signal and a minor signal) → one plain refusal line + pivot in canned mode; a stance line in the live prompt. Never continued, never kept.
- **Live prompt:** `build_system_prompt` now carries the two gates + the exception after the Directive #1 boundary law, including "you guard the doorway" and "do not re-ask a gate already answered."
- **Docs:** test **T8 — Sensitivity gates** added to build-plan Day 2 discipline; Day 5 gained the upload-gate inheritance line (nude/intimate images gated at upload time — documented only, media handling not built yet); MISSION-LAYER gained **M7** with Petro's line: "Liv does not choose what is talked about; the storyteller does. Liv guards the doorway."
- **Verification:** 18 scripted probes via the real chat handler (canned path) ALL PASS locally: 403 intact; health gate fires → "yes" continues → follow-up health mention NOT re-gated; intimate gate fires → "no" pivots, no return; ambiguous answer pivots with no consent; 4 ordinary-story turns (childhood, mother's cooking, first job, love for wife) fire NO gate; Directive #1 boundary probe still passes; minor-exception probe returns the refusal with no gate question. Unit tests 3/3. Banned-copy grep: zero new hits (only pre-existing IP-boundary prohibitions in build-plan.md).
