# Fidelity Scorecard — Fireside / Liv

- **Date:** November 10, 2026
- **Harness:** `eval/run_eval.py` (re-runnable: `python3 -m eval.run_eval` from the repo root)
- **Fixtures:** `eval/fixtures/fidelity_cases.json` — synthetic sample material only, invented for this harness. No real storyteller content is used anywhere in this evaluation.

## Method (brief)

The harness measures the shipped code, not a reimplementation, and makes **zero live model calls** (deterministic / canned paths only):

- **(a) Source-check integrity** — draft chapters are built from a small synthetic telling. One draft is seeded with planted inventions (names, dates, and details that do not appear in the source telling); one clean draft is arranged only from the telling's own material. Both are run through the shipped deterministic source-check, `server.chapter.source_check`, which flags names, dates, and places in a draft that do **not** appear in the storyteller's own words. Chapters arrange the conversation; the check is a mechanical comparison of draft details against the source telling, and a flag means "please check this" — nothing more.
- **(b) Count-correction adoption** — the shipped session note-taker `server.app._note_count_correction` is exercised directly with synthetic sessions (a photo whose measured count is stored as `person_count`), plus the shipped `TestCountCorrection` test class is run and reported.
- **(c) Behaviour suite** — the full existing test suite, run as `python -m unittest discover -s tests -t .` from the repo root.
- **(d) Chapter cost/time** — not measured: the harness makes no live model calls and the repo holds no cost/time artifacts. Marked **TO-RUN** rather than estimated.

## Measured numbers (from actual runs on Nov 10, 2026)

### (a) Source-check integrity

| Measure | Result |
|---|---|
| Planted inventions, total | 9 |
| Flagged by the source-check | **7** |
| Missed | **2** |
| Candidates checked, planted draft | 10 |
| Candidates checked, clean draft | 3 |
| False flags on the clean draft | **0** |

Flagged: `Zanzibar`, `1977`, `Eleanor`, `Lake Victoria`, `March 12, 1991`, `Santiago`, `2003`.
Missed: `red bicycle`, `three weeks` — see "Where it fails".

### (b) Count-correction adoption

| Measure | Result |
|---|---|
| Deliberate corrections adopted (owner's number stored as `owner_count`, measurement kept beside it, never overwritten) | **3 / 3** |
| Non-correction controls correctly held (a number merely mentioned changes nothing) | **2 / 2** |
| Shipped `TestCountCorrection` class | **9 ran, 9 passed** |

### (c) Behaviour suite

| Measure | Result |
|---|---|
| Suite before this pass (measured at the start of the pass) | 242 ran, 242 passed |
| Suite after this pass (final verification, run twice with the same result) | **270 ran, 270 passed, 0 failures, 0 errors, 0 skipped** |

The +28 is: 6 new harness tests in `tests/test_eval_harness.py`, plus 22 tests from parallel same-day winners-lessons work (guided judge path, keepsake share card, public scorecard surface) that landed in this repo during the pass.

### (d) Chapter cost/time

**TO-RUN.** No number is claimed. Measuring live chapter cost/time requires live model calls and timing artifacts; this harness deliberately makes none.

## Where it fails

- **The source-check misses lowercase invented details.** Of 9 planted inventions, 2 were missed: `red bicycle` (an invented object, written in ordinary lowercase words) and `three weeks` (an invented spelled-out duration). This is by construction, not a bug found later: the check extracts only capitalised name/place phrases and numeric or full written dates (including bare years). An invented detail phrased in lowercase common words is invisible to it, and the storyteller-facing flag list will not show it.
- **The check is a surface comparison, not a proof.** A candidate counts as grounded when its words appear in the source telling, so a multi-word phrase assembled entirely from words the storyteller did say could pass unflagged even if the combination is new. A flag means "not found in your words — please check"; no flag does **not** mean a draft detail was confirmed.
- **The false-flag number rests on a tiny sample.** 0 false flags were measured on one small clean synthetic draft (3 candidates checked). That is a clean result on this fixture, not a general false-flag rate.
- **Count correction is shape-bound.** Adoption was measured only for the narrow deliberate-correction shapes the shipped detector recognises (e.g. "there are nine of us in that photo", "nine is a correction"). Corrections phrased outside those shapes are not adopted by this code path — the controls show the same narrowness working in the safe direction (passing mentions change nothing).
- **Chapter cost/time is unmeasured** (TO-RUN, above).
- **Baseten smoke test failed** (below) — no live-model verdict of any kind is available from this pass.

## Work notes

- **Baseten smoke test:** FAILURE — no HTTP response received on either of 2 attempts, ~0.4s and ~0.2s.

  One minimal chat-completions call was made to the Baseten OpenAI-compatible endpoint (model-apis.baseten.co/v1, model meta-models/muse-spark-open-1026). The API key was read from the repo gitignored .env file at runtime, and it is recorded nowhere in any tracked file. Both attempts ended before any HTTP response arrived — the remote end closed the connection without responding — so no HTTP status exists to report, and this result is not an auth verdict and not a model verdict. General network egress from the same environment was verified working against another public host in the same window. Re-run the smoke test from an environment that can reach the Baseten model APIs before drawing any conclusion.
- Every number above comes from a run executed during this pass. Anything not measured is marked TO-RUN.
