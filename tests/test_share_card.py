"""Keepsake share card: after approval the chapter view carries
a share card (title, dedication, ONE summary line, share link);
before approval there is no card. The card is in-product only.
Drives server/chapter.py directly (deterministic, no model).
"""
import unittest
from pathlib import Path

from server import chapter

WEB = Path(__file__).resolve().parent.parent / "web"


def _session():
    return {
        "history": [
            {"role": "user",
             "content": "My grandfather kept a workshop in Dayton."},
            {"role": "user",
             "content": "He taught me to sharpen a chisel there."},
        ],
        "media": {},
        "chapter": None,
    }


class TestShareCard(unittest.TestCase):
    def setUp(self):
        chapter._shares.clear()

    def tearDown(self):
        chapter._shares.clear()

    def _approved_view(self):
        sess = _session()
        status, _ = chapter.start_outline(sess)
        self.assertEqual(status, 200)
        status, _ = chapter.replan(sess, dedication="my family")
        self.assertEqual(status, 200)
        status, _ = chapter.make_draft(sess)
        self.assertEqual(status, 200)
        return chapter.approve(sess, "share-card-test")

    def test_no_card_before_approval(self):
        sess = _session()
        self.assertIsNone(chapter.share_card_for(sess.get("chapter")))
        status, view = chapter.start_outline(sess)
        self.assertEqual(status, 200)
        self.assertIsNone(view["chapter"]["share_card"])
        status, view = chapter.make_draft(sess)
        self.assertEqual(status, 200)
        self.assertIsNone(view["chapter"]["share_card"])

    def test_card_after_approval(self):
        status, view = self._approved_view()
        self.assertEqual(status, 200, view)
        card = view["chapter"]["share_card"]
        self.assertIsNotNone(card)
        self.assertTrue(card["title"])
        self.assertEqual(card["dedication"], "my family")
        self.assertIn(card["title"], card["summary_line"])
        self.assertIn("approved by the storyteller",
                      card["summary_line"])
        self.assertEqual(card["share_url"], view["share_url"])
        self.assertTrue(card["share_url"].startswith("/keepsake/"))

    def test_card_copy_is_claim_disciplined(self):
        status, view = self._approved_view()
        card = view["chapter"]["share_card"]
        lowered = card["summary_line"].lower()
        self.assertNotIn("verbatim", lowered)
        self.assertNotIn("word-for-word", lowered)
        self.assertNotIn("word for word", lowered)


class TestShareCardFrontend(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")

    def test_card_markup_and_copy_affordances(self):
        for marker in ('id="share-card"', 'id="share-card-title"',
                       'id="share-card-dedication"',
                       'id="share-card-summary"',
                       'id="share-card-copy-link"',
                       'id="share-card-copy-text"',
                       "Copy link", "Copy card text"):
            self.assertIn(marker, self.html + self.js)

    def test_copy_is_clipboard_only_no_posting(self):
        self.assertIn("navigator.clipboard.writeText", self.js)
        card_js = self.js.split("Keepsake share card", 1)[1] \
            .split("function openChapter", 1)[0]
        self.assertNotIn("fetch(", card_js)


if __name__ == "__main__":
    unittest.main()
