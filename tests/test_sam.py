"""Tests for the SAM scene-ledger slice (Day 5): one SAM 3.1
call (concept "person") runs before the Spark vision turn on a
photo turn, and its boxes become a one-line ledger of measured
facts — person count and frame share — in the live prompt,
worded as ground truth Liv must not contradict. The ledger
carries counts only, never identities (D28 by construction);
any SAM failure, timeout, or empty result degrades silently to
no ledger. The SAM call and the chat call are both faked — no
live calls in the suite. All content is synthetic.
Run: python3 -m unittest discover -s tests
"""
import json
import re
import unittest
from unittest.mock import patch

from server import app
from server.sam_client import SAM_TIMEOUT, SamClient, parse_boxes
from tests.test_meta_client import FakeResponse

JPEG = b"\xff\xd8\xff" + b"synthetic-jpeg-bytes"
PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic-image-bytes"

# The founder's stance-portrait box, as measured by the spike:
# one person filling ~94% of a 515x917 frame.
STANCE_BOX = {"x1": 4, "y1": 39, "x2": 512, "y2": 916,
              "w": 515, "h": 917}

STREAM_TWO = ("<0f>0"
              "<|box;x1=4;y1=39;x2=512;y2=916;w=515;h=917|>"
              "<|mask;x=0;y=0;data=abc123~!@#|>"
              "<|box;x1=10;y1=20;x2=110;y2=220;w=515;h=917|>"
              "<|mask;x=0;y=0;data=zzz999|>")


def sam_payload(text):
    """A Responses payload in the shape the spike recorded."""
    return {"model": "sam-3.1", "status": "completed",
            "output": [{"type": "message", "role": "assistant",
                        "content": [{"type": "output_text",
                                     "text": text}]}],
            "usage": {"images_processed": 1, "total_tokens": 0}}


def nine_boxes():
    return [{"x1": 10 + i * 55, "y1": 100, "x2": 50 + i * 55,
             "y2": 500, "w": 515, "h": 686} for i in range(9)]


class TestParseBoxes(unittest.TestCase):
    def test_stream_yields_boxes_masks_ignored(self):
        boxes = parse_boxes(STREAM_TWO)
        self.assertEqual(len(boxes), 2)
        self.assertEqual(boxes[0], STANCE_BOX)
        self.assertEqual(boxes[1]["x2"], 110)

    def test_empty_text_is_no_boxes(self):
        self.assertEqual(parse_boxes(""), [])
        self.assertEqual(parse_boxes(None), [])

    def test_mask_only_stream_is_no_boxes(self):
        self.assertEqual(
            parse_boxes("<|mask;x=0;y=0;data=abc|>"), [])


class TestSamClient(unittest.TestCase):
    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            SamClient("")

    def test_segment_posts_responses_payload_and_parses(self):
        captured = {}

        def fake_open(req, timeout=None):
            captured["url"] = req.get_full_url()
            captured["timeout"] = timeout
            captured["auth"] = req.get_header("Authorization")
            captured["body"] = json.loads(req.data.decode())
            return FakeResponse(sam_payload(STREAM_TWO))

        with patch("urllib.request.urlopen", side_effect=fake_open):
            boxes = SamClient("test-key").segment(JPEG, "person")

        self.assertTrue(captured["url"].endswith("/responses"),
                        captured["url"])
        self.assertEqual(captured["timeout"], SAM_TIMEOUT)
        self.assertTrue(captured["auth"].startswith("Bearer "))
        body = captured["body"]
        self.assertEqual(body["model"], "sam-3.1")
        content = body["input"][0]["content"]
        # The concept rides as a BARE noun phrase — a sentence
        # would silently no-op on the real surface.
        self.assertEqual(content[0], {"type": "input_text",
                                      "text": "person"})
        self.assertEqual(content[1]["type"], "input_image")
        self.assertTrue(content[1]["image_url"].startswith(
            "data:image/jpeg;base64,"))
        self.assertEqual(len(boxes), 2)
        self.assertEqual(boxes[0], STANCE_BOX)

    def test_timeout_is_named_and_has_headroom(self):
        # Spike measured 1.4–2.3 s per call; 10 s is the named
        # budget — headroom over the slowest, never a hang.
        self.assertEqual(SAM_TIMEOUT, 10)
        self.assertEqual(SamClient("k").timeout, 10)

    def test_empty_output_is_empty_list_not_error(self):
        def fake_open(req, timeout=None):
            return FakeResponse(sam_payload(""))

        with patch("urllib.request.urlopen", side_effect=fake_open):
            self.assertEqual(
                SamClient("k").segment(JPEG, "dog"), [])

    def test_disallowed_model_refused_before_any_call(self):
        called = []

        def fake_open(req, timeout=None):
            called.append(True)
            return FakeResponse(sam_payload(STREAM_TWO))

        with patch("urllib.request.urlopen", side_effect=fake_open):
            with self.assertRaises(ValueError):
                SamClient("k").segment(JPEG, "person",
                                        model="sam-3.1-contributor")
        self.assertEqual(called, [])

    def test_timeout_propagates_to_caller(self):
        def fake_open(req, timeout=None):
            raise TimeoutError("read timed out")

        with patch("urllib.request.urlopen", side_effect=fake_open):
            with self.assertRaises(TimeoutError):
                SamClient("k").segment(JPEG, "person")


class FakeChatClient:
    """Stands in for MetaClient on the chat path; captures the
    exact messages the live model would have been shown."""

    def __init__(self, reply="What a photograph — tell me about it."):
        self.reply = reply
        self.calls = []

    def chat(self, messages, model=None, **kwargs):
        self.calls.append(messages)
        return self.reply, {}

    def last_user_text(self):
        for message in reversed(self.calls[-1]):
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, list):
                return "".join(p.get("text", "") for p in content
                               if isinstance(p, dict))
            return content or ""
        return ""


class FakeSamClient:
    """Stands in for SamClient; returns canned boxes or raises."""

    def __init__(self, boxes=None, fail=None):
        self.boxes = [STANCE_BOX] if boxes is None else boxes
        self.fail = fail
        self.calls = []

    def segment(self, image_bytes, concept,
                content_type="image/jpeg", model=None):
        self.calls.append({"concept": concept,
                           "content_type": content_type,
                           "size": len(image_bytes)})
        if self.fail is not None:
            raise self.fail
        return [dict(b) for b in self.boxes]


class SceneLedgerCase(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        self._saved_key = app.MODEL_API_KEY
        self._saved_client = app._live_client
        self._saved_sam = getattr(app, "_sam_client", None)
        app.MODEL_API_KEY = ""       # no live clients unless faked
        app._live_client = None
        app._sam_client = None
        self.session = "sam-test"
        self.payload = {"session_id": self.session, "consent": True,
                        "age_confirmed": True}
        self.chat = FakeChatClient()
        self.sam = FakeSamClient()

    def tearDown(self):
        app.MODEL_API_KEY = self._saved_key
        app._live_client = self._saved_client
        app._sam_client = self._saved_sam
        app._sessions.clear()

    def go_live(self):
        app._live_client = self.chat
        app._sam_client = self.sam

    def upload_photo(self):
        fields = {"session_id": self.session, "consent": "true",
                  "age_confirmed": "true", "kind": "photo"}
        files = {"file": ("stance.jpg", "image/jpeg", JPEG)}
        status, body = app.handle_media_upload(fields, files)
        self.assertEqual(status, 200, body)
        return body["media_id"]

    def photo_turn(self, media_id):
        status, body = app.handle_chat(dict(
            self.payload, message="I wanted to show you this photo.",
            media_ids=[media_id]))
        self.assertEqual(status, 200, body)
        return body


class TestSceneLedger(SceneLedgerCase):
    def test_ledger_present_in_live_prompt_for_photo_turn(self):
        self.go_live()
        body = self.photo_turn(self.upload_photo())
        self.assertEqual(body["mode"], "live")
        self.assertEqual(len(self.sam.calls), 1)
        self.assertEqual(self.sam.calls[0]["concept"], "person")
        text = self.chat.last_user_text()
        self.assertIn("Scene ledger", text)
        self.assertIn("exactly 1 person is in this photo", text)
        self.assertIn("filling nearly the whole frame", text)
        self.assertIn("say 1 — never a different number", text)

    def test_ledger_counts_nine_people(self):
        self.sam = FakeSamClient(boxes=nine_boxes())
        self.go_live()
        self.photo_turn(self.upload_photo())
        text = self.chat.last_user_text()
        self.assertIn("exactly 9 people are in this photo", text)
        self.assertIn("together filling a good part of the frame",
                      text)
        self.assertIn("say 9 — never a different number", text)

    def test_ledger_carries_no_identity_language(self):
        self.go_live()
        self.photo_turn(self.upload_photo())
        text = self.chat.last_user_text()
        ledger = text[text.index("[Scene ledger"):]
        self.assertIn("say nothing about who the person is", ledger)
        # Whole-word matching: "how many people" must not trip
        # the check, and "person" is the ledger's only noun for
        # a human being.
        for word in ("man", "woman", "boy", "girl", "mother",
                     "father", "sister", "brother", "husband",
                     "wife", "daughter", "son", "child", "elderly"):
            self.assertIsNone(
                re.search(r"\b" + word + r"\b", ledger), word)

    def test_ledger_absent_on_sam_failure(self):
        self.sam = FakeSamClient(fail=RuntimeError("sam is down"))
        self.go_live()
        body = self.photo_turn(self.upload_photo())
        # The turn proceeds exactly as before SAM existed.
        self.assertEqual(body["mode"], "live")
        self.assertEqual(body["reply"], self.chat.reply)
        self.assertNotIn("Scene ledger", self.chat.last_user_text())

    def test_ledger_absent_on_sam_timeout(self):
        self.sam = FakeSamClient(fail=TimeoutError("read timed out"))
        self.go_live()
        body = self.photo_turn(self.upload_photo())
        self.assertEqual(body["mode"], "live")
        self.assertNotIn("Scene ledger", self.chat.last_user_text())

    def test_ledger_absent_on_empty_result(self):
        self.sam = FakeSamClient(boxes=[])
        self.go_live()
        body = self.photo_turn(self.upload_photo())
        self.assertEqual(body["mode"], "live")
        self.assertNotIn("Scene ledger", self.chat.last_user_text())

    def test_ledger_absent_without_sam_client(self):
        app._live_client = self.chat     # chat live, SAM absent
        body = self.photo_turn(self.upload_photo())
        self.assertEqual(body["mode"], "live")
        self.assertNotIn("Scene ledger", self.chat.last_user_text())

    def test_ledger_absent_on_non_photo_turn(self):
        self.go_live()
        status, body = app.handle_chat(dict(
            self.payload,
            message="My father taught me patience, drop by drop."))
        self.assertEqual(status, 200, body)
        self.assertEqual(body["mode"], "live")
        self.assertEqual(self.sam.calls, [])
        self.assertNotIn("Scene ledger", self.chat.last_user_text())

    def test_canned_path_never_calls_sam(self):
        app._sam_client = self.sam       # SAM ready, chat not live
        media_id = self.upload_photo()
        status, body = app.handle_chat(dict(
            self.payload, message="I wanted to show you this photo.",
            media_ids=[media_id]))
        self.assertEqual(status, 200, body)
        self.assertEqual(body["mode"], "canned")
        self.assertEqual(self.sam.calls, [])

    def test_ledger_never_enters_session_history(self):
        self.go_live()
        self.photo_turn(self.upload_photo())
        history = app._session(self.session)["history"]
        for entry in history:
            self.assertNotIn("Scene ledger", entry["content"])

    def test_archive_photo_turn_inherits_the_ledger(self):
        # Archive-shared photos land in the same media store and
        # ride the same vision turn — the ledger comes with them.
        self.go_live()
        sess = app._session(self.session)
        sess["media"]["m-arch"] = {
            "kind": "photo", "content_type": "image/png",
            "data": PNG, "name": "house.png", "source": "archive",
            "caption": "The red house on the hill.",
            "date_str": "12 May 2019", "album": "Family Days",
        }
        self.photo_turn("m-arch")
        text = self.chat.last_user_text()
        self.assertIn("The red house on the hill.", text)
        self.assertIn("Scene ledger", text)
        self.assertIn("exactly 1 person is in this photo", text)
        self.assertEqual(self.sam.calls[0]["content_type"],
                         "image/png")

    def test_media_turn_messages_injects_ledger_when_given(self):
        item = {"kind": "photo", "content_type": "image/png",
                "data": PNG, "name": "plain.png"}
        messages = [{"role": "user", "content": "A photo."}]
        shaped = app._media_turn_messages(
            messages, [item], "A photo.",
            scene_ledger="[Scene ledger — test line.]")
        text = "".join(p.get("text", "") for p in shaped[0]["content"]
                       if isinstance(p, dict))
        self.assertIn("[Scene ledger — test line.]", text)
        # And without one, the shaping is byte-for-byte the old one.
        shaped = app._media_turn_messages(messages, [item], "A photo.")
        text = "".join(p.get("text", "") for p in shaped[0]["content"]
                       if isinstance(p, dict))
        self.assertNotIn("Scene ledger", text)


if __name__ == "__main__":
    unittest.main()
