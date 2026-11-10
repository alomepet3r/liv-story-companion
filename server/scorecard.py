"""Public scorecard surface — renders SCORECARD.md's numbers.

The evaluation's headline numbers live in SCORECARD.md at the
repo root. This module reads that file AT REQUEST TIME: when
the file lands, its numbers appear on the landing and on
/scorecard with no code change and nothing hardcoded here.
Until the file exists, the honest fallback state is served —
"evaluation pending" — never invented figures.

Parsing is deliberately simple: headline numbers are taken
from markdown table rows (`| label | value |`), from bold
label lines (`- **Label:** value`), and from `Label: value`
lines, in file order, keeping only values that contain a
digit. Everything else in the file is ignored.
"""
import html
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCORECARD_PATH = REPO_ROOT / "SCORECARD.md"

_TABLE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
_BOLD_LABEL = re.compile(
    r"^\s*[-*]\s*\*\*(.+?)\*\*\s*[:—-]?\s*(.+?)\s*$")
_PLAIN_LABEL = re.compile(r"^\s*[-*]?\s*([^:#|]{3,60}?)\s*:\s*(.+?)\s*$")
_SKIP_LABELS = {"metric", "measure", "number", "result", "label",
                "value", "scorecard"}


def parse_scorecard_text(text):
    """Headline numbers from scorecard markdown: a list of
    {"label": str, "value": str} in file order."""
    numbers = []
    seen = set()
    for line in (text or "").splitlines():
        label = value = None
        m = _TABLE_ROW.match(line)
        if m and not set(line.replace("|", "").strip()) <= {"-", ":", " "}:
            label, value = m.group(1).strip(), m.group(2).strip()
        else:
            m = _BOLD_LABEL.match(line)
            if m:
                label, value = m.group(1).strip(), m.group(2).strip()
            else:
                m = _PLAIN_LABEL.match(line)
                if m:
                    label, value = m.group(1).strip(), m.group(2).strip()
        if not label or not value:
            continue
        label = label.strip().rstrip(":").strip()
        if label.lower() in _SKIP_LABELS:
            continue
        if not any(ch.isdigit() for ch in value):
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        numbers.append({"label": label, "value": value})
    return numbers


def scorecard_payload(path=None):
    """The scorecard as data. Reads the file dynamically on
    every call; a missing file is the pending state, not an
    error."""
    path = Path(path) if path is not None else SCORECARD_PATH
    if not path.is_file():
        return {"available": False, "status": "evaluation pending",
                "numbers": []}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {"available": False, "status": "evaluation pending",
                "numbers": []}
    numbers = parse_scorecard_text(text)
    return {"available": bool(numbers),
            "status": "measured" if numbers else "evaluation pending",
            "numbers": numbers}


def render_scorecard_html(payload):
    """The standalone /scorecard page, in the Marriage
    language (ink, sheet, Montserrat, Terracotta Deep as the
    one warm accent). Numbers come only from the payload."""
    def esc(text):
        return html.escape(str(text or ""), quote=True)

    if payload.get("numbers"):
        rows = "".join(
            "<tr><th scope=\"row\">" + esc(n["label"]) + "</th>"
            "<td>" + esc(n["value"]) + "</td></tr>\n"
            for n in payload["numbers"])
        body = ("<table>\n" + rows + "</table>\n"
                "<p class=\"note\">Measured numbers, read from "
                "SCORECARD.md when this page was served.</p>")
    else:
        body = ("<p class=\"pending\">Evaluation pending.</p>\n"
                "<p class=\"note\">No measured numbers have been "
                "published yet. When SCORECARD.md lands, this "
                "page reads it directly — nothing here is "
                "hardcoded.</p>")
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
        "table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:.7rem .5rem;"
        "border-bottom:1px solid rgba(60,59,58,.25);font-size:1.1rem}"
        "td{font-weight:700;color:#93502F}"
        ".pending{font-size:1.4rem;font-weight:700}"
        ".note{color:#68635B}"
        "a{color:#3C3B3A}"
        "</style>\n</head>\n<body>\n<main>\n"
        "<h1>Fireside — Scorecard</h1>\n"
        + body +
        "\n<p><a href=\"/\">Back to Fireside</a></p>\n"
        "</main>\n</body>\n</html>"
    )
