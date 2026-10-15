"""Thin client for the Meta Model API (Muse Spark).

Uses the OpenAI-compatible chat surface:
    POST {base_url}/v1/chat/completions
    Authorization: Bearer <MODEL_API_KEY>

The key is passed in, never read from disk here — callers take it from
the environment (see config.py / .env.example).
"""
import json
import urllib.request

from .config import CHAT_MODEL


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

    def chat(self, messages, model=None, **kwargs):
        """One chat turn. Returns (assistant_text, usage_dict)."""
        payload = {"model": model or CHAT_MODEL, "messages": messages}
        payload.update(kwargs)
        data = self._request("POST", "/chat/completions", payload)
        message = data["choices"][0]["message"]
        return message.get("content", ""), data.get("usage", {})
