"""Offline unit tests for server.meta_client. No API key needed."""
import io
import json
import unittest
from unittest.mock import patch

from server.meta_client import MetaClient


class FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode()

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class TestMetaClient(unittest.TestCase):
    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            MetaClient("")

    def test_list_models_hits_models_endpoint(self):
        captured = {}

        def fake_open(req, timeout=None):
            captured["url"] = req.get_full_url()
            captured["auth"] = req.get_header("Authorization")
            return FakeResponse({"data": [{"id": "muse-spark-1.3"}]})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            data = MetaClient("test-key-123").list_models()

        self.assertEqual(captured["auth"], "Bearer test-key-123")
        self.assertTrue(captured["url"].endswith("/models"),
                        captured["url"])
        self.assertEqual(data["data"][0]["id"], "muse-spark-1.3")

    def test_chat_posts_completions_payload(self):
        captured = {}

        def fake_open(req, timeout=None):
            captured["url"] = req.get_full_url()
            captured["body"] = json.loads(req.data.decode())
            return FakeResponse(
                {"choices": [{"message": {"content": "hello there"}}],
                 "usage": {"total_tokens": 42}})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            text, usage = MetaClient("k").chat(
                [{"role": "user", "content": "hi"}], model="muse-spark-1.3")

        self.assertEqual(text, "hello there")
        self.assertEqual(usage["total_tokens"], 42)
        self.assertTrue(captured["url"].endswith("/chat/completions"))
        self.assertEqual(captured["body"]["model"], "muse-spark-1.3")
        self.assertEqual(captured["body"]["messages"][0]["role"], "user")


    def test_contributor_model_refused(self):
        # The -contributor IDs are a data-sharing (training rights)
        # tier; they must never carry storyteller content.
        with self.assertRaises(ValueError):
            MetaClient("k").chat([{"role": "user", "content": "hi"}],
                                 model="muse-spark-1.3-contributor")

    def test_empty_content_retries_with_bigger_budget(self):
        bodies = []

        def fake_open(req, timeout=None):
            bodies.append(json.loads(req.data.decode()))
            if len(bodies) == 1:
                return FakeResponse(
                    {"choices": [{"message": {"content": None},
                                  "finish_reason": "length"}],
                     "usage": {"total_tokens": 10}})
            return FakeResponse(
                {"choices": [{"message": {"content": "warm reply"}}],
                 "usage": {"total_tokens": 20}})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            text, _usage = MetaClient("k").chat(
                [{"role": "user", "content": "hi"}], model="muse-spark-1.3")

        self.assertEqual(text, "warm reply")
        self.assertEqual(len(bodies), 2)
        self.assertEqual(bodies[0]["reasoning_effort"], "minimal")
        self.assertGreater(bodies[1]["max_tokens"],
                           bodies[0]["max_tokens"])


WEBP = b"RIFF\x10\x00\x00\x00WEBP" + b"synthetic-webp-bytes"


class TestGenerateImage(unittest.TestCase):
    """muse-image-1.0 on POST /images/generations (surface
    verified live Oct 30, 2026; here the transport is faked)."""

    def test_generate_image_posts_and_decodes(self):
        import base64
        captured = {}

        def fake_open(req, timeout=None):
            captured["url"] = req.get_full_url()
            captured["body"] = json.loads(req.data.decode())
            return FakeResponse(
                {"created": 1,
                 "data": [{"b64_json":
                           base64.b64encode(WEBP).decode()}],
                 "output_format": "webp",
                 "usage": {"total_tokens": 100}})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            image, info = MetaClient("k").generate_image(
                "a quiet gym at dawn, no people, no text")

        self.assertEqual(image, WEBP)
        self.assertTrue(captured["url"].endswith(
            "/images/generations"), captured["url"])
        self.assertEqual(captured["body"]["model"],
                         "muse-image-1.0")
        self.assertEqual(captured["body"]["n"], 1)
        # Content type is sniffed from the bytes' own magic.
        self.assertEqual(info["content_type"], "image/webp")
        self.assertEqual(info["image_bytes"], len(WEBP))

    def test_png_magic_sniffed_as_png(self):
        import base64
        png = b"\x89PNG\r\n\x1a\n" + b"synthetic-png-bytes"

        def fake_open(req, timeout=None):
            return FakeResponse(
                {"data": [{"b64_json":
                           base64.b64encode(png).decode()}],
                 "output_format": "webp"})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            _image, info = MetaClient("k").generate_image("x")
        # The bytes outrank the response's claimed format.
        self.assertEqual(info["content_type"], "image/png")

    def test_contributor_image_model_refused(self):
        with self.assertRaises(ValueError):
            MetaClient("k").generate_image(
                "x", model="muse-image-1.0-contributor")

    def test_response_without_image_raises(self):
        def fake_open(req, timeout=None):
            return FakeResponse({"data": []})

        with patch("urllib.request.urlopen", side_effect=fake_open):
            with self.assertRaises(ValueError):
                MetaClient("k").generate_image("x")


if __name__ == "__main__":
    unittest.main()
