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
