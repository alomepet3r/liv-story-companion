"""Liv-only + greeting contracts (founder rulings, Oct 29, 2026).

Three rulings pinned here:

- LIV-ONLY: the companion is Liv — only Liv. The Livio/Livia
  variants mapped to voices, but TTS was cut from this build, so
  the consent-screen choice changed nothing real. A client may
  still SEND a companion/companion_name value; it is accepted and
  ignored, and a session's name can never vary from Liv.
- GREETING: Liv introduces herself in the founder's words —
  "Hi, I'm Liv!" — keeping the pace and skip beats, and the
  name ask now carries its own skip ("…or no name at all — and
  you can skip this too; whatever feels right.").
- ONE-ASK GUARANTEE: the name question is asked exactly once.
  A clear name answer is captured; an explicit skip/decline is
  honoured with no name stored and no re-ask; a substantive
  telling launched straight past the question is received as
  the story — never mined for a name, never circled back to.
- MIC BUTTON (UI/UX ruling, same day): an inline SVG microphone
  (never the emoji glyph), an always-visible "Talk to Liv"
  label, and a distinct recording state in CSS.
- CONVERSATION LAYOUT (founder rulings, Oct 29, 2026, in
  three acts: his layout ruling, his hand sketch, his own
  vetted mockup — then CASANOVA Direction B "Sheet",
  chosen by the founder over Direction A the same night):
  the app is ONE calm sheet centred on a quiet desk. The
  header is the wordmark as he drew it — "FireSide" in
  bold italic near-black with an ember flame glyph after
  the word — over the sub-line "Talking To Liv" (title
  case as drawn; his phrasing: to, not with), Atkinson
  bold, ink, left-aligned. ONE paper tone (--sheet) and
  ONE card white: the cream stack (--paper-2/--paper-3/
  --box) is collapsed, --gold/--sage are deleted, and
  there is ONE red — --ember-deep is deleted (build
  condition 1), so Liv's label and rules are pure ember.
  Speaker labels ride above each turn, small — LIV left
  in ember, YOU right in the storyteller's blue
  (--user-blue #1458B4, declared by his design), in
  capitals set by CSS with NO marker glyphs; the DOM
  text stays "Liv" / "You" for assistive technology.
  Both speakers' turns live in the SAME square white box
  at the SAME size (parity is deliberate), differentiated
  by 3px rules — ember at Liv's LEFT, user-blue at the
  storyteller's RIGHT — and the label colours. Dialogue
  boxes are RECTANGULAR (border-radius 0); the sheet,
  the field, and the buttons keep their curves. The 4px
  ember seam is DELETED (condition 3). The reply section
  is a dark band exactly as wide as the SHEET, never
  100vw: label "Reply", a white field at 20px radius,
  one action row (Talk to Liv — the row's sole ember
  fill · + Add · Send as a full pill at the right end
  with a NON-ember ink fill, condition 2), the session
  actions inside the band as ghost outline buttons at
  52px with borders in the tokenised --ghost-line
  (#C7C3BC), and "Take your time" beneath them in its
  Cormorant cameo — nothing of the session area remains
  on the sheet below the band. Standing UI principle, in
  his words: minimalist but very functional,
  conversational, intuitive, effective.
"""
import unittest
from pathlib import Path

from server import app
from server.canned import CannedCompanion, normalize_companion_name

WEB = Path(__file__).resolve().parent.parent / "web"

NAME_ASK = ("Before we begin — what would you like me to call "
            "you? A name, a nickname, or no name at all — and "
            "you can skip this too; whatever feels right.")
STORY = ("I grew up in Bamenda, in Cameroon, and the house I "
         "remember most is the one behind the old market, where "
         "my grandmother kept chickens and the rain on the zinc "
         "roof sounded like drumming.")


class TestLivOnlyNames(unittest.TestCase):
    def test_normalize_always_returns_liv(self):
        for value in ("Liv", "Livio", "Livia", "livia", "Bob",
                      "", None, 42):
            self.assertEqual(normalize_companion_name(value), "Liv")

    def test_companion_cannot_be_constructed_with_a_variant(self):
        self.assertEqual(CannedCompanion("Livia").name, "Liv")
        self.assertEqual(CannedCompanion("Livio").name, "Liv")
        self.assertEqual(CannedCompanion().name, "Liv")


class TestGreeting(unittest.TestCase):
    def test_greeting_opens_with_the_founders_words(self):
        self.assertTrue(
            CannedCompanion().greeting().startswith("Hi, I’m Liv!"))

    def test_greeting_keeps_pace_skip_and_the_ask_with_its_skip(self):
        greeting = CannedCompanion().greeting()
        self.assertIn("we can go at your pace", greeting)
        self.assertIn("And we can skip anything — just say so.",
                      greeting)
        self.assertIn(NAME_ASK, greeting)


class _EmptyChatClient:
    """Live-shaped stub whose chat returns empty, so handle_chat
    lands on the canned companion (the parity path)."""

    def chat(self, messages, model=None, **kwargs):
        return "", {}

    def transcribe_wav(self, wav_bytes, model=None):
        raise RuntimeError("not used here")


class TestHandlerLivOnly(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        self._saved_client = app._live_client
        app._live_client = _EmptyChatClient()

    def tearDown(self):
        app._live_client = self._saved_client
        app._sessions.clear()

    def chat(self, session_id, message, **extra):
        payload = {"session_id": session_id, "consent": True,
                   "age_confirmed": True, "message": message}
        payload.update(extra)
        status, body = app.handle_chat(payload)
        self.assertEqual(status, 200, body)
        return body

    def test_variant_request_still_greets_as_liv(self):
        body = self.chat("s-variant", "", companion="Livia")
        self.assertEqual(body["companion"], "Liv")
        self.assertTrue(body["reply"].startswith("Hi, I’m Liv!"))

    def test_variant_sent_mid_session_changes_nothing(self):
        self.chat("s-mid", "", companion_name="Livio")
        self.chat("s-mid", "Call me Petro.")
        body = self.chat("s-mid", "Petro is fine.",
                         companion="Livia")
        self.assertEqual(body["companion"], "Liv")
        self.assertEqual(
            app._sessions["s-mid"]["companion_name"], "Liv")

    def test_sessions_never_vary(self):
        for i, asked in enumerate(("Livio", "Livia", "Liv", None)):
            sid = "s-%d" % i
            extra = {} if asked is None else {"companion": asked}
            body = self.chat(sid, "", **extra)
            self.assertEqual(body["companion"], "Liv")


class TestOneAskGuarantee(unittest.TestCase):
    """The three first-reply shapes (founder catch, Oct 29)."""

    def companion_after(self, first_reply):
        c = CannedCompanion()
        c.greeting()
        reply = c.reply(first_reply)
        return c, reply

    def test_clear_name_is_captured_and_used_sparingly(self):
        c, reply = self.companion_after("Call me Petro.")
        self.assertEqual(c.preferred_name, "Petro")
        self.assertEqual(c.name_state, "set")
        self.assertIn("Petro", reply)

    def test_explicit_skip_stores_no_name(self):
        for decline in ("Skip.", "I'd rather not say.",
                        "No name at all, thanks."):
            c, reply = self.companion_after(decline)
            self.assertIsNone(c.preferred_name, decline)
            self.assertEqual(c.name_state, "declined", decline)
            self.assertIn("no name at all is perfectly fine", reply)

    def test_decline_is_never_reasked(self):
        c, _ = self.companion_after("Skip.")
        follow = c.reply("Judith was like a second mother to me.")
        self.assertNotIn("what would you like me to call", follow)
        self.assertIsNone(c.preferred_name)

    def test_story_first_reply_is_a_telling_not_a_name(self):
        c, reply = self.companion_after(STORY)
        self.assertIsNone(c.preferred_name)
        self.assertEqual(c.name_state, "missed")
        # The story was heard as a story: a detail was gathered
        # and the reply follows up on the telling itself.
        self.assertTrue(c.details)
        self.assertIn("Bamenda", reply)

    def test_story_first_reply_is_never_reasked(self):
        c, _ = self.companion_after(STORY)
        follow = c.reply("The roof leaked every rainy season.")
        self.assertNotIn("what would you like me to call", follow)
        self.assertIsNone(c.preferred_name)

    def test_im_from_is_a_telling_not_a_name(self):
        c, _ = self.companion_after("I'm from Bamenda.")
        self.assertIsNone(c.preferred_name)
        self.assertEqual(c.name_state, "missed")


class TestFrontendContract(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")

    def test_no_variants_no_choice_in_the_page(self):
        self.assertNotIn("Livio", self.html)
        self.assertNotIn("Livia", self.html)
        self.assertNotIn('name="companion"', self.html)
        self.assertIn('class="companion-intro"', self.html)

    def test_no_companion_choice_sent_or_wired(self):
        self.assertNotIn("Livio", self.js)
        self.assertNotIn("Livia", self.js)
        self.assertNotIn('input[name="companion"]', self.js)
        self.assertNotIn("companion:", self.js)

    def test_mic_icon_is_svg_never_emoji(self):
        self.assertNotIn("\U0001F399", self.html)  # 🎙 emoji
        self.assertIn('<span class="mic-icon" aria-hidden="true">'
                      "<svg", self.html)
        self.assertIn('id="mic-label">Talk to Liv<', self.html)

    def test_mic_button_styles_two_colour_and_recording_state(self):
        resting = self.css.split(".mic-btn {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--ember)", resting)
        self.assertIn("color: #FFFFFF", resting)
        self.assertIn("border-radius: 999px", resting)
        self.assertIn("min-height: 3.25rem", resting)
        recording = self.css.split(".mic-btn.recording {", 1)[1]
        recording = recording.split("}", 1)[0]
        self.assertIn("background: var(--ink)", recording)
        self.assertIn(".mic-btn.recording::after", self.css)


class TestConversationLayout(unittest.TestCase):
    """Founder layout ruling (Oct 29, 2026) — see module docstring."""

    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")
        self.css = (WEB / "styles.css").read_text(encoding="utf-8")

    def test_page_title_begins_with_the_brand(self):
        self.assertIn(
            "<title>Fireside — Your stories, in your own voice"
            "</title>", self.html)

    def test_brand_lockup_wordmark_and_flame(self):
        # The vetted mockup's wordmark: bold italic "FireSide"
        # (capital F, capital S) with the ember flame glyph
        # AFTER the word — the flame-in-ring medallion and the
        # Cormorant name are gone.
        self.assertIn('class="brand-lockup"', self.html)
        self.assertIn('<span class="brand-name">FireSide</span>',
                      self.html)
        self.assertIn('class="brand-flame"', self.html)
        self.assertLess(self.html.index('class="brand-name"'),
                        self.html.index('class="brand-flame"'))
        self.assertNotIn('class="brand-mark"', self.html)
        name = self.css.split(".brand-name {", 1)[1].split("}", 1)[0]
        self.assertIn("font-style: italic", name)
        self.assertIn("font-weight: 700", name)
        # Direction B type scale: the wordmark at 32px.
        self.assertIn("font-size: 2rem", name)
        flame = self.css.split(".brand-flame {", 1)[1]
        flame = flame.split("}", 1)[0]
        self.assertIn("color: var(--ember)", flame)

    def test_sub_line_is_the_founders_phrasing(self):
        # His phrasing ("to", not "with"), presented title
        # case as drawn in the vetted mockup — Atkinson bold,
        # left-aligned, no longer Cormorant italic.
        self.assertIn(
            '<h1 id="chat-heading" class="chat-subtitle">'
            "Talking To Liv</h1>", self.html)
        self.assertNotIn("Talking with", self.html)
        sub = self.css.split(".chat-subtitle {", 1)[1].split("}", 1)[0]
        self.assertIn("font-weight: 700", sub)
        self.assertIn("text-align: left", sub)
        self.assertNotIn("italic", sub)
        # Direction B: 24px, in ink (14.0:1 on the sheet) —
        # no longer the quiet gray of the vetted mockup.
        self.assertIn("font-size: 1.5rem", sub)
        self.assertIn("color: var(--ink)", sub)

    def test_conversation_lives_on_the_sheet(self):
        # Direction B: masthead and main both live inside the
        # one sheet; the desk shows around it on wide screens.
        sheet = self.html.index('class="sheet"')
        masthead = self.html.index('class="masthead"')
        main = self.html.index("<main>")
        self.assertLess(sheet, masthead)
        self.assertLess(masthead, main)
        # The declared tokens of the Sheet world.
        for token in ("--desk: #E8E2D6", "--sheet: #FBF7EF",
                      "--control: #6B655E", "--ink-2: #59524C",
                      "--ghost-line: #C7C3BC"):
            self.assertIn(token, self.css)
        # The cream stack and the second red are gone, and
        # the quiet ink is a solid token now, not an rgba.
        for gone in ("--paper:", "--paper-2:", "--paper-3:",
                     "--box:", "--gold:", "--sage:",
                     "--ember-deep:", "var(--ember-deep)",
                     "var(--ink-soft)"):
            self.assertNotIn(gone, self.css)
        body = self.css.split("body {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--desk)", body)
        sheet_css = self.css.split(".sheet {", 1)[1]
        sheet_css = sheet_css.split("}", 1)[0]
        self.assertIn("background: var(--sheet)", sheet_css)
        self.assertIn("max-width: 760px", sheet_css)
        self.assertIn("border: 1px solid var(--control)",
                      sheet_css)
        self.assertIn("box-shadow:", sheet_css)
        # The turns still group inside the panel wrapper, and
        # the composer still follows — but the wrapper itself
        # carries no surface of its own any more.
        panel = self.html.index('class="conversation-panel"')
        messages = self.html.index('id="messages"')
        listening = self.html.index('id="listening"')
        composer = self.html.index('class="composer"')
        self.assertLess(panel, messages)
        self.assertLess(messages, listening)
        self.assertLess(listening, composer)
        block = self.css.split(".conversation-panel {", 1)[1]
        block = block.split("}", 1)[0]
        self.assertIn("background: transparent", block)
        self.assertIn("border: none", block)
        self.assertIn("box-shadow: none", block)

    def test_speaker_labels_small_caps_and_marker_free(self):
        # The founder's sketch restored the labels; his review
        # of the deployed build then removed the marker glyphs
        # (refinement, Oct 29, 2026): the name alone, in
        # capitals set by CSS, at the same small size. The DOM
        # text app.js writes stays "Liv" / "You", so AT reads
        # the speaker as before.
        self.assertIn('label.className = "who"', self.js)
        block = self.css.split(".msg .who {", 1)[1].split("}", 1)[0]
        self.assertIn("display: block", block)
        # Direction B type scale: 13px, bold, tracked out.
        self.assertIn("font-size: 0.8125rem", block)
        self.assertIn("font-weight: 700", block)
        self.assertIn("letter-spacing: 0.08em", block)
        self.assertIn("text-transform: uppercase", block)
        # The visually-hidden recipe stays gone.
        self.assertNotIn("clip-path: inset(50%)", block)
        self.assertNotIn("position: absolute", block)
        # No markers anywhere: no ::before content on the
        # labels, and neither glyph survives in the stylesheet.
        self.assertNotIn(".who::before", self.css)
        self.assertNotIn("◆", self.css)
        self.assertNotIn("●", self.css)
        # The storyteller's label still aligns right, over
        # his boxes.
        you = self.css.split(".msg.storyteller .who {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("text-align: right", you)

    def test_turn_boxes_unified_with_mirrored_rules(self):
        # Direction B (Oct 29, 2026): both speakers' turns
        # live in the SAME square white box (--card) on the
        # sheet — the shared cream tint is gone with the
        # cream stack. The differentiators are the 3px rules
        # (a margin mark, not a flag: ember at Liv's LEFT,
        # the storyteller's blue at his RIGHT) and the label
        # colours. Dialogue boxes stay RECTANGULAR (founder
        # amendment: radius 0, rules flush); the sheet, the
        # field, and the buttons keep their curves. Parity
        # is deliberate (reconciliation D16): both turns set
        # at the same 19px / 1.65. Ink on the card is 15.0:1.
        self.assertIn("--user-blue: #1458B4", self.css)
        liv = self.css.split(".msg.companion {", 1)[1].split("}", 1)[0]
        self.assertIn("border-left: 3px solid var(--ember)", liv)
        self.assertIn("background: var(--card)", liv)
        self.assertIn("border-radius: 0", liv)
        you = self.css.split(".msg.storyteller {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("border-right: 3px solid var(--user-blue)",
                      you)
        self.assertIn("background: var(--card)", you)
        self.assertIn("border-radius: 0", you)
        # Same shape: the padding declaration is identical.
        liv_pad = [ln.strip() for ln in liv.splitlines()
                   if "padding:" in ln]
        you_pad = [ln.strip() for ln in you.splitlines()
                   if "padding:" in ln]
        self.assertEqual(liv_pad, you_pad)
        self.assertEqual(liv_pad,
                         ["padding: 1.125rem 1.375rem;"])
        # Deliberate size parity: identical font-size and
        # line-height on both speakers' turns.
        for block in (liv, you):
            self.assertIn("font-size: 1.19rem", block)
            self.assertIn("line-height: 1.65", block)
        # The label colours ride with the speakers: LIV in
        # the single ember (7.3:1 on the sheet, AAA — the
        # ember-deep second red is deleted), YOU in his
        # blue (6.4:1 on the sheet).
        liv_who = self.css.split(".msg.companion .who {", 1)[1]
        liv_who = liv_who.split("}", 1)[0]
        self.assertIn("color: var(--ember)", liv_who)
        you_who = self.css.split(".msg.storyteller .who {", 1)[1]
        you_who = you_who.split("}", 1)[0]
        self.assertIn("color: var(--user-blue)", you_who)
        self.assertIn("text-align: right", you_who)

    def test_composer_follows_the_sketch(self):
        # Below the box: the reply label and field, then ONE
        # action row — Talk to Liv, + Add (quiet, moved down
        # from its old row above the field), Send compact at
        # the row's right end. No full-width send bar.
        field = self.html.index('id="chat-input"')
        mic = self.html.index('id="mic-btn"')
        attach = self.html.index('id="btn-attach"')
        send = self.html.index('class="primary small send-btn"')
        self.assertLess(field, mic)
        self.assertLess(mic, attach)
        self.assertLess(attach, send)
        self.assertIn('class="attach-btn attach-quiet"', self.html)
        # The button left the old standalone attach row; the
        # picker it controls stayed in place above the form.
        row = self.html.split('class="attach-row"', 1)[1]
        row = row.split("</div>", 1)[0]
        self.assertNotIn('id="btn-attach"', row)
        self.assertIn('id="attach-picker"', row)
        rule = self.css.split(".composer-actions .send-btn {", 1)[1]
        rule = rule.split("}", 1)[0]
        self.assertIn("margin-left: auto", rule)

    def test_reply_section_is_a_sheet_width_dark_band(self):
        # Direction B (Oct 29, 2026): the reply band stays
        # dark and distinct (ruling 4 kept in kind) but its
        # width is the SHEET's width, never the viewport's —
        # the form reaches the sheet's edges through
        # negative margins of the sheet's own side padding.
        # The ember seam is deleted (condition 3). The
        # session actions and the "Take your time" line live
        # INSIDE the band; nothing of the session area
        # remains on the sheet below it. Button positions
        # inside are unchanged (the sketch test above still
        # pins their order).
        self.assertIn('<form id="chat-form" class="reply-band">',
                      self.html)
        self.assertIn('<label for="chat-input">Reply</label>',
                      self.html)
        band = self.css.split(".reply-band {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--ink)", band)
        self.assertIn("margin: 0 calc(-1 * var(--pad-side))",
                      band)
        self.assertIn("padding: 1.875rem var(--pad-side)",
                      band)
        self.assertNotIn("100vw", band)
        # The seam is gone — element and rule both.
        self.assertNotIn('class="seam"', self.html)
        self.assertNotIn(".seam {", self.css)
        # The session area is inside the form (the band):
        form_open = self.html.index('<form id="chat-form"')
        form_close = self.html.index("</form>")
        for frag in ('id="finish-btn"', 'id="chapter-btn"',
                     'id="end-session-btn"',
                     "Take your time. There is no hurry here."):
            where = self.html.index(frag)
            self.assertLess(form_open, where, frag)
            self.assertLess(where, form_close, frag)
        # On the dark ground the words are sheet (14.0:1)…
        self.assertIn("#chat-form.reply-band label", self.css)
        self.assertIn(".reply-band .voice-status", self.css)
        # …the field is white with a sheet border and the
        # Sheet drawing's 20px radius, its text set at the
        # heritage floor line-height (condition 5)…
        field = self.css.split(".reply-band #chat-input {", 1)[1]
        field = field.split("}", 1)[0]
        self.assertIn("border: 2px solid var(--sheet)", field)
        self.assertIn("border-radius: 20px", field)
        area = self.css.split("#chat-input {", 1)[1]
        area = area.split("}", 1)[0]
        self.assertIn("line-height: 1.65", area)
        # …the mic pill — the row's sole ember fill — keeps
        # its sheet border, because ember against ink alone
        # is 1.92:1, under WCAG 1.4.11's 3:1 for a control's
        # boundary…
        mic = self.css.split(".reply-band .mic-btn {", 1)[1]
        mic = mic.split("}", 1)[0]
        self.assertIn("border-color: var(--sheet)", mic)
        # …and Send is NOT an ember fill (condition 2): an
        # ink fill with a sheet border, still a full pill
        # at the row's right end.
        send = self.css.split(
            ".reply-band .composer-actions .send-btn {", 1)[1]
        send = send.split("}", 1)[0]
        self.assertIn("background: var(--ink)", send)
        self.assertNotIn("var(--ember)", send)
        self.assertIn("border: 1.5px solid var(--sheet)", send)
        row = self.css.split(".composer-actions .send-btn {", 1)[1]
        row = row.split("}", 1)[0]
        self.assertIn("margin-left: auto", row)
        self.assertIn("border-radius: 999px", row)
        # The session buttons: ghost borders in the
        # tokenised --ghost-line (condition 3 — the drawing's
        # literal #C7C3BC, now a named token), at the full
        # 52px touch height (condition 4).
        ghost = self.css.split(".reply-band button.secondary {",
                               1)[1].split("}", 1)[0]
        self.assertIn("border-color: var(--ghost-line)", ghost)
        secondary = self.css.split("button.secondary {", 1)[1]
        secondary = secondary.split("}", 1)[0]
        self.assertIn("min-height: 3.25rem", secondary)
        # "Take your time" closes the band in its Cormorant
        # cameo (Direction B's one serif appearance here).
        calm = self.css.split("#chat-screen #chat-form .quiet {",
                              1)[1].split("}", 1)[0]
        self.assertIn("Cormorant Garamond", calm)
        self.assertIn("color: var(--sheet)", calm)


if __name__ == "__main__":
    unittest.main()
