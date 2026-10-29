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
- **Live (Modal, deployed Oct 27):** full synthetic end-to-end
  run over HTTPS with SAMPLE-STORY ("The Elevator") material
  only — no real storyteller content. Health 200; chapter
  outline + approve without consent → **403**; greeting + five
  story turns (live mode); outline → steps `[gather, plan]` with
  the real detail lines, no share link; re-plan set title
  "The Elevator" + dedication "my children"; draft came back
  **mode: live** (the Spark arrangement path, not the fallback),
  source-check **9 checked / 0 flags**, share link still absent;
  approval minted `/keepsake/<token>`; the keepsake GET returned
  200 carrying the title, "For my children", and the story's own
  material; a bogus token returned **404**. The live keepsake
  page's HTML is saved at
  `../ui-redesign-shots/chapter-keepsake-live.html`.
- **Deployment identity:** the live `/`, `index.html`, `app.js`
  and `styles.css` are **byte-identical** to the committed code
  (cmp-verified after deploy).
- **Screenshot limitation, stated plainly:** headless Chromium
  in this sandbox cannot navigate at all (chrome-error pages for
  the live URL and for localhost alike; zygote/socket failures
  on every flag combination tried — the same class of limit the
  accessibility audit recorded). So there is no pixel shot of
  Screen 3 from this environment; the visual artifact is the
  live keepsake HTML above, the flow evidence is the API run,
  and the UI code is the committed, byte-identical asset set.
  A phone pass by Petro remains the real-device check, as with
  the redesign.

## Known warts / Day 4 tuning

Filed Oct 28, 2026, from Petro's first real chapter outline
(~1:28 AM CT screenshot of a live sitting — the plan screen
itself worked: the steps showed 9 tellings + 4 shared items
gathered, and the checklist states were correct). Two items:

1. **Material labels are generic.** Every telling in the
   plan's "What goes in" checklist is labelled only "Something
   you told Liv" — nine identical rows — and media items read
   "A photo you shared" / "A voice recording you shared" /
   "A video you shared". The storyteller cannot identify
   *which* item is which, so the include/exclude control is
   nearly meaningless: you cannot knowingly uncheck what you
   cannot recognise. **Fix:** label each telling with its
   opening words (first ~8–10 words, truncated gracefully);
   label each media item with its type plus a distinguishing
   detail — the caption's first words, the date/time shared,
   or the archive album name when present.
2. **Suggested title is a raw fragment.** The title field was
   prefilled "My dad had just passed and I…" — the truncated
   opening of his first sentence, mid-thought, with an
   ellipsis. A suggested title should never be a chopped
   sentence fragment. **Fix:** derive a cleaner suggestion, or
   fall back to an honest placeholder ("Untitled — yours to
   name"); never truncate mid-sentence.


## Wart confirmation — Oct 28, 2026, ~2:50 PM CT (Petro's at-work session, live screenshot)

Both Day 4 warts REPRODUCED on fresh material (second sitting, same failures — now confirmed patterns, not one-offs):
1. **Material labels still generic:** the outline's "What goes in" lists **10 identical rows, all "Something you told Liv"** (plus 1 shared item), all ticked — include/exclude remains meaningless for the storyteller.
2. **Suggested title still a mid-sentence fragment:** "We are in Bamenda Cameroon, in the..." — truncated from the telling "We are in Bamenda Cameroon, in the late 1970s, I would have been...". Same defect as Sitting #1's "My dad had just passed and I...".
Steps/checklist rendered correctly (Gathered 10 told + 1 shared; Outline proposed; checklist states accurate). Dedication field took "My Family". Evidence screenshot: Petro's liv2.PNG in the hackathon chat, Oct 28.


## Wart fixes — Oct 29, 2026 (Day 4)

All three warts fixed in one pass; suite **116/116** (102 at the
post-bundle baseline + 14 new chapter tests). Not deployed —
parent verifies and deploys.

1. **Labels (wart 1).** `gather_sources` now labels each telling
   by its own opening (first ~10 words, backed off to the last
   clause boundary in reach; an ellipsis only where text was
   actually left behind, at that clean cut), and each media item
   by the most identifying detail it carries: caption's first
   words → date → album → share time (app.py now stamps
   `shared_at` on upload). A recording whose transcript is its
   text is labelled by the transcript's opening. A uniqueness
   pass numbers any repeated label ("… (2)") so no two materials
   with different content share a label.
2. **Titles (wart 2).** `suggest_title` no longer chops the
   longest telling at seven words. It walks the tellings in
   order and offers the first clean derivation: a complete short
   sentence (≤8 words) standing whole, or a 4–9 word clause cut
   at a comma/semicolon/colon/dash/conjunction that does not end
   on a dangling word. The production failures now yield "My dad
   had just passed" and "We are in Bamenda Cameroon". When no
   telling offers a clean derivation, the suggestion is the
   honest "Untitled — yours to name". No ellipsis ever appears
   in a suggested title.
3. **Housekeeping turns (wart 3).** A shape-based filter in
   `gather_sources` (the chapter layer only — conversation
   behaviour untouched) excludes pure plumbing from the sources:
   name declarations ("Call me Petro.", "My name is…", bare
   opening names, name-question declines), bare greetings,
   closing phrases ("Finish for today"), and meta questions to
   Liv. A declaration or greeting that merely *leads* a telling
   is stripped, and the telling is kept. Detection carries the
   companion's own glue-word guard, so substantive short
   tellings survive intact: "It did not stay with me." and
   "I'm from Bamenda." are sources, never housekeeping.
