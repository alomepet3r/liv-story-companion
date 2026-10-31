"""Thin client for Meta SAM 3.1 scene grounding (Day 5 slice).

SAM does NOT live on the chat surface (chat answers 404 with a
pointer here). Its surface is the Responses API:

    POST {base_url}/responses
    Authorization: Bearer <MODEL_API_KEY>
    {"model": "sam-3.1",
     "input": [{"role": "user", "content": [
         {"type": "input_text", "text": "<one bare noun phrase>"},
         {"type": "input_image",
          "image_url": "data:<mime>;base64,..."}]}]}

The wire format was found empirically by the Oct 30, 2026 spike
(see spike-sam/VERDICT.md in the hackathon folder), traps and
all:

  * The concept MUST be a bare noun phrase ("person"). A
    sentence ("Segment the person in this photo.") returns
    HTTP 200 with images_processed: 1 and EMPTY output — a
    silent no-op. One concept per call.
  * The answer's output_text is a token stream:
    "<0f>0<|box;x1=..;y1=..;x2=..;y2=..;w=W;h=H|><|mask;...|>"
    Box coordinates are RAW PIXELS of the source image; the
    w/h fields are the image's own dimensions. The mask
    payloads that follow each box are large and are discarded
    unread — only boxes are parsed.
  * An unmatched concept is NOT an error: HTTP 200 with empty
    text. Empty therefore means "nothing found" — segment()
    returns [] for it, and the caller decides what an absence
    is worth (the scene ledger stays silent on one).

PRODUCTION ALLOWLIST: only "sam-3.1". segment() refuses any
other model ID — the same discipline as meta_client's chat /
transcribe / image allowlists: no other tier may ever carry a
storyteller's photo.

The key is passed in, never read from disk here — callers take
it from the environment (see config.py). Usage logging records
model + concept + box count + latency only, never image bytes
or anything from the photo; the log is meta_client's (outside
the repo, never committed).

SAM supplies verified facts — presence, count, position. It
never speaks to the storyteller and never identifies anyone:
counting is not naming (recognition doctrine, D28).
"""
import base64
import json
import re
import time
import urllib.request
from datetime import datetime, timezone

from .meta_client import _log_usage

SAM_MODEL = "sam-3.1"
ALLOWED_SAM_MODELS = {SAM_MODEL}

# Timeout for one segmentation call. The Oct 30 spike measured
# 1.4–2.3 s per call across eight live calls; 10 s is roughly
# 4x headroom over the slowest, while keeping a stuck call
# from ever hanging a sitting — the caller degrades silently
# to no-ledger behaviour on any failure anyway.
SAM_TIMEOUT = 10

_BOX_RE = re.compile(
    r"<\|box;x1=(\d+);y1=(\d+);x2=(\d+);y2=(\d+);w=(\d+);h=(\d+)\|>")


def parse_boxes(text):
    """Extract box dicts from a SAM output_text stream.

    Mask payloads in the stream are ignored — the regex only
    matches complete box tokens. Returns [] for empty or
    garbled text (an unmatched concept answers empty).
    """
    boxes = []
    for match in _BOX_RE.finditer(text or ""):
        x1, y1, x2, y2, w, h = (int(g) for g in match.groups())
        boxes.append({"x1": x1, "y1": y1, "x2": x2, "y2": y2,
                      "w": w, "h": h})
    return boxes


def _extract_text(data):
    """The output_text of a Responses payload, or ""."""
    if isinstance(data.get("output_text"), str):
        return data["output_text"]
    parts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if isinstance(part, dict) \
                    and part.get("type") == "output_text":
                parts.append(part.get("text") or "")
    return "".join(parts)


class SamClient:
    def __init__(self, api_key, base_url="https://api.meta.ai/v1",
                 timeout=SAM_TIMEOUT):
        if not api_key:
            raise ValueError("MODEL_API_KEY is not set — "
                             "copy .env.example to .env and add your key")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def segment(self, image_bytes, concept,
                content_type="image/jpeg", model=None):
        """Segment ONE bare-noun-phrase concept in one photo.

        Returns a list of box dicts {x1, y1, x2, y2, w, h} in
        raw source-image pixels — [] when the concept is not
        found (an empty answer is a result, not an error).
        Raises on a disallowed model, on transport failure, and
        on timeout — the caller degrades silently.
        """
        model = model or SAM_MODEL
        if model not in ALLOWED_SAM_MODELS:
            raise ValueError(
                f"model {model!r} is not in the SAM allowlist "
                f"{sorted(ALLOWED_SAM_MODELS)} — no other tier "
                "may ever carry a storyteller's photo")
        uri = ("data:" + content_type + ";base64,"
               + base64.b64encode(image_bytes).decode("ascii"))
        payload = {"model": model,
                   "input": [{"role": "user", "content": [
                       {"type": "input_text", "text": concept},
                       {"type": "input_image",
                        "image_url": uri}]}]}
        req = urllib.request.Request(
            self.base_url + "/responses",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        started = time.time()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.load(resp)
        latency = round(time.time() - started, 3)
        boxes = parse_boxes(_extract_text(data))
        usage = data.get("usage", {}) or {}
        _log_usage({
            "ts": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "kind": "segment",
            "concept": concept,
            "boxes": len(boxes),
            "images_processed": usage.get("images_processed"),
            "latency_s": latency,
        })
        return boxes
