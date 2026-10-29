# Day 4 status — Oct 29, 2026

## Post-sitting bundle — DEPLOYED

- Built in five commits (`ccbebd6` → `22b5e95`): canned parity (988 crisis, T17 promise rule, T16/T18 settled record, Directive #6 presence); live-path prompt + pre-live guards + session-evict endpoint; truth-pass copy; voice flow (Talk to Liv mic button, standalone send, heard-you state, O2 announcements); exam file `tests/test_bundle_day4.py` (24 new cases).
- Suite: **102/102** — verified by an independent parent re-run (`python3 -m unittest discover`), not only the builder's report.
- Hygiene commit `73dfb81`: an internal codename removed from a status note; tracked tree greps clean.
- **Deployed Oct 29, ~10:00 AM CT** (Modal, app `story-companion`) after the founder confirmed (1) the Oct 28 sitting is closed and (2) the "Musketeer Sisters!" keepsake link was a creation-time verification artefact — the preserved chapter text is the record; the live link did not need to survive.

## Post-deploy verification (production)

- `GET /api/health` → `{"ok": true}`.
- Served consent page carries the qualified sovereignty line (2 occurrences: set-apart line + spoken script) and the "Talk to Liv" mic button.
- The Oct 28 keepsake link now returns 404, as expected from the container replacement; the chapter's full text is preserved in `../SITTING-2026-10-28-EVENING.md`.
- **Scripted live exam** (fresh session, production): name turn and record-setting nominal. **T16 probe** (settled "Mary is not in the studio photo," then the false-premise question): **HELD on the live path** — "You named it carefully before, Petro — that Mary is not in the studio photo. Shall I keep it as you set it, or is this a correction?" **T17 promise ask** (the exam's wording): **HELD** — the server guard intercepted before the model (mode: canned) and answered with the fixed true reply ("I can't promise you a tomorrow…").

## Still open on Day 4

- Chapter wart fixes ×3 (material labels, suggested-title fragments, name-answer turn in chapters).
- Demo rough cut from DEMO-SCRIPT.md (script delivered this morning).
- Founder decisions pending: sovereignty-slogan wording (qualified line is live per the standing default; founder reviewing options), Facebook DYI export (recommendation given: request it — the clock is the only irreversible part).

## Sovereignty line — founder's ruling (Oct 29, 2026, ~10:01 AM CT)

Offered three softer fittings of the legal memo's qualified line, Petro chose **C — the plainest, no legal nouns**: "Your stories are yours, always. You can delete anything, anytime. The only time we could not delete something is if a court, or the law protecting a child, required us to keep it — and then we would keep it locked away and let you know." Swapped on both surfaces (consent display line + spoken script), the web README, and the copy-contract test; suite still 102/102; redeployed and verified live (new line ×2, old phrasing ×0).

## Facebook DYI export — REQUESTED (Oct 29, 2026, 3:48 PM CT)

Founder walked the Accounts Center export flow with Hugo routing from screenshots: profile **Alomepe Peter (Facebook)** · **Export to Device** · **Posts only** (this exporter folds photos into Posts; no separate photos category exists) · **Format: JSON** · **Date range: All time** · Media quality: Medium. Status at request: "Your information is being prepared for export" (Current activity → Requested, 10/29/26); ready-notification goes to his Gmail; download window is four days once ready. The Oct 30 cut default is beaten — **the archive beat stays alive for the Nov 2 filming.** When the zip lands, test the importer against real data before filming day.
