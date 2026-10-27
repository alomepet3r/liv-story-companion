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
