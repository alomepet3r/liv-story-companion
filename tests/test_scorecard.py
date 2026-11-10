"""Scorecard surface + stakes-first landing.

The scorecard reads SCORECARD.md dynamically (repo root): no
file (or no numbers in it) is the honest "evaluation pending"
state, and nothing is hardcoded. The landing carries the
stakes headline, the checked answer, three TO-RUN-or-measured
numbers, the named model stack, values second, and a
"Where it fails" line — with no fidelity claims beyond the
arrange + source-check + approve account.
"""
import tempfile
import unittest
from pathlib import Path

from server import app, scorecard

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

SAMPLE = """# Scorecard

| Metric | Result |
| --- | --- |
| Source-check flags caught | 12 of 12 |
| Chapters approved in testing | 9 |

- **Median sitting length:** 14 minutes
- Sessions completed: 31
A line with no numbers at all.
"""


class TestScorecardParsing(unittest.TestCase):
    def test_parses_tables_and_label_lines(self):
        numbers = scorecard.parse_scorecard_text(SAMPLE)
        pairs = {(n["label"], n["value"]) for n in numbers}
        self.assertIn(("Source-check flags caught", "12 of 12"),
                      pairs)
        self.assertIn(("Chapters approved in testing", "9"), pairs)
        self.assertIn(("Median sitting length", "14 minutes"),
                      pairs)
        self.assertIn(("Sessions completed", "31"), pairs)

    def test_header_rows_and_numberless_lines_are_skipped(self):
        numbers = scorecard.parse_scorecard_text(SAMPLE)
        labels = [n["label"].lower() for n in numbers]
        self.assertNotIn("metric", labels)
        for n in numbers:
            self.assertTrue(any(c.isdigit() for c in n["value"]))

    def test_missing_file_is_evaluation_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = scorecard.scorecard_payload(
                Path(tmp) / "SCORECARD.md")
        self.assertFalse(payload["available"])
        self.assertEqual(payload["status"], "evaluation pending")
        self.assertEqual(payload["numbers"], [])

    def test_file_landing_makes_numbers_appear(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SCORECARD.md"
            path.write_text(SAMPLE, encoding="utf-8")
            payload = scorecard.scorecard_payload(path)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["status"], "measured")
        self.assertGreaterEqual(len(payload["numbers"]), 3)

    def test_endpoint_and_page_use_the_payload(self):
        status, payload = app.handle_scorecard()
        self.assertEqual(status, 200)
        self.assertIn("numbers", payload)
        page = scorecard.render_scorecard_html(payload)
        if payload["numbers"]:
            for n in payload["numbers"]:
                self.assertIn(n["value"], page)
        else:
            self.assertIn("Evaluation pending", page)


class TestLandingCopy(unittest.TestCase):
    def setUp(self):
        self.html = (WEB / "index.html").read_text(encoding="utf-8")
        self.js = (WEB / "app.js").read_text(encoding="utf-8")

    def test_stakes_headline_first(self):
        self.assertIn(
            "Every family is one funeral away from losing its "
            "stories", self.html)
        headline = self.html.index("Every family is one funeral")
        self.assertLess(headline, self.html.index("landing-values"))

    def test_checked_answer_without_fidelity_claims(self):
        landing = self.html.split('id="landing-models-heading"')[0]
        self.assertIn("arrange", landing)
        self.assertIn("source-check flags", landing)
        self.assertIn("reviews and approves", landing)
        lowered = landing.lower()
        self.assertNotIn("verbatim", lowered)
        self.assertNotIn("word-for-word", lowered)
        self.assertNotIn("word for word", lowered)
        self.assertNotIn("exactly as told", lowered)

    def test_three_numbers_wired_to_scorecard(self):
        self.assertIn('id="scorecard-numbers"', self.html)
        self.assertIn("TO-RUN", self.html)
        self.assertIn('href="/scorecard"', self.html)
        self.assertIn("/api/scorecard", self.js)

    def test_named_model_stack(self):
        for marker in ("Muse Spark 1.3", "Muse Voice Transcribe 1.0",
                       "SAM 3.1", "Muse Image 1.0",
                       "There is no companion",
                       "Tellers who can't type can't tell",
                       "guess at photographs",
                       "The keepsake is text only"):
            self.assertIn(marker, self.html)

    def test_values_second_and_where_it_fails(self):
        self.assertIn('class="landing-values"', self.html)
        self.assertIn("Where it fails", self.html)
        self.assertIn("sessions live in memory", self.html)
        self.assertIn("a refresh ends a sitting", self.html)
        values = self.html.index('class="landing-values"')
        models = self.html.index('id="landing-models-heading"')
        self.assertLess(models, values)


if __name__ == "__main__":
    unittest.main()
