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


if __name__ == "__main__":
    unittest.main()
