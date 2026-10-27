# Chapter slice status — talk → chapter → keepsake (built Oct 27, 2026)

**Trigger:** two orders converged. (1) The skunkworks review's #1
move: freeze non-loop work and build the chapter — until today
only one of the loop's three steps existed (talk). (2) Petro,
after the Oct 27 Agents-101 Pt. 1 workshop briefing: *"We need to
incorporate this into Liv."* The workshop's five transferable
principles (see ../WORKSHOP-OCT27-NOTES.md) are the chapter flow's
architecture; the plan-side record is the "Chapter architecture"
section of ../build-plan.md. Day 4's chapter item is therefore
pulled forward and built; what remains for Day 4 is tuning on real
sittings.

## What shipped

**Server (`server/chapter.py`, stdlib only; routes in
`server/app.py`)** — `POST /api/chapter/outline|replan|draft|
approve|view`, each behind the same consent + 18+ gates as chat
(403 otherwise), and `GET /keepsake/<token>`, the one share link.

1. **Show the work.** Every stage records step events for the
   operations it really performed (gather / plan / re-plan /
   draft / check / approve); the UI renders exactly those.
2. **Checklist + evidence.** The checklist states derive from the
   chapter's actual state. Each draft paragraph carries its
   source ids (conversation turn or caption); the UI's "Where did
   this come from?" lists them per paragraph.
3. **Unverified until approved.** Drafts render badged
   "Unverified draft"; the share token is minted inside
   `approve()` and nowhere else (unknown token → 404; nothing
   unapproved is reachable). A local **source-check** (regex +
   corpus lookup, no model calls) extracts names/dates/places
   from the draft and flags any that do not appear in the
   storyteller's own words as "not in your words — please check".
   It runs on BOTH drafting paths.
4. **Plan before write.** Outline (suggested title, dedication —
   mission layer M1/FR-K7, materials with include/exclude) →
   optional re-plan → drafting → check → review → approve →
   keepsake. Re-plan after drafting is refused.
5. **Grounding discipline.** The live drafting prompt: only this
   session's sources, anchor every paragraph to its source
   labels, invent nothing, omit what is unsure. One Spark call
   (Standard tier; contributor guard untouched). Unparseable or
   failed live output falls back to the deterministic canned
   arrangement; the mode is recorded on the draft either way.

**UI (`web/`, Screen 3)** — "Arrange this into a chapter" beside
"Finish for today"; steps list, checklist, plan editor (title,
"Who is this chapter for?", material checkboxes, section list),
draft view with the unverified badge, the please-check flags,
per-paragraph evidence disclosures, photos kept with the chapter,
approval button, and the keepsake box with the share link.
Accessibility posture kept: labelled controls, `role="status"`
announcements for stage changes, focus moved to the chapter
heading on open and to the share link on approval, 44px targets.

## Deliberately not built

- No persistence: chapter + share-token state is per-session /
  per-container in-memory, like everything else in the demo. The
  known multi-container caveat (skunkworks K4) applies unchanged;
  the deploy's one warm container covers the event window.
- No illustration (Muse Image is Day 5 / FR-K4), no PDF (first
  scope cut), no chapter editing of prose — the storyteller's
  levers are the plan (title, dedication, materials) and approval.
- No new model calls beyond the single drafting call.

## Verification

- **Tests: 47/47** (`python3 -m unittest discover -s tests`) —
  30 pre-existing + 17 chapter tests: gate 403s on every chapter
  route, no-story 400, outline steps/checklist states, re-plan
  exclusion + dedication carried into the draft, refusal to
  re-plan after drafting, no approval before draft, no share
  link before approval, unknown token → nothing, keepsake HTML
  escaping, source-check flags an invented name + date while
  grounded ones pass, arrangement-prompt construction, live-draft
  parsing with source mapping, fake-client live drafting, and
  live-failure fallback to canned.
- **Local HTTP smoke:** health 200; unconsented outline → 403;
  outline → draft (canned, zero flags on grounded material) →
  approve → keepsake 200; bogus token → 404.
- **Live (Modal):** see the deploy note appended below after the
  live end-to-end run with SAMPLE-STORY material only.
