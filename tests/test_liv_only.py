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
- CONVERSATION LAYOUT (founder ruling, same day; refined by
  his hand sketch, then his review of the deployed build;
  finally rebuilt to HIS OWN vetted mockup, same day): the
  header is the wordmark as he drew it — "FireSide" in bold
  italic near-black with an ember flame glyph after the
  word — over the sub-line "Talking To Liv" (title case as
  drawn; his phrasing: to, not with), Atkinson bold, quiet
  gray, left-aligned. The transcript lives in a contained
  panel (the box); an ember seam (4px) runs under it; then
  the reply band. Speaker labels ride above each turn,
  small — LIV left in ember-deep, YOU right in the
  storyteller's blue (--user-blue #1458B4, declared by his
  design), in capitals set by CSS with NO marker glyphs;
  the DOM text stays "Liv" / "You" for assistive
  technology. Both speakers' turns live in the SAME shaped
  box on ONE shared tint (--box); the differentiators are
  the 14px slabs — ember at Liv's LEFT, user-blue at the
  storyteller's RIGHT — and the label colours. AMENDMENT
  (founder, same day): dialogue boxes are RECTANGULAR
  (border-radius 0, slabs flush); the panel, the field,
  and the buttons keep their curves. The reply section is
  a full-bleed dark band (the form on ink, broken out to
  the viewport's width, content aligned to the column):
  label "Reply", a white field with the mockup's 24px
  radius, one action row (Talk to Liv · + Add · Send as a
  full pill at the right end), and the session actions
  inside the band as ghost outline buttons with "Take
  your time" beneath them — nothing of the session area
  remains on the canvas. Standing UI principle, in his
  words: minimalist but very functional, conversational,
  intuitive, effective.
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

    def test_conversation_lives_in_a_panel(self):
        panel = self.html.index('class="conversation-panel"')
        messages = self.html.index('id="messages"')
        listening = self.html.index('id="listening"')
        composer = self.html.index('class="composer"')
        # Turns and the listening state are inside the box; the
        # composer stays below it.
        self.assertLess(panel, messages)
        self.assertLess(messages, listening)
        self.assertLess(listening, composer)
        block = self.css.split(".conversation-panel {", 1)[1]
        block = block.split("}", 1)[0]
        self.assertIn("background: var(--paper-2)", block)
        self.assertIn("border: 1px solid var(--line)", block)
        self.assertIn("border-radius: 18px", block)

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
        self.assertIn("font-size: 0.82rem", block)
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

    def test_turn_boxes_unified_with_mirrored_slabs(self):
        # Vetted mockup (Oct 29, 2026): both speakers' turns
        # live in the SAME shaped box on ONE shared tint
        # (--box) — the ember-tint / paper-3 split is gone.
        # The differentiators are the 14px slabs (ember at
        # Liv's LEFT, the storyteller's blue at his RIGHT)
        # and the label colours. AMENDMENT (founder, same
        # day): dialogue boxes are RECTANGULAR — radius 0,
        # slabs flush at the square edges; the panel, the
        # field, and the buttons keep their curves. Ink text
        # on the box measures 12.4:1.
        self.assertIn("--box: #EFE9DC", self.css)
        self.assertIn("--user-blue: #1458B4", self.css)
        liv = self.css.split(".msg.companion {", 1)[1].split("}", 1)[0]
        self.assertIn("border-left: 14px solid var(--ember)", liv)
        self.assertIn("background: var(--box)", liv)
        self.assertIn("border-radius: 0", liv)
        you = self.css.split(".msg.storyteller {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("border-right: 14px solid var(--user-blue)",
                      you)
        self.assertIn("background: var(--box)", you)
        self.assertIn("border-radius: 0", you)
        # Same shape: the padding declaration is identical.
        liv_pad = [ln.strip() for ln in liv.splitlines()
                   if "padding:" in ln]
        you_pad = [ln.strip() for ln in you.splitlines()
                   if "padding:" in ln]
        self.assertEqual(liv_pad, you_pad)
        self.assertEqual(liv_pad, ["padding: 1rem 1.25rem;"])
        # The label colours ride with the speakers: LIV in
        # ember-deep (8.4:1 on the box), YOU in his blue
        # (5.6:1 on the box).
        liv_who = self.css.split(".msg.companion .who {", 1)[1]
        liv_who = liv_who.split("}", 1)[0]
        self.assertIn("color: var(--ember-deep)", liv_who)
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

    def test_reply_section_is_a_full_bleed_dark_band(self):
        # Vetted mockup (Oct 29, 2026): the reply band breaks
        # out to the full viewport width — the inset rounded
        # panel is superseded. The ember seam stands between
        # the conversation panel and the band. The session
        # actions and the "Take your time" line live INSIDE
        # the band; nothing of the session area remains on
        # the canvas below it. Button positions inside are
        # unchanged (the sketch test above still pins their
        # order).
        self.assertIn('<form id="chat-form" class="reply-band">',
                      self.html)
        self.assertIn('<label for="chat-input">Reply</label>',
                      self.html)
        band = self.css.split(".reply-band {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--ink)", band)
        self.assertIn("width: 100vw", band)
        self.assertIn("margin-left: calc(50% - 50vw)", band)
        # The seam: 4px of ember, spanning the column, in the
        # DOM immediately before the band.
        self.assertIn('class="seam"', self.html)
        self.assertLess(self.html.index('class="seam"'),
                        self.html.index('<form id="chat-form"'))
        seam = self.css.split(".seam {", 1)[1].split("}", 1)[0]
        self.assertIn("height: 4px", seam)
        self.assertIn("background: var(--ember)", seam)
        # The session area is inside the form (the band):
        form_open = self.html.index('<form id="chat-form"')
        form_close = self.html.index("</form>")
        for frag in ('id="finish-btn"', 'id="chapter-btn"',
                     'id="end-session-btn"',
                     "Take your time. There is no hurry here."):
            where = self.html.index(frag)
            self.assertLess(form_open, where, frag)
            self.assertLess(where, form_close, frag)
        # On the dark ground the words are paper (14.0:1)…
        self.assertIn("#chat-form.reply-band label", self.css)
        self.assertIn(".reply-band .voice-status", self.css)
        # …the field is white with a paper border and the
        # mockup's 24px radius…
        field = self.css.split(".reply-band #chat-input {", 1)[1]
        field = field.split("}", 1)[0]
        self.assertIn("border: 2px solid var(--paper)", field)
        self.assertIn("border-radius: 24px", field)
        # …and the ember pills carry a paper border, because
        # ember against ink alone is 1.92:1 — under WCAG
        # 1.4.11's 3:1 for a control's boundary.
        mic = self.css.split(".reply-band .mic-btn {", 1)[1]
        mic = mic.split("}", 1)[0]
        self.assertIn("border-color: var(--paper)", mic)
        send = self.css.split(".reply-band button.primary {", 1)[1]
        send = send.split("}", 1)[0]
        self.assertIn("border: 1.5px solid var(--paper)", send)
        # Send is a full pill now, matching Talk to Liv's
        # shape, still at the row's right end.
        row = self.css.split(".composer-actions .send-btn {", 1)[1]
        row = row.split("}", 1)[0]
        self.assertIn("margin-left: auto", row)
        self.assertIn("border-radius: 999px", row)


if __name__ == "__main__":
    unittest.main()
