# Liv — a storytelling companion · Meta AI Hackathon Build

**What this is:** Liv is an accessibility-first storytelling companion
for adults of every generation — anyone with a life to tell. You talk;
Liv listens, at your pace. When you're ready, the conversation is
arranged into a keepsake chapter that **you review and approve** before
anything is shared. (This demo build is adults-only — 18+ — by design;
see the consent posture below.)

**The one loop:** talk → chapter → keepsake.

**Live demo:** https://alomepe--story-companion-serve.us-east.modal.run

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
| Photo scene description and people-masking with SAM 3.1 | Planned (Day 5) |
| Keepsake illustrations with Muse Image | Roadmap |

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

## Quickstart

1. Create a Meta Model API key at https://dev.meta.ai/
2. `cp .env.example .env` and put the key in `MODEL_API_KEY`
3. `python3 -m unittest discover -s tests` — offline unit tests (78)
4. Run locally: `python3 -m server.app`, then open
   http://127.0.0.1:8765 — or deploy with
   `modal deploy deploy/modal_app.py` (see `deploy/README-modal.md`)

## Status

Build notes live in `DAY0-STATUS.md` … `DAY3-STATUS.md` and
`CHAPTER-STATUS.md` — what shipped, how it was verified, and what is
deliberately not built.
