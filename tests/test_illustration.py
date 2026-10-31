"""Tests for the keepsake illustration slice (Day 5): after a
chapter is APPROVED, the storyteller may ask for one Muse Image
illustration, built only from the chapter's own furniture (title,
dedication, section headings) under the baked-in no-people /
no-faces / no-likeness / no-text discipline. The live image call
is exercised through a fake client; no real calls in the suite.
All content is synthetic. Run: python3 -m unittest discover -s tests
"""
import unittest

from server import app, chapter
from tests.test_archive import PNG

STORY_TURNS = [
    "Call me Margaret.",
    "My father took me to Bamenda in 1984, to ride the first "
    "elevator the town had ever seen.",
    "I was seven years old, and the doors closed and the room "
    "moved, and I held his hand the whole way up.",
    "He told me that day: never be afraid of new things, "
    "Margaret. Little by little, drop by drop.",
]

ILLUSTRATION_BYTES = PNG  # synthetic stand-in image bytes


class FakeImageClient:
    """Stands in for MetaClient on the illustration path."""

    def __init__(self, image=ILLUSTRATION_BYTES,
                 content_type="image/png"):
        self.image = image
        self.content_type = content_type
        self.prompts = []

    def generate_image(self, prompt, model=None):
        self.prompts.append(prompt)
        return self.image, {"model": "muse-image-1.0",
                            "content_type": self.content_type,
                            "image_bytes": len(self.image)}


class FailingImageClient:
    def generate_image(self, prompt, model=None):
        raise RuntimeError("the image surface is down")


class IllustrationCase(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        chapter._shares.clear()
        self._saved_key = app.MODEL_API_KEY
        self._saved_client = app._live_client
        app.MODEL_API_KEY = ""       # no live client unless faked
        app._live_client = None
        self.session = "illustration-test"
        self.payload = {"session_id": self.session, "consent": True,
                        "age_confirmed": True}

    def tearDown(self):
        app.MODEL_API_KEY = self._saved_key
        app._live_client = self._saved_client
        app._sessions.clear()
        chapter._shares.clear()

    def tell_story(self):
        for turn in STORY_TURNS:
            status, body = app.handle_chat(
                dict(self.payload, message=turn))
            self.assertEqual(status, 200, body)

    def approve_chapter(self, dedication="my family"):
        self.tell_story()
        status, view = app.handle_chapter_outline(self.payload)
        self.assertEqual(status, 200, view)
        status, view = app.handle_chapter_replan(
            dict(self.payload, dedication=dedication))
        self.assertEqual(status, 200, view)
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        status, view = app.handle_chapter_approve(self.payload)
        self.assertEqual(status, 200, view)
        return view


class TestIllustrationGates(IllustrationCase):
    def test_illustrate_requires_consent(self):
        status, _ = app.handle_chapter_illustrate(
            dict(self.payload, consent=False))
        self.assertEqual(status, 403)

    def test_illustrate_requires_age_confirmation(self):
        status, _ = app.handle_chapter_illustrate(
            dict(self.payload, age_confirmed=False))
        self.assertEqual(status, 403)

    def test_no_chapter_at_all_is_409(self):
        status, body = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 409)
        self.assertIn("approved chapter", body["error"])

    def test_unapproved_chapter_is_409(self):
        self.tell_story()
        status, _view = app.handle_chapter_outline(self.payload)
        self.assertEqual(status, 200)
        status, body = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 409)
        # And still 409 with a draft sitting in review.
        status, _view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200)
        status, body = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 409)


class TestIllustrationFlow(IllustrationCase):
    def test_illustrate_approved_chapter_end_to_end(self):
        app._live_client = FakeImageClient()
        view = self.approve_chapter()
        token = view["share_url"].rsplit("/", 1)[1]

        status, view = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 200, view)
        self.assertTrue(view["chapter"]["illustration"])
        self.assertEqual(view["chapter"]["illustration_version"], 1)
        step_ids = [s["id"] for s in view["steps"]]
        self.assertIn("illustrate", step_ids)

        sess = app._sessions[self.session]
        stored = chapter.get_illustration(sess)
        self.assertEqual(stored["data"], ILLUSTRATION_BYTES)
        self.assertEqual(stored["content_type"], "image/png")

        snapshot = chapter.get_share(token)
        self.assertTrue(snapshot["illustration"])
        html = chapter.render_keepsake_html(snapshot)
        self.assertIn("/api/chapter/illustration?session_id="
                      + self.session, html)
        self.assertIn('alt="An illustration made for this '
                      'chapter"', html)

    def test_reasking_replaces_the_illustration(self):
        first = FakeImageClient(image=b"first-image-bytes")
        app._live_client = first
        self.approve_chapter()
        status, view = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 200, view)

        second_bytes = b"second-image-bytes"
        app._live_client = FakeImageClient(image=second_bytes)
        status, view = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 200, view)
        self.assertEqual(view["chapter"]["illustration_version"], 2)
        sess = app._sessions[self.session]
        self.assertEqual(chapter.get_illustration(sess)["data"],
                         second_bytes)
        token = view["share_url"].rsplit("/", 1)[1]
        snapshot = chapter.get_share(token)
        self.assertEqual(snapshot["illustration_version"], 2)
        self.assertIn("&v=2", chapter.render_keepsake_html(snapshot))

    def test_prompt_uses_furniture_only_under_the_discipline(self):
        fake = FakeImageClient()
        app._live_client = fake
        self.approve_chapter(dedication="my family")
        status, _view = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 200)
        self.assertEqual(len(fake.prompts), 1)
        prompt = fake.prompts[0]
        sess = app._sessions[self.session]
        ch = sess["chapter"]
        # Furniture: title, dedication, every section heading.
        self.assertIn(ch["draft"]["title"], prompt)
        self.assertIn("my family", prompt)
        for section in ch["draft"]["sections"]:
            self.assertIn(section["heading"], prompt)
        # The discipline is in the prompt itself.
        lowered = prompt.lower()
        self.assertIn("no people", lowered)
        self.assertIn("no faces", lowered)
        self.assertIn("no likeness of any real person", lowered)
        self.assertIn("no words", lowered)
        # No raw telling reaches the image model: phrases that
        # exist only in the tellings' body text are absent. (A
        # detail inside the TITLE is furniture, not transcript —
        # the title is the storyteller's own chosen heading.)
        self.assertNotIn("elevator", prompt)
        self.assertNotIn("held his hand", prompt)
        self.assertNotIn("seven years old", prompt)

    def test_build_prompt_without_dedication(self):
        fake_chapter = {"draft": {
            "title": "A Quiet Morning",
            "dedication": "",
            "sections": [{"heading": "The beginning"},
                         {"heading": "Where it rests"}]}}
        prompt = chapter.build_illustration_prompt(fake_chapter)
        self.assertIn("A Quiet Morning", prompt)
        self.assertIn("The beginning", prompt)
        self.assertIn("Where it rests", prompt)
        self.assertNotIn("dedicated to", prompt)


class TestIllustrationFailure(IllustrationCase):
    def assert_chapter_untouched(self, before_steps):
        sess = app._sessions[self.session]
        ch = sess["chapter"]
        self.assertEqual(ch["stage"], "approved")
        self.assertIsNone(ch.get("illustration"))
        token = ch["share_token"]
        self.assertFalse(chapter.get_share(token)["illustration"])
        html = chapter.render_keepsake_html(
            chapter.get_share(token))
        self.assertNotIn("/api/chapter/illustration", html)
        self.assertEqual([s["id"] for s in ch["steps"]],
                         before_steps)

    def test_failing_generator_leaves_chapter_intact(self):
        app._live_client = FailingImageClient()
        self.approve_chapter()
        sess = app._sessions[self.session]
        before = [s["id"] for s in sess["chapter"]["steps"]]
        status, body = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 502)
        self.assertEqual(body["error"],
                         chapter.ILLUSTRATION_FAILURE)
        self.assertIn("complete without it", body["error"])
        self.assert_chapter_untouched(before)

    def test_no_live_client_is_the_same_honest_failure(self):
        self.approve_chapter()
        sess = app._sessions[self.session]
        before = [s["id"] for s in sess["chapter"]["steps"]]
        status, body = app.handle_chapter_illustrate(self.payload)
        self.assertEqual(status, 502)
        self.assertEqual(body["error"],
                         chapter.ILLUSTRATION_FAILURE)
        self.assert_chapter_untouched(before)


if __name__ == "__main__":
    unittest.main()
