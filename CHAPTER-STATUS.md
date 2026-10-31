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

## Keepsake illustration — Oct 30, 2026 (Day 5)

The third Meta model enters the product: after a chapter is
APPROVED, the storyteller can ask for an illustration for the
keepsake (Muse Image). One illustration per chapter; asking
again replaces it, and the keepsake copy says so plainly.

- **Surface probe (first image call).** `GET /v1/models`
  confirmed the exact id `muse-image-1.0`. Generation lives on
  the OpenAI-compatible surface `POST /images/generations`
  with `{model, prompt, n: 1}`, answered by
  `{created, data: [{b64_json}], output_format, background,
  usage}`. One harmless probe (an apple, watercolour) returned
  200; the base64 decoded to a 474,212-byte WebP (RIFF magic).
  `MetaClient.generate_image` follows the house pattern:
  allowlist `{muse-image-1.0}` only (contributor tiers refused),
  content type sniffed from the image's own magic bytes (the
  bytes outrank the response's claimed format), usage logged as
  metadata only (model, latency, byte count, numeric usage
  fields — never the prompt).
- **Prompt discipline.** The image prompt is built ONLY from
  the approved chapter's furniture — title, dedication, section
  headings (`chapter.build_illustration_prompt`). Raw
  conversation text never reaches the image model (tested:
  body-only phrases from the tellings are absent from the
  prompt). The white-paper red-team rules are baked into the
  server-side template itself: NO people, NO faces, NO human
  figures or silhouettes, NO likeness of any real person, NO
  words/letters/numbers/text anywhere in the image. The brief
  steers to places, objects and moods — for a boxing chapter:
  gloves, a gym, dawn light over a town.
- **Flow.** `POST /api/chapter/illustrate` (same consent + 18+
  gates as every chapter route) → 409 when there is no approved
  chapter → `chapter.illustrate` records a real step event and
  stores the image in the chapter's in-memory state, mirrored
  into the share snapshot as a flag + version. The keepsake
  page renders it at the top with alt text "An illustration
  made for this chapter", served by
  `GET /api/chapter/illustration?session_id=...` from the
  owning session. Same lifetime as the keepsake: it dies with
  the container and with the share link — no persistence was
  invented.
- **Failure honesty.** No live client, a raised generator, or
  an empty result all answer 502 with "The illustration didn't
  come through — your chapter is complete without it." The
  approved chapter, its steps and its keepsake are left
  exactly as they were (tested).
- **UI.** In the keepsake box: an "Illustrate this chapter"
  button in the house style, a truthful working line while it
  generates, the illustration shown when present, and the
  honest failure line on error.
- **Tests.** Suite 183 (was 169): client-level decode/sniff/
  allowlist/refusal tests in `test_meta_client.py`, and
  `tests/test_illustration.py` — gates (403), 409 before
  approval, end-to-end approval → illustrate → keepsake
  render, replacement on re-ask (version 2), furniture-only
  prompt under the discipline, and both failure paths leaving
  the chapter intact. No live calls in the suite.

## Scene ledger (SAM) — Oct 30, 2026 (Day 5)

The fourth Meta model enters the product, in the shrunk form
the Oct 30 spike earned (verdict: BUILDABLE-SHRUNK; threads
and masking stay on the Round 2 kill list). When a photo rides
a conversation turn, ONE SAM 3.1 call (concept `person`) runs
BEFORE the Spark vision turn, and its boxes become a one-line
ledger of measured facts in the live prompt.

- **Client.** `server/sam_client.py` — SAM lives on the
  Responses surface (`POST /responses`), not chat. The
  concept must be a BARE noun phrase (a sentence returns 200
  with empty output — the spike's silent no-op trap); boxes
  are regex-extracted from the output_text token stream in
  raw source pixels, mask payloads discarded unread.
  Allowlist discipline identical to the other three models:
  only `sam-3.1` may ever carry a storyteller's photo, refused
  in code before any call. Timeout `SAM_TIMEOUT = 10` s (the
  spike measured 1.4–2.3 s per call). Usage logging is
  metadata only (model, concept, box count, latency).
- **The ledger line.** Exactly:
  `[Scene ledger — measured facts about this photo from a
  scene tool, not a guess: exactly N person/people is/are in
  this photo[, together] filling …the frame. The count is
  verified: if you say how many people are in this photo, say
  N — never a different number. These facts say nothing about
  who the person/anyone is.]` — count always; frame share
  (boxes' combined area over the frame, capped) only when it
  states cleanly (one shared image size across boxes, ≥5%).
  With several photos on a turn the ledger names "the first
  photo in this turn" — SAM runs once, on that photo.
- **D28 by construction.** Counts and frame share only — no
  identities, no guesses; no box or mask is shown anywhere.
  An empty SAM answer is silence, not a claim of absence: a
  ledger exists only when at least one person was verifiably
  found.
- **Failure = silence.** No key, any SAM error, a timeout, or
  an empty result all degrade to exactly the pre-SAM
  behaviour — the photo turn proceeds, no ledger, no
  user-facing seam. The ledger lives only in the model's
  per-turn copy; it never enters session history.
- **Canned path.** No change: it has no live model, SAM is
  never called on it, and it never sees a ledger (tested).
- **Archive photos.** No gap: archive-shared photos land in
  the same session media store and ride the same vision turn,
  so they carry the ledger too, alongside their caption/date
  context (tested).
- **Tests.** Suite 204 (was 183): `tests/test_sam.py` —
  box-stream parsing (masks ignored, empty = []), the
  Responses payload shape + bare-noun concept + timeout
  plumbing, allowlist refusal before any call, timeout
  propagation; ledger present in the live prompt (1 person /
  9 people, share phrases), absent on failure, on timeout, on
  empty result, without a SAM client, on non-photo turns, and
  on the canned path; no identity language in the ledger
  (whole-word check); ledger never enters history; archive
  inheritance. No live calls in the suite.

### Follow-up count gap — closed Oct 30, 2026 (Day 5 evening)

- **Production evidence.** The parent agent's live probe of
  the deployed build: on the photo turn the ledger is
  injected and holds. But ask "How many of us are in that
  photo?" on the NEXT turn — no media attached — and the live
  model confabulated "sixteen". The ledger lived only in the
  photo turn's per-turn copy (by the original design: never
  in history), so the follow-up turn held neither the image
  nor the facts. A count question naturally arrives a turn
  after the photo; the grounding must travel with the photo.
- **Facts persist on the photo.** When SAM produces a
  ledger, the measured facts are stored on the media item
  itself: `item["scene_facts"] = {"person_count": N,
  "frame_share": <phrase or None>}` — counts and frame share
  only, D28 unchanged. (Decision, named: `frame_share`
  stores the ledger's verbal phrase, not a float — the
  re-injection block needs words, and the phrase is already
  the honesty-checked form.) Facts ride the session's media
  store; they never enter session history.
- **Re-injection on later turns (live path only).** Each
  live turn's system copy gains, when earlier photos carry
  facts, a compact block in exactly this format:
  `[Verified facts about photos shared earlier in this
  conversation — measured by a scene tool when each photo
  arrived, not guesses: the photo labelled “<chapter media
  label>” contains exactly N person/people[, together]
  <frame share> — if you say how many people are in that
  photo, say N — never a different number; these facts say
  nothing about who the person/anyone is; ….]` — per photo,
  bound by the chapter module's media label (caption, date,
  album, or share time — the reference the conversation
  itself uses), most recent first, capped at the last three
  photos with facts. On a photo turn the fresh ledger rides
  the user message as before and the block excludes that
  photo (dedupe by media id), so a photo is never stated
  twice in one turn.
- **Never-guess rule (live prompt).** `build_system_prompt`
  now carries "COUNTING PEOPLE IN PHOTOS — never invent a
  number": a count is welcome when it is measured (ledger or
  scene facts) or the storyteller's own; when NO verified
  count is available, Liv must not invent one — the rule
  names a hedge on an invented number ("sixteen, I think —
  tell me if I'm wrong") as still invention, forbidden — and
  her move is to say she doesn't want to guess at a number
  she can't stand behind and invite the storyteller's count.
- **Canned path — documented absence.** There is no canned
  surface to mirror into: the canned companion never sees a
  photo at all (its `media_reply` acknowledges the arrival
  honestly and asks for a description) and has no count
  mechanism or count claim anywhere — it cannot state a
  number about a photo, invented or otherwise. SAM remains
  never called on the canned path; facts re-injection is a
  live-path assembly and is absent there by construction.
- **Failure still = silence.** No facts, no block; any SAM
  failure on the photo turn leaves the item fact-free and
  later turns exactly as before this fix.
- **Tests.** Suite 211 (was 204): `TestSceneFactsTravel` —
  facts stored on the item (and not stored on SAM failure);
  a follow-up text turn's assembled system copy carries the
  earlier photo's count and label, SAM not re-called, block
  absent from history; dedupe on the photo's own turn (fresh
  ledger in the user copy, block carries only the earlier
  photo); cap at the three most recent, in order; archive
  photo facts stored and carried under their caption label;
  never-guess rule text present in the live prompt assembly
  with no facts anywhere, and no facts block in that case.
  No live calls in the suite.
