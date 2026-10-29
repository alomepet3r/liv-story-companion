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


if __name__ == "__main__":
    unittest.main()
