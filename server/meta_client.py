"""Thin client for the Meta Model API (Muse Spark).

Uses the OpenAI-compatible chat surface:
    POST {base_url}/v1/chat/completions
    Authorization: Bearer <MODEL_API_KEY>

The key is passed in, never read from disk here — callers take it from
the environment (see config.py / .env.example).

Muse Spark 1.3 is a REASONING model: completion budget is spent on
reasoning tokens before any visible content appears. Probes on
Oct 26, 2026 (see DAY1-STATUS.md) showed that with default effort a
small max_tokens returns finish_reason="length" with content=null —
the whole budget burned on reasoning. The cheapest reliable
configuration for short conversational replies was
reasoning_effort="minimal" with max_tokens>=300. We therefore:
  * default to reasoning_effort="minimal", max_tokens=600;
  * retry ONCE with a larger budget (max_tokens=1500, effort="low")
    if the first attempt returns empty/null content, before the
    caller falls back to the canned companion.

Usage (token counts + latency only, never message content) is
appended as JSONL to a local log for budget tracking. The log lives
outside the repo by default (/tmp) and is never committed; override
with FIRESIDE_USAGE_LOG.

PRODUCTION MODEL ALLOWLIST: only "muse-spark-1.3" (Standard tier).
The "-contributor" model IDs are a data-sharing tier — prompts and
completions on them may be used to train future Meta models — so
they must NEVER carry storyteller content. chat() refuses any model
outside the allowlist.
"""
import base64
import json
import os
import time
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import CHAT_MODEL

ALLOWED_MODELS = {"muse-spark-1.3"}

# Transcription (Day 3). The exact model-id spelling was resolved
# from GET /v1/models on Oct 28, 2026 — "muse-voice-transcribe-1.0"
# — never guessed. It does NOT live on the chat surface (chat
# answers model_not_found for it); its endpoint is
# POST {base}/asr/transcribe, multipart/form-data with a `request`
# JSON part and an `audio` part, verified live the same day. The
# allowlist discipline is identical to chat's: only this Standard
# ID may ever carry storyteller audio — no contributor tier.
TRANSCRIBE_MODEL = "muse-voice-transcribe-1.0"
ALLOWED_TRANSCRIBE_MODELS = {TRANSCRIBE_MODEL}

# Image generation (Day 5). The model-id spelling was resolved
# from GET /v1/models on Oct 30, 2026 — "muse-image-1.0" — never
# guessed. Its surface is the OpenAI-compatible image surface:
# POST {base}/images/generations with {"model", "prompt", "n"},
# answered by {"data": [{"b64_json": ...}], "output_format": ...,
# "usage": ...} — verified live the same day with one harmless
# test prompt (the decoded image was WebP, RIFF magic). The
# allowlist discipline is identical to chat's and transcription's:
# only this Standard ID may ever carry a prompt derived from a
# chapter — no contributor tier.
IMAGE_MODEL = "muse-image-1.0"
ALLOWED_IMAGE_MODELS = {IMAGE_MODEL}

# Primary attempt: cheapest reliable per Oct 26 probes.
PRIMARY = {"max_tokens": 600, "reasoning_effort": "minimal"}
# Single retry on empty content: more room, slightly deeper reasoning.
RETRY = {"max_tokens": 1500, "reasoning_effort": "low"}


def _usage_log_path():
    override = os.environ.get("FIRESIDE_USAGE_LOG")
    if override:
        return Path(override)
    return Path("/tmp/fireside-usage.jsonl")


def _log_usage(record):
    try:
        path = _usage_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        pass  # Budget logging must never break a conversation turn.


class MetaClient:
    def __init__(self, api_key, base_url="https://api.meta.ai/v1",
                 timeout=60):
        if not api_key:
            raise ValueError("MODEL_API_KEY is not set — "
                             "copy .env.example to .env and add your key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method, path, payload=None):
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.load(resp)

    def list_models(self):
        """Harmless read: what this key is entitled to."""
        return self._request("GET", "/models")

    @staticmethod
    def _extract_text(data):
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            return ""
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):  # content-parts shape, just in case
            parts = [p.get("text", "") for p in content
                     if isinstance(p, dict) and p.get("type") == "text"]
            return "".join(parts).strip()
        return ""

    def _attempt(self, messages, model, params, attempt_no):
        payload = {"model": model, "messages": messages}
        payload.update(params)
        started = time.time()
        data = self._request("POST", "/chat/completions", payload)
        latency = round(time.time() - started, 3)
        usage = data.get("usage", {}) or {}
        details = usage.get("completion_tokens_details") or {}
        text = self._extract_text(data)
        _log_usage({
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "attempt": attempt_no,
            "max_tokens": params.get("max_tokens"),
            "reasoning_effort": params.get("reasoning_effort"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "reasoning_tokens": details.get("reasoning_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "latency_s": latency,
            "content_chars": len(text),
        })
        return text, usage

    def chat(self, messages, model=None, **kwargs):
        """One chat turn. Returns (assistant_text, usage_dict).

        Empty/null content (reasoning ate the budget) triggers one
        retry with a larger budget before giving up; the caller then
        falls back to the canned companion.
        """
        model = model or CHAT_MODEL
        if model not in ALLOWED_MODELS:
            raise ValueError(
                f"model {model!r} is not in the production allowlist "
                f"{sorted(ALLOWED_MODELS)} — contributor/data-sharing "
                "tiers must never carry storyteller content")
        params = dict(PRIMARY)
        params.update(kwargs)
        text, usage = self._attempt(messages, model, params, attempt_no=1)
        if text:
            return text, usage
        # Retry always escalates the budget past whatever the primary
        # used — a caller-supplied small max_tokens must not shrink it.
        retry_params = dict(RETRY)
        for key, value in kwargs.items():
            if key not in ("max_tokens", "reasoning_effort"):
                retry_params[key] = value
        if isinstance(kwargs.get("max_tokens"), int):
            retry_params["max_tokens"] = max(RETRY["max_tokens"],
                                              kwargs["max_tokens"])
        text, usage = self._attempt(messages, model, retry_params,
                                    attempt_no=2)
        return text, usage

    def transcribe_wav(self, wav_bytes, model=None):
        """Transcribe one listening track (mono PCM WAV, 16/24 kHz).

        Returns (transcript_text, info) where info carries the
        model's own audioDurationMs. Raises on transport/API
        failure — the caller decides the honest fallback; an empty
        transcript comes back as "" (a silent recording is a
        result, not an exception). Usage logging records model +
        audio duration + latency only, never audio or text.
        """
        model = model or TRANSCRIBE_MODEL
        if model not in ALLOWED_TRANSCRIBE_MODELS:
            raise ValueError(
                f"model {model!r} is not in the transcription "
                f"allowlist {sorted(ALLOWED_TRANSCRIBE_MODELS)} — "
                "contributor/data-sharing tiers must never carry "
                "storyteller audio")
        boundary = "----fireside" + uuid.uuid4().hex
        request_part = json.dumps(
            {"model": model, "audioEncoding": "WAV"}).encode()
        body = b"".join([
            ("--" + boundary + "\r\n"
             "Content-Disposition: form-data; name=\"request\"\r\n"
             "Content-Type: application/json\r\n\r\n").encode(),
            request_part, b"\r\n",
            ("--" + boundary + "\r\n"
             "Content-Disposition: form-data; name=\"audio\"; "
             "filename=\"listening.wav\"\r\n"
             "Content-Type: audio/wav\r\n\r\n").encode(),
            wav_bytes, b"\r\n",
            ("--" + boundary + "--\r\n").encode(),
        ])
        req = urllib.request.Request(
            self.base_url + "/asr/transcribe",
            data=body,
            headers={
                "Content-Type": "multipart/form-data; boundary="
                                + boundary,
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        started = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        latency = round(time.time() - started, 3)
        text = (data.get("transcript") or "").strip()
        _log_usage({
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "kind": "transcribe",
            "audio_duration_ms": data.get("audioDurationMs"),
            "latency_s": latency,
            "content_chars": len(text),
        })
        return text, {"audio_duration_ms": data.get("audioDurationMs"),
                      "model": model}

    @staticmethod
    def _image_content_type(image_bytes, output_format=None):
        """Name the image's type from its own magic bytes — what
        the bytes say outranks what the response claims; the
        response's output_format is only a fallback."""
        if image_bytes[:4] == b"\x89PNG":
            return "image/png"
        if image_bytes[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if image_bytes[:4] == b"RIFF" \
                and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        return {"webp": "image/webp", "png": "image/png",
                "jpeg": "image/jpeg", "jpg": "image/jpeg"}.get(
                    str(output_format or "").lower(), "image/webp")

    def generate_image(self, prompt, model=None):
        """Generate one image from a text prompt (muse-image-1.0).

        Returns (image_bytes, info) where info carries the model,
        the sniffed content type, and the byte count. Raises on
        transport/API failure or on a response carrying no image —
        the caller decides the honest fallback. Usage logging
        records model + latency + byte count + whatever numeric
        usage fields the API returned — never the prompt.
        """
        model = model or IMAGE_MODEL
        if model not in ALLOWED_IMAGE_MODELS:
            raise ValueError(
                f"model {model!r} is not in the image allowlist "
                f"{sorted(ALLOWED_IMAGE_MODELS)} — contributor/"
                "data-sharing tiers must never carry prompts "
                "derived from a storyteller's chapter")
        started = time.time()
        data = self._request("POST", "/images/generations",
                             {"model": model, "prompt": prompt,
                              "n": 1})
        latency = round(time.time() - started, 3)
        try:
            encoded = data["data"][0]["b64_json"]
            image_bytes = base64.b64decode(encoded)
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError(
                "the image response carried no image") from None
        if not image_bytes:
            raise ValueError("the image response carried no image")
        content_type = self._image_content_type(
            image_bytes, data.get("output_format"))
        usage = data.get("usage", {}) or {}
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "kind": "image",
            "latency_s": latency,
            "image_bytes": len(image_bytes),
        }
        for key in ("prompt_tokens", "completion_tokens",
                    "total_tokens", "input_tokens", "output_tokens"):
            if isinstance(usage.get(key), (int, float)):
                record[key] = usage[key]
        _log_usage(record)
        return image_bytes, {"model": model,
                             "content_type": content_type,
                             "image_bytes": len(image_bytes)}
