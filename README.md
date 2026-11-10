# Fireside — Liv, a storytelling companion · Meta AI Hackathon Build

## Every family is one funeral away from losing its stories forever.

Liv helps a storyteller tell their story in conversation. Chapters
**arrange** the conversation. A deterministic source-check flags draft
details that do not appear in the telling. The storyteller reviews and
approves before a chapter is published or shared with another person.

Liv is an accessibility-first companion for adults of every generation —
anyone with a life to tell. You talk; Liv listens, at your pace. This
demo build is adults-only — 18+ — by design; see the consent posture
below.

**The one loop:** talk → chapter → keepsake.

**Live demo:** https://alomepe--story-companion-serve.us-east.modal.run

## The heart

Liv is patient. She does not hurry a telling, and she does not fill
silences with guesses. When a photograph is shared, the storyteller's
count governs: a measured count is only a starting point, and a
deliberate correction from the storyteller is adopted at once and held
for the rest of the sitting. Liv never guesses who is in a photograph —
the storyteller names people, and Liv holds the names she is given.
And the storyteller stays sovereign over the sitting: anything can be
deleted, at any time, by the person telling the story.

## By the numbers

Measured results belong here — and nowhere else in this README makes a
performance claim without them.

| Measure | Result |
|---|---|
| Source-check — planted inventions caught | **7 of 9** flagged (`SCORECARD.md`, Nov 10, 2026) |
| Source-check — planted inventions missed | **2** — `red bicycle`, `three weeks` (see *Where it fails*) |
| False flags on a clean draft | **0** (one small clean draft, 3 candidates checked) |
| Count corrections adopted | **3 of 3** deliberate corrections; 2 of 2 non-correction controls held |
| Automated test suite | **277 tests, all passing** |

*How to read this table: the source-check counts come from a
planted-invention evaluation — details deliberately placed in a draft
that were never in the telling, then counted as flagged (caught) or
unflagged (missed). Misses are published here, not hidden. Full method,
fixtures, and failures: `SCORECARD.md` (re-runnable:
`python3 -m eval.run_eval`). Chapter cost/time is **TO-RUN** — the
harness makes no live model calls, so no cost or time number is claimed.*

## What Liv sends, and what approval gates

The real data path, plainly:

- The browser sends the conversation and any shared media to the
  app server (hosted on Modal). The sitting — conversation, media,
  chapters, and keepsake tokens — is held in that one server
  container's memory.
- To work, the app sends material on to Meta's model services:
  conversation text and photos to Muse Spark (and photos to
  SAM 3.1 for the scene ledger), recordings and the spoken audio
  of videos to Muse Voice Transcribe, the session's sources and
  outline to Muse Spark for a live chapter arrangement, and an
  approved chapter's title, dedication, and section headings to
  Muse Image for its illustration. The deterministic
  source-check itself runs in the app, on the session's own
  words; it is not a model call.
- **Approval does not gate that processing.** Approval gates
  publication: no chapter is published, given a keepsake link,
  or shared with another person until the storyteller approves
  that chapter. Anyone the storyteller gives the approved
  keepsake link to can read that chapter.
- **Closing or refreshing the tab does not delete a sitting.**
  It leaves the sitting unreachable in server memory. The
  storyteller's end-and-delete control wipes the session's
  in-memory state and drops its keepsake links; a container
  restart or redeploy also clears the memory, links included.

## Model stack — every model has a named job

| Model | Job in Liv | Without it |
|---|---|---|
| **Muse Spark 1.3** | Conversation, vision, chapter arrangement | No companion |
| **Muse Voice Transcribe 1.0** | Voice tellings — spoken words are transcribed and answered as the teller's words | Tellers who can't type are shut out |
| **SAM 3.1** | Scene ledger that counts people in a photograph without identifying anyone | Liv would have to guess at photos, which she refuses to do |
| **Muse Image 1.0** | Keepsake illustration, drawn only from an approved chapter's title, dedication, and section headings | Keepsake is text only |

Remove any row and a named capability goes with it. That is the test
each model had to pass to stay in the stack.

## What's live today

| Capability | Status |
|---|---|
| Conversation with Liv (Muse Spark 1.3, live path; deterministic fallback engine when the API is unreachable) | **Live** |
| Speak and be heard — voice notes and the spoken words in videos are transcribed (Muse Voice Transcribe) and answered as your words | **Live** |
| Photos — Liv sees a photo you share and asks about it; she never guesses or speculates about who is in a photo (you name people; she holds your naming) | **Live** |
| Chapter flow — outline → re-plan → draft → source-check → your approval → one shareable keepsake link (nothing is shareable before approval) | **Live** |
| Source-check — a deterministic check that flags names, dates, and places in a draft that are not in the storyteller's own words ("please check") | **Live** |
| Bring your archive — import your own Facebook export; photos + captions only, nothing selected by default, nothing reaches Liv until you tick it | **Live** |
| Consent + 18+ gates on every route; stated boundaries and declined topics hold for the whole sitting | **Live** |
| Scene facts with SAM 3.1 — a shared photo is measured into a scene ledger (how many people are in it, how much of the frame they fill) and those facts are given to Liv, so any count she states comes from measurement, never a guess; the ledger says nothing about who anyone is | **Live** |
| Keepsake illustration with Muse Image — an approved chapter can be illustrated, drawn only from the chapter's own title, dedication, and section headings (never people, faces, likenesses, or text) | **Live** |

## Where it fails

Honest limits, stated plainly:

- **Sessions are in-memory — a refresh strands a sitting.** Sessions,
  media, chapters, and keepsake tokens live in one container's memory
  (the deployment pins the fleet to a single container for exactly this
  reason — see `deploy/modal_app.py`). Closing or refreshing the tab
  does not delete the sitting: it stays in server memory, unreachable,
  until the storyteller ends and deletes it (which also drops its
  keepsake links) or the container restarts and clears its memory.
  Either way, an unapproved chapter cannot be recovered afterwards.
- **The source-check is mechanical, not wise.** It flags draft details
  — names, dates, and places as extracted — that do not appear in the
  telling. It cannot judge emphasis or meaning, it cannot tell whether
  something the teller *did* say is true, and it does not grade how a
  chapter reads. That judgment stays with the storyteller at review.
- **It misses some of what it should catch.** The planted-invention
  evaluation (`SCORECARD.md`) caught 7 of 9 planted inventions and
  missed 2 — `red bicycle` and `three weeks`: the check extracts only
  capitalised name/place phrases and numeric or full written dates, so
  an invented detail in lowercase common words is invisible to it. A draft still
  needs the storyteller's own read before approval; the check assists
  that read, it does not replace it.
- **The open-weights option is unverified.** A smoke test of Muse Spark
  Open via Baseten (`meta-models/muse-spark-open-1026`) on Nov 10, 2026
  failed before any HTTP response arrived (connection closed, both
  attempts) — recorded in `SCORECARD.md`. It is a connectivity result,
  not a model verdict, and the engine is not wired to it in this build.
- **When the Meta API is unreachable, a deterministic fallback engine
  answers instead.** The sitting continues, but the fallback is a
  narrower, scripted companion — not the live model.
- **The illustration can fail.** On failure the build says so honestly
  ("The illustration didn't come through — your chapter is complete
  without it") and the approved chapter stands on its own.

## Prior-work disclosure

This repository's scaffold and Meta Model API wiring were created on
**Oct 15–20, 2026**, ahead of the build window (see the earliest
commits). The application itself — the shell, the persona, media
capture, the archive slice, the chapter flow, and voice — was designed
and built during the official build window, **Oct 26 – Nov 4, 2026**.
The broader product concept and the persona research predate the
event; no pre-existing application code is included beyond the Day-0
scaffold disclosed here.

## IP boundary — read before touching this repo

This build must **never** contain verbatim-fidelity mechanisms,
two-chamber delivery, or any claim about provably faithful
preservation. Those belong to a separate, sealed effort under a
disclosure freeze. In this repo:

- Chapters are *plain arrangements* of the session's own words under
  simple headings — reviewable by the speaker, nothing more.
- No hashes, no Merkle trees, no "fidelity receipts," no quarantine
  logic.
- No copy anywhere in code, UI, video, or write-up may claim faithful
  preservation or anything like it.

## Layout

```
fireside-build/
  server/          the app: chat + persona engines, media, archive,
                   chapter flow, voice (Python standard library only)
  web/             consent, conversation, and chapter screens
  deploy/          Modal wrapper + runbook (the live deployment)
  tests/           unit tests + live-check scripts (no key needed
                   for the unit suite)
  .env.example     copy to .env — never commit real keys
```

## How to run

1. Create a Meta Model API key at https://dev.meta.ai/
2. `cp .env.example .env` and put the key in `MODEL_API_KEY`
3. Run the offline unit tests (no key needed):
   `python3 -m unittest discover -s tests`
4. Run locally: `python3 -m server.app`, then open
   http://127.0.0.1:8765

## Tests

- Unit suite (offline, Python standard library only):
  `python3 -m unittest discover -s tests`
- The suite lives in `tests/` (`test_*.py` modules covering archive,
  chapter flow, identification refusal, illustration, voice, SAM,
  and more), plus live-check helpers such as
  `tests/live_identification_check.py` for checks against a running
  instance. The measured suite size is published in *By the numbers*
  above, from the harness-emitted `SCORECARD.json` / `SCORECARD.md`.

## Deploy

Deploy with Modal from the repo root:

```bash
modal deploy deploy/modal_app.py
```

See `deploy/README-modal.md` for the full runbook (account, token
hand-off, secret creation, verification, and budget notes). The
wrapper in `deploy/modal_app.py` serves the existing `server/` +
`web/` app unchanged; the API key reaches the container only through
the Modal Secret named `meta-model-api`.

## License

MIT — see `LICENSE` in this repo.

## Status

Build notes live in `DAY0-STATUS.md` … `DAY3-STATUS.md` and
`CHAPTER-STATUS.md` — what shipped, how it was verified, and what is
deliberately not built.
