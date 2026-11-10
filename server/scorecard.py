"""Public scorecard surface — renders the evaluation's metrics.

The metrics live in SCORECARD.json at the repo root, emitted by
the eval harness (`eval/run_eval.py`) as structured data:
stable metric IDs, labels, values, sample sizes and caveats,
with the run's metadata (date, harness, fixtures) in a separate
object. This module reads that JSON at request time — it never
parses SCORECARD.md (the human-readable companion document)
back into numbers, so metadata can never be mistaken for a
metric and no markdown artifact can reach the page. Until the
JSON exists, the honest fallback state is served —
"evaluation pending" — never invented figures.
"""
import html
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORECARD_JSON_PATH = REPO_ROOT / "SCORECARD.json"

# The landing's three headline slots, by metric ID, in order.
HEADLINE_METRIC_IDS = (
    "source_check_flagged",
    "source_check_false_flags",
    "count_corrections_adopted",
)

_METADATA_LABELS = (
    ("date", "Date"),
    ("harness", "Harness"),
    ("fixtures", "Fixtures"),
    ("fixture_scope", "Fixture scope"),
    ("live_model_calls", "Live model calls"),
    ("chapter_cost_time", "Chapter cost / time"),
)


def _clean(value):
    """Plain text only: structured values should already be
    clean, but no markdown marker ever reaches the page."""
    text = str(value if value is not None else "")
    return text.replace("`", "").replace("**", "").strip()


def _normalise_metric(raw):
    if not isinstance(raw, dict):
        return None
    metric = {}
    for key, value in raw.items():
        if isinstance(value, str):
            metric[key] = _clean(value)
        elif isinstance(value, list):
            metric[key] = [_clean(v) if isinstance(v, str) else v
                           for v in value]
        else:
            metric[key] = value
    if not metric.get("id") or not metric.get("label") \
            or "value" not in metric:
        return None
    metric["value"] = _clean(metric["value"])
    return metric


def load_metrics_document(path=None):
    """The parsed SCORECARD.json document, or None when it is
    missing or unreadable (the pending state, not an error)."""
    path = Path(path) if path is not None else SCORECARD_JSON_PATH
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) \
            or not isinstance(document.get("metrics"), list):
        return None
    return document


def scorecard_payload(path=None):
    """The scorecard as data: metadata and metrics as separate
    objects, plus a `numbers` view (label/value pairs, metrics
    only) for simple consumers."""
    document = load_metrics_document(path)
    if document is None:
        return {"available": False, "status": "evaluation pending",
                "metadata": {}, "metrics": [], "numbers": []}
    metrics = [m for m in
               (_normalise_metric(raw)
                for raw in document["metrics"])
               if m is not None]
    metadata = {}
    raw_metadata = document.get("metadata")
    if isinstance(raw_metadata, dict):
        for key, value in raw_metadata.items():
            metadata[key] = _clean(value) \
                if isinstance(value, str) else value
    by_id = {m["id"]: m for m in metrics}
    headline = [by_id[mid] for mid in HEADLINE_METRIC_IDS
                if mid in by_id]
    where_it_fails = [_clean(item) for item in
                      document.get("where_it_fails", [])
                      if isinstance(item, str)]
    return {
        "available": bool(metrics),
        "status": _clean(document.get("status")) or "measured"
                  if metrics else "evaluation pending",
        "generated_on": _clean(document.get("generated_on", "")),
        "metadata": metadata,
        "metrics": metrics,
        "headline_metrics": headline,
        "numbers": [{"label": m["label"], "value": m["value"]}
                    for m in metrics],
        "where_it_fails": where_it_fails,
    }


def render_scorecard_html(payload):
    """The standalone /scorecard page, in the Marriage
    language (ink, sheet, Montserrat, Terracotta Deep as the
    one warm accent). Metadata is rendered as labelled
    metadata; the metrics table carries metrics only, each
    with its sample detail and caveat."""
    def esc(text):
        return html.escape(str(text if text is not None else ""),
                           quote=True)

    sections = []
    metadata = payload.get("metadata") or {}
    if metadata:
        rows = "".join(
            "<tr><th scope=\"row\">" + esc(label) + "</th>"
            "<td>" + esc(metadata[key]) + "</td></tr>\n"
            for key, label in _METADATA_LABELS if key in metadata)
        if rows:
            sections.append("<h2>About this evaluation</h2>\n"
                            "<table>\n" + rows + "</table>")
    if payload.get("metrics"):
        rows = ""
        for metric in payload["metrics"]:
            detail = metric.get("detail", "")
            caveat = metric.get("caveat", "")
            notes = " ".join(part for part in (detail, caveat)
                             if part)
            rows += ("<tr><th scope=\"row\">" + esc(metric["label"])
                     + "</th><td>" + esc(metric["value"]) + "</td>"
                     + "<td class=\"detail\">" + esc(notes)
                     + "</td></tr>\n")
        sections.append("<h2>Measured metrics</h2>\n<table>\n"
                        "<tr><th scope=\"col\">Metric</th>"
                        "<th scope=\"col\">Result</th>"
                        "<th scope=\"col\">Sample and caveats</th>"
                        "</tr>\n" + rows + "</table>")
        fails = payload.get("where_it_fails") or []
        if fails:
            items = "".join("<li>" + esc(item) + "</li>\n"
                            for item in fails)
            sections.append("<h2>Where it fails</h2>\n<ul>\n"
                            + items + "</ul>")
        sections.append(
            "<p class=\"note\">Measured numbers, read from "
            "SCORECARD.json when this page was served. "
            "SCORECARD.md is the human-readable companion; the "
            "figures above come from the structured data the "
            "eval harness emitted.</p>")
    else:
        sections.append(
            "<p class=\"pending\">Evaluation pending.</p>\n"
            "<p class=\"note\">No measured numbers have been "
            "published yet. When the eval harness emits "
            "SCORECARD.json, this page reads it directly — "
            "nothing here is hardcoded.</p>")
    body = "\n".join(sections)
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, "
        "initial-scale=1\">\n"
        "<title>Fireside — Scorecard</title>\n"
        "<link href=\"https://fonts.googleapis.com/css2?"
        "family=Montserrat:ital,wght@0,400;0,700;0,800;1,800"
        "&display=swap\" rel=\"stylesheet\">\n"
        "<style>"
        "body{margin:0;background:#3C3B3A;color:#3C3B3A;"
        "font-family:Montserrat,Arial,sans-serif}"
        "main{max-width:44rem;margin:2rem auto;background:#F1EDE6;"
        "padding:2.5rem 2rem 3rem;border-radius:3px}"
        "h1{font-size:2rem;margin:0 0 1rem}"
        "h2{font-size:1.35rem;margin:2rem 0 .6rem}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:.7rem .5rem;"
        "border-bottom:1px solid rgba(60,59,58,.25);font-size:1.05rem;"
        "vertical-align:top}"
        "td{font-weight:700;color:#93502F}"
        "td.detail{font-weight:400;color:#3C3B3A}"
        ".pending{font-size:1.4rem;font-weight:700}"
        ".note{color:#68635B}"
        "a{color:#3C3B3A}"
        "</style>\n</head>\n<body>\n<main>\n"
        "<h1>Fireside — Scorecard</h1>\n"
        + body +
        "\n<p><a href=\"/\">Back to Fireside</a></p>\n"
        "</main>\n</body>\n</html>"
    )
