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
  his hand sketch, same day; refined again on his review of
  the deployed build, same day): the header is one compact
  brand lockup — the flame-in-ring mark beside the word
  Fireside, the project's filed public name — with "Talking
  to Liv" (his phrasing: to, not with) as the quiet sub-line
  beneath it. The transcript lives in a contained panel (the
  box), composer below it. Speaker labels ride above each
  turn, small — LIV left, YOU right, in capitals set by CSS,
  with NO marker glyphs (the sketch's diamonds/dots were
  removed on review); the DOM text stays "Liv" / "You" for
  assistive technology. Both speakers' turns live in the
  SAME shaped box (same radius, border, padding), a step
  or two darker than the panel: Liv's in ember-tint ruled
  ember at the left, the storyteller's in paper-3 ruled
  ink at the right — the rule and the tint are the only
  differentiators. The reply section is a distinct dark
  band (the form on ink, same rounded language; button
  positions unchanged). The composer follows the sketch:
  reply label, field, then one action row (Talk to Liv ·
  + Add · compact Send at the right end) — no full-width
  send bar. Standing UI principle, in his words:
  minimalist but very functional, conversational,
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

    def test_brand_lockup_mark_beside_fireside(self):
        self.assertIn('class="brand-lockup"', self.html)
        self.assertIn('<span class="brand-name">Fireside</span>',
                      self.html)
        # The old roundel-over-"Liv" stack is gone.
        self.assertNotIn('class="wordmark', self.html)

    def test_sub_line_is_the_founders_phrasing(self):
        self.assertIn(
            '<h1 id="chat-heading" class="chat-subtitle">'
            "Talking to Liv</h1>", self.html)
        self.assertNotIn("Talking with", self.html)

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

    def test_turn_boxes_unified_with_mirrored_rules(self):
        # Refinement (Oct 29, 2026): both speakers' turns live
        # in the SAME shaped box — same radius, border, and
        # padding. The only differentiators are the heavy
        # rule (Liv's ember at the LEFT, the storyteller's
        # ink at the RIGHT — the sketch's hatched edges) and
        # the tint: both a step or two darker than the panel
        # (paper-2), one step apart — ember-tint for Liv,
        # paper-3 for the storyteller. Ink text holds past
        # 11:1 on both (12.9:1 and 12.0:1, measured).
        liv = self.css.split(".msg.companion {", 1)[1].split("}", 1)[0]
        self.assertIn("border-left: 3px solid var(--ember)", liv)
        self.assertIn("background: var(--ember-tint)", liv)
        self.assertIn("border-radius: var(--radius)", liv)
        you = self.css.split(".msg.storyteller {", 1)[1]
        you = you.split("}", 1)[0]
        self.assertIn("border-right: 3px solid var(--ink)", you)
        self.assertIn("background: var(--paper-3)", you)
        self.assertIn("border-radius: var(--radius)", you)
        # Same shape: the padding declaration is identical.
        liv_pad = [ln.strip() for ln in liv.splitlines()
                   if "padding:" in ln]
        you_pad = [ln.strip() for ln in you.splitlines()
                   if "padding:" in ln]
        self.assertEqual(liv_pad, you_pad)
        self.assertEqual(liv_pad, ["padding: 1rem 1.25rem;"])

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

    def test_reply_section_is_a_dark_band(self):
        # Refinement (Oct 29, 2026): the reply section is
        # distinct — the form sits on ink, in the conversation
        # box's rounded language, with the session actions and
        # the "Take your time" line left below it on the
        # canvas. Button positions inside are unchanged (the
        # sketch test above still pins their order).
        self.assertIn('<form id="chat-form" class="reply-band">',
                      self.html)
        band = self.css.split(".reply-band {", 1)[1].split("}", 1)[0]
        self.assertIn("background: var(--ink)", band)
        self.assertIn("border-radius: 18px", band)
        # On the dark ground the words are paper (14.0:1)…
        self.assertIn("#chat-form.reply-band label", self.css)
        self.assertIn(".reply-band .voice-status", self.css)
        # …and the ember pills carry a paper border, because
        # ember against ink alone is 1.92:1 — under WCAG
        # 1.4.11's 3:1 for a control's boundary.
        mic = self.css.split(".reply-band .mic-btn {", 1)[1]
        mic = mic.split("}", 1)[0]
        self.assertIn("border-color: var(--paper)", mic)
        send = self.css.split(".reply-band button.primary {", 1)[1]
        send = send.split("}", 1)[0]
        self.assertIn("border: 1.5px solid var(--paper)", send)


if __name__ == "__main__":
    unittest.main()
