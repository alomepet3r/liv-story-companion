"""Tests for Day 3 voice (server.voice, transcription wiring in
server.app / server.meta_client) and the conversation-first
composer's DOM contract (web/).

The bug these exist to prevent (Petro, live sitting, Oct 28,
2026): the storyteller shared audio of himself talking to Liv
and a video answering her question, and Liv replied she could
not listen or watch. Now: audio/video arrive with a browser-made
listening track (16 kHz mono WAV), the server transcribes it,
and the words are answered as speech — in the live context, in
the fallback companion, and in chapter sources. All content is
synthetic. Run: python3 -m unittest discover -s tests
"""
import io
import json
import struct
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from server import app, chapter, voice
from server.meta_client import MetaClient

WEB = Path(__file__).resolve().parent.parent / "web"

TRANSCRIPT = ("I grew up in Bamenda, and my father taught me "
              "patience, drop by drop.")


def make_wav(rate=16000, channels=1, sampwidth=2, seconds=0.25):
    """A small valid PCM WAV (quiet tone samples)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(rate)
        frames = int(rate * seconds)
        if sampwidth == 2:
            data = b"".join(struct.pack("<h", 1200) for _ in range(
                frames * channels))
        else:
            data = bytes([128]) * frames * channels
        wav.writeframes(data)
    return buf.getvalue()


class FakeClient:
    """Stands in for MetaClient: transcribes on demand, and its
    chat returns empty so app.py falls back to the canned
    companion (which is where transcript-listening is asserted)."""

    def __init__(self, transcript=TRANSCRIPT, fail=False):
        self.transcript = transcript
        self.fail = fail
        self.transcribe_calls = []

    def transcribe_wav(self, wav_bytes, model=None):
        self.transcribe_calls.append(wav_bytes)
        if self.fail:
            raise RuntimeError("asr down")
        return self.transcript, {"audio_duration_ms": 250}

    def chat(self, messages, model=None, **kwargs):
        return "", {}


class TestWavValidation(unittest.TestCase):
    def test_valid_16k_mono_accepted(self):
        info, error = voice.validate_listening_wav(make_wav())
        self.assertIsNone(error)
        self.assertEqual(info["rate"], 16000)
        self.assertEqual(info["channels"], 1)

    def test_valid_24k_mono_accepted(self):
        info, error = voice.validate_listening_wav(make_wav(rate=24000))
        self.assertIsNone(error)
        self.assertEqual(info["rate"], 24000)

    def test_stereo_rejected(self):
        _info, error = voice.validate_listening_wav(
            make_wav(channels=2))
        self.assertIsNotNone(error)

    def test_44100_rate_rejected(self):
        _info, error = voice.validate_listening_wav(
            make_wav(rate=44100))
        self.assertIsNotNone(error)

    def test_8bit_rejected(self):
        _info, error = voice.validate_listening_wav(
            make_wav(sampwidth=1))
        self.assertIsNotNone(error)

    def test_garbage_rejected(self):
        _info, error = voice.validate_listening_wav(b"webm bytes here")
        self.assertIsNotNone(error)

    def test_is_listening_wav(self):
        self.assertTrue(voice.is_listening_wav(make_wav()))
        self.assertFalse(voice.is_listening_wav(b"nope"))


class VoiceCase(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        chapter._shares.clear()
        self._saved_key = app.MODEL_API_KEY
        self._saved_client = app._live_client
        self.session = "voice-test"
        self.payload = {"session_id": self.session, "consent": True,
                        "age_confirmed": True}

    def tearDown(self):
        app.MODEL_API_KEY = self._saved_key
        app._live_client = self._saved_client
        app._sessions.clear()
        chapter._shares.clear()

    def use_client(self, client):
        app.MODEL_API_KEY = "test-key"
        app._live_client = client

    def upload(self, kind="audio", with_listen=True, main=None):
        fields = {"session_id": self.session, "consent": "true",
                  "age_confirmed": "true", "kind": kind}
        if main is None:
            main = ("rec.webm", "audio/webm", b"fake-webm-bytes")
        files = {"file": main}
        if with_listen:
            files["listen"] = ("listening.wav", "audio/wav",
                               make_wav())
        return app.handle_media_upload(fields, files)

    def begin(self):
        status, _ = app.handle_chat(dict(self.payload, message=""))
        self.assertEqual(status, 200)
        status, _ = app.handle_chat(
            dict(self.payload, message="Call me Margaret."))
        self.assertEqual(status, 200)


class TestTranscriptionFlow(VoiceCase):
    def test_transcript_stored_on_upload(self):
        fake = FakeClient()
        self.use_client(fake)
        status, body = self.upload()
        self.assertEqual(status, 200, body)
        self.assertEqual(body["transcript"], TRANSCRIPT)
        self.assertEqual(body["transcript_status"], "ok")
        self.assertEqual(len(fake.transcribe_calls), 1)
        item = app._session(self.session)["media"][body["media_id"]]
        self.assertEqual(item["transcript"], TRANSCRIPT)

    def test_uploaded_wav_is_its_own_listening_track(self):
        fake = FakeClient()
        self.use_client(fake)
        status, body = self.upload(
            with_listen=False,
            main=("rec.wav", "audio/wav", make_wav()))
        self.assertEqual(status, 200, body)
        self.assertEqual(body["transcript_status"], "ok")

    def test_invalid_listening_track_is_a_kind_400(self):
        self.use_client(FakeClient())
        fields = {"session_id": self.session, "consent": "true",
                  "age_confirmed": "true", "kind": "audio"}
        files = {"file": ("rec.webm", "audio/webm", b"x"),
                 "listen": ("listening.wav", "audio/wav",
                            b"not a wav at all")}
        status, body = app.handle_media_upload(fields, files)
        self.assertEqual(status, 400)
        self.assertIn("listening copy", body["error"])

    def test_video_without_listening_track_is_unavailable(self):
        self.use_client(FakeClient())
        status, body = self.upload(
            kind="video", with_listen=False,
            main=("clip.mp4", "video/mp4", b"fake-mp4"))
        self.assertEqual(status, 200, body)
        self.assertEqual(body["transcript_status"], "unavailable")
        self.assertIsNone(body["transcript"])

    def test_transcription_failure_is_recorded_not_faked(self):
        self.use_client(FakeClient(fail=True))
        status, body = self.upload()
        self.assertEqual(status, 200, body)
        self.assertEqual(body["transcript_status"], "failed")
        self.assertIsNone(body["transcript"])


class TestSpokenWordsAnswered(VoiceCase):
    def test_canned_reply_echoes_a_spoken_detail(self):
        self.use_client(FakeClient())
        self.begin()
        _status, body = self.upload()
        status, reply = app.handle_chat(dict(
            self.payload, message="",
            media_ids=[body["media_id"]]))
        self.assertEqual(status, 200, reply)
        # The fallback companion listened to the transcript with
        # its ordinary detail mechanics: Bamenda was followed up.
        self.assertIn("Bamenda", reply["reply"])
        self.assertNotIn("could not listen", reply["reply"])
        self.assertNotIn("cannot listen", reply["reply"])

    def test_transcript_enters_history_as_speech(self):
        self.use_client(FakeClient())
        self.begin()
        _status, body = self.upload()
        app.handle_chat(dict(self.payload, message="",
                             media_ids=[body["media_id"]]))
        sess = app._session(self.session)
        joined = "\n".join(t["content"] for t in sess["history"]
                           if t["role"] == "user")
        self.assertIn(TRANSCRIPT, joined)
        self.assertIn("spoke these words", joined)

    def test_failed_listening_asks_for_the_heart_in_typing(self):
        self.use_client(FakeClient(fail=True))
        self.begin()
        _status, body = self.upload()
        status, reply = app.handle_chat(dict(
            self.payload, message="",
            media_ids=[body["media_id"]]))
        self.assertEqual(status, 200, reply)
        self.assertIn("didn\u2019t work this time", reply["reply"])
        self.assertIn("type the heart", reply["reply"])

    def test_spoken_story_becomes_a_chapter(self):
        self.use_client(FakeClient())
        self.begin()
        _status, body = self.upload()
        app.handle_chat(dict(self.payload, message="",
                             media_ids=[body["media_id"]]))
        status, view = app.handle_chapter_outline(self.payload)
        self.assertEqual(status, 200, view)
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        draft_text = " ".join(
            p["text"] for s in view["chapter"]["draft"]["sections"]
            for p in s["paragraphs"])
        self.assertIn("Bamenda", draft_text)
        # The transcript is in the source corpus: nothing the
        # draft says from it is flagged as foreign.
        self.assertEqual(view["chapter"]["check"]["flags"], [])


class TestTranscribeClientContract(unittest.TestCase):
    def test_contributor_transcribe_model_refused(self):
        with self.assertRaises(ValueError):
            MetaClient("k").transcribe_wav(
                b"wav", model="muse-voice-transcribe-1.0-contributor")

    def test_transcribe_posts_asr_multipart(self):
        captured = {}

        class FakeResponse:
            def read(self):
                return json.dumps(
                    {"transcript": "hello world",
                     "audioDurationMs": 900}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def fake_open(req, timeout=None):
            captured["url"] = req.get_full_url()
            captured["body"] = req.data
            captured["ctype"] = req.get_header("Content-type")
            return FakeResponse()

        with patch("urllib.request.urlopen", side_effect=fake_open):
            text, info = MetaClient("k").transcribe_wav(b"RIFF....")
        self.assertEqual(text, "hello world")
        self.assertEqual(info["audio_duration_ms"], 900)
        self.assertTrue(captured["url"].endswith("/asr/transcribe"))
        self.assertIn("multipart/form-data", captured["ctype"])
        self.assertIn(b'name="request"', captured["body"])
        self.assertIn(b'"audioEncoding": "WAV"', captured["body"])
        self.assertIn(b"muse-voice-transcribe-1.0",
                      captured["body"])
        self.assertIn(b'name="audio"', captured["body"])


class TestComposerContract(unittest.TestCase):
    def test_attach_picker_replaces_media_bar(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="btn-attach"', html)
        self.assertIn('id="attach-picker"', html)
        self.assertIn("Photo or camera", html)
        self.assertIn("Voice recording", html)
        self.assertIn("Document or archive", html)
        self.assertNotIn('class="media-bar"', html)

    def test_picker_buttons_open_the_same_panels(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        for panel in ("panel-photo", "panel-audio", "panel-video",
                      "panel-archive"):
            self.assertIn('aria-controls="' + panel + '"', html)
            self.assertIn('id="' + panel + '"', html)

    def test_listening_track_is_built_in_the_browser(self):
        js = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn("makeListeningTrack", js)
        self.assertIn("decodeAudioData", js)
        self.assertIn("OfflineAudioContext", js)
        self.assertIn('fd.append("listen"', js)
        self.assertIn("attachPicker", js)

    def test_picker_hidden_state_survives_flex(self):
        css = (WEB / "styles.css").read_text(encoding="utf-8")
        self.assertIn(".attach-picker[hidden]", css)


if __name__ == "__main__":
    unittest.main()
