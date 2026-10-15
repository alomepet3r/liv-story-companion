# Fireside — Meta AI Hackathon Build

**What this is:** an accessibility-first voice companion for elders. Unhurried
conversations become illustrated keepsake chapters and a shareable keepsake.
Built for the Meta AI hackathon (build window Oct 26 → Nov 4, 2026).

**The one loop:** talk → chapter → keepsake.

## IP boundary — read before touching this repo

This build must **never** contain verbatim-fidelity mechanisms, two-chamber
delivery, or any claim about provably faithful preservation. Those belong to a
separate, sealed effort under a disclosure freeze. In this repo:

- Chapters are *plain arrangements* of the session's own words under simple
  headings — reviewable by the speaker, nothing more.
- No hashes, no Merkle trees, no "fidelity receipts," no quarantine logic.
- No copy anywhere in code, UI, video, or write-up may claim faithful
  preservation or anything like it.

## Layout

```
fireside-build/
  server/          Day-0 API wiring (Meta Model API client) + smoke check
  web/             Day-1 app shell lands here
  tests/           unit tests (no key needed)
  .env.example     copy to .env — never commit real keys
```

## Quickstart (Day 0)

1. Claim the $150 Meta Model API credits and create a key at
   https://dev.meta.ai/
2. `cp .env.example .env` and put the key in `MODEL_API_KEY`
3. `python3 -m server.smoke` — lists the models your key can reach
4. `python3 -m unittest discover -s tests` — offline unit tests

## Status

See `DAY0-STATUS.md` for what's done and what's waiting on a human.
