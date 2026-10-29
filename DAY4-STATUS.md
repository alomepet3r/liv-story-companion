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

## Liv-only + greeting rulings (Oct 29, 2026, afternoon)

**Liv-only.** The founder ruled the companion is Liv — only Liv — for the hackathon build. His own usage never veered from Liv across every sitting; the Livio/Livia variants mapped to voices, but TTS was cut from this build, so the consent-screen choice changed nothing real and only taxed the storyteller a decision. The variants are **parked for the real platform**, where voices exist — not deleted as an idea. Implementation: consent cards replaced by a "Meet Liv" introduction; no companion value is sent by the client; the server accepts and ignores any client-supplied name; `normalize_companion_name` always returns "Liv"; sessions can never carry another name.

**Greeting + the name ask's own skip.** The canned greeting (and the live path's opening, served from it) now opens with the founder's words: **"Hi, I'm Liv!"** — pace and skip beats unchanged. Founder's catch, same afternoon: the name question now carries its own skip in the question itself — "…or no name at all — and you can skip this too; whatever feels right." Behaviour pinned by tests as the one-ask guarantee: a clear name answer is captured; an explicit skip/decline stores no name and is never re-asked; a substantive telling launched straight past the question is received as the story (state "missed") — never mined for a name, never circled back to. The live prompt carries the same rule in prose.

**Mic button restyle (founder UI/UX ruling, same day).** "Talk to Liv" is now a solid ember pill (#9D2224) with a white inline-SVG microphone icon (the emoji glyph is gone) and a white, always-visible label (~18px, 700). Pairings: white on ember 7.8:1 (text); the pill boundary vs the cream paper ~7.3:1 (WCAG 1.4.11 needs 3:1). Recording state no longer rests on colour: the fill flips to ink charcoal, the label swaps to "Tap to send," a pulsing ember dot rides the pill, and #voice-status announcements are unchanged. Minimum height 52px.

Suite after all three rulings: **133/133** (17 new cases in `tests/test_liv_only.py`). Commits: `32db561`, `e018325`, `7633e37`, `53d1901`. DEMO-SCRIPT.md Beat 2 updated (consent + introduction; no choice to film). **Not deployed** — parent verifies and deploys.

## Conversation layout — founder's ruling (Oct 29, 2026, ~4:09 PM CT)

Petro rejected Hugo's bare-declutter sketch and gave his own layout, using a chat UI as the visual reference — his words: 'At the Top is "FireSide" / Talking to Liv - follows / Then if the conversation could live in a box like this one... It would be great.' **Standing UI principle, recorded in his words: minimalist but very functional, conversational, intuitive, effective.**

As built:
- **Header lockup:** one compact brand lockup on every screen — the small flame-in-ring mark beside the word **Fireside** (Cormorant Garamond; the project's filed public name) — replacing the roundel stacked over the "Liv" wordmark on the conversation screen, and applied to the shared masthead so the consent screen carries the same lockup (Liv is introduced there by the Meet Liv panel). Page title is now "Fireside — Your stories, in your own voice."
- **Sub-line:** beneath the lockup on the conversation screen, exactly **"Talking to Liv"** — the founder's phrasing ("to", not "with") — set quiet (Cormorant italic, ink-soft).
- **The box:** the transcript (turns + Liv's listening state) now lives in a contained panel — background `--paper-2` (#F6EFE1, one paper step deeper than the #FBF7EF canvas), border `1px solid var(--line)` (rgba(43,38,34,0.16)), **border-radius 18px** (16px on small screens), padding 1.5rem/1.35rem (1.15rem/1.05rem small), the house `--shadow`. The composer (+ Add, reply box, Talk to Liv, Send) stays below the box; the session actions and "Take your time" line are unmoved. The composer's old hairline rule came off — the box's border does that work now.
- **Speaker tags:** the visible ◆ LIV / YOU tags are removed; inside the box, Liv's left-ruled letter blocks and the storyteller's right-side tinted cards carry who is speaking. Speaker identification remains for assistive technology: app.js still labels every turn, and the label is now visually hidden (the standard 1px clip recipe), so screen readers announce "Liv" / "You" as before.

Suite: **138/138** (5 new layout-contract cases in `tests/test_liv_only.py`). Commits: `4183123` (layout), `6a81aaa` (tests). DEMO-SCRIPT.md updated (Beat 2 must-be-true, Beat 3 screen action, §6 checklist item). **Not deployed** — parent verifies and deploys.

## Founder's hand sketch — folded in (Oct 29, 2026, afternoon)

Hours after the layout ruling, the founder hand-drew the conversation screen himself and sent the sketch. It refined the ruling in three places, all now built (suite 140/140, pushed, awaiting the parent's single deploy so the founder refreshes once into the finished surface):

- **Speaker labels visible again — small.** The sketch keeps a quiet label inside the box above each turn ("◆ Liv" left, "● You" right, 0.82rem muted) — reversing the morning's full removal. A whisper, not the old shout; AT labelling unchanged.
- **Mirrored edge rules.** Liv's blocks now carry a heavy ember rule at the left (3px); the storyteller's cards gained the matching heavy ink rule at the right — the sketch's hatched edges.
- **Composer per the sketch.** Reply label → full-width field → one action row: Talk to Liv pill, "+ Add" as a quiet text-button (moved down from its separate row above the field; its picker still opens in its long-standing home above the field and is controlled by id from the row), and Send compact at the row's right end. The full-width send bar is gone; Send stays visible on the parent's accessibility call (typed input needs a visible send affordance).

## Conversation screen — founder's refinement pass #2 (Oct 29, 2026, ~4:24 PM CT)

The founder reviewed the deployed layout build and ruled five refinements in one message; his standing ADA priority governed the pass ("ADA standards is a big deal for me"). All built, suite **141/141**, pushed, awaiting the parent's verify-and-deploy:

- **Labels:** the ◆ / ● marker glyphs are gone. Both speaker labels are now ALL CAPS at the same size (0.82rem, 600) via CSS `text-transform` — the DOM/AT text stays "Liv" / "You". LIV left over her boxes, YOU right-aligned over his.
- **Same boxes:** Liv's turns lost the open letter-block asymmetry — both speakers now sit in the same shaped box (radius `var(--radius)`, 1px frame, padding 1rem/1.25rem). Differentiators are only the heavy rule (hers 3px ember at the LEFT, his 3px ink at the RIGHT) and the tint: both a step or two darker than the panel (paper-2 #F6EFE1) — **Liv: ember-tint #F8ECE7; storyteller: paper-3 #EFE5CF**. These are the only two declared steps that satisfy every constraint at once: ink text measures **12.9:1** on ember-tint and **12.0:1** on paper-3 (bar: ≥11:1). The file's one deeper tone, #DCD2BF (the disabled-button ground), was measured and rejected — ink on it is 10.0:1.
- **Reply section — distinct, darker:** the reply form is now an ink band (`.reply-band`: background ink #2B2622, radius 18px/16px small, house shadow) in the conversation box's rounded language. Button positions unchanged (Talk to Liv left, + Add, Discard when recording, Send compact at the right end). On the dark ground: label and voice-status in paper (14.0:1); the textarea stays white with ink text (15.0:1 — the strongest pairing on the page, where his words are composed); ember pills carry a paper border because ember against ink alone measures 1.92:1, under WCAG 1.4.11's 3:1 for control boundaries; Discard takes paper words and a paper edge (≈8.4:1 boundary); + Add takes paper words with a paper-wash hover, its open state keeping ember-on-tint; focus outlines in paper on this ground. Session actions and "Take your time" stay below the band on the canvas, unchanged.
- **Measured pairings (Oct 29, 2026):** label (ink-soft composite #58524C) on panel 6.7:1 · ink on Liv's ember-tint 12.9:1 · ink on storyteller's paper-3 12.0:1 · paper label on ink 14.0:1 · textarea ink-on-white 15.0:1 · white on ember (pill text) 7.8:1 · ember pill edge vs ink 1.92:1 → paper edge vs ink 14.0:1.
- DEMO-SCRIPT.md aligned (Beat 3 capture note, §6 layout checklist). JS behaviour, ids, and all media/mic/heard-you flows untouched — markup/CSS surgery only.
