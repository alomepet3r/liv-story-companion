"""Guided judge path: a no-login demo over synthetic material
only. It must serve a preloaded made-up story, run the REAL
source-check on its planted detail, create no session, call no
model, and leave the real sitting's consent + 18+ gates intact.
"""
import unittest
from pathlib import Path

from server import app, chapter, guided

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"


class TestGuidedPayload(unittest.TestCase):
    def test_payload_is_labelled_synthetic(self):
        payload = guided.demo_payload()
        self.assertTrue(payload["guided_demo"])
        self.assertTrue(payload["synthetic"])
        self.assertIn("made-up sample story", payload["notice"])
        self.assertIn("grandfather", payload["telling"][0]["text"])

    def test_source_check_is_real_and_flags_the_plant(self):
        payload = guided.demo_payload()
        # Recompute with the chapter module's own check: the
        # endpoint's result must be that function's result.
        sources = guided._sources()
        expected = chapter.source_check(guided._draft(), sources)
        self.assertEqual(payload["check"], expected)
        flags = [f["text"] for f in payload["check"]["flags"]]
        self.assertIn("1968", flags)
        self.assertEqual(payload["planted_detail"], "1968")

    def test_payload_walks_the_real_beats(self):
        payload = guided.demo_payload()
        ids = [s["id"] for s in payload["steps"]]
        self.assertEqual(ids, ["talk", "plan", "draft", "check",
                               "approve", "keepsake"])
        self.assertTrue(payload["draft"]["sections"])
        self.assertTrue(payload["summary_line"])


class TestGuidedEndpoint(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        chapter._shares.clear()

    def tearDown(self):
        app._sessions.clear()
        chapter._shares.clear()

    def test_endpoint_needs_no_gate_and_creates_nothing(self):
        status, payload = app.handle_guided_demo()
        self.assertEqual(status, 200)
        self.assertTrue(payload["synthetic"])
        # No session was created and no share link minted.
        self.assertEqual(app._sessions, {})
        self.assertEqual(chapter._shares, {})

    def test_real_gates_are_untouched(self):
        # Chat still refuses without consent and without 18+.
        status, _ = app.handle_chat({"session_id": "g1",
                                     "message": "hello"})
        self.assertEqual(status, 403)
        status, _ = app.handle_chat({"session_id": "g1",
                                     "message": "hello",
                                     "consent": True})
        self.assertEqual(status, 403)
        # Chapter routes keep their gates too.
        status, _ = app.handle_chapter_outline(
            {"session_id": "g1"})
        self.assertEqual(status, 403)


class TestGuidedFrontend(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")

    def test_entry_is_clearly_linked_and_labelled(self):
        self.assertIn("Try the 4-minute guided sitting", self.html)
        self.assertIn('id="guided-start"', self.html)
        self.assertIn('id="guided-screen"', self.html)
        self.assertIn("made-up sample story", self.html)

    def test_guided_path_uses_only_the_demo_endpoint(self):
        self.assertIn("/api/guided/demo", self.js)
        guided = self.js.split("Guided demo (judge path)", 1)[1]
        self.assertNotIn('fetch("/api/chat"', guided)
        self.assertNotIn('fetch("/api/chapter', guided)
        self.assertNotIn("chapterCall(", guided)


if __name__ == "__main__":
    unittest.main()
