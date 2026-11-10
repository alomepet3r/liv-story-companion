"""Scorecard surface + stakes-first landing.

The scorecard serves SCORECARD.json (repo root): structured
metrics emitted by the eval harness, with run metadata in a
separate object. No JSON (or no metrics in it) is the honest
"evaluation pending" state, and nothing is hardcoded. The
landing's three headline slots are selected by metric ID —
never by file order — so metadata can never fill a slot
(RT-01/RT-02 regression). The landing carries the stakes
headline, the checked answer, the named model stack, values
second, and a "Where it fails" line — with no fidelity claims
beyond the arrange + source-check + approve account.
"""
import json
import tempfile
import unittest
from pathlib import Path

from server import app, scorecard

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"

SAMPLE_DOCUMENT = {
    "schema_version": 1,
    "status": "measured",
    "generated_on": "2026-11-10",
    "metadata": {
        "date": "November 10, 2026",
        "harness": "eval/run_eval.py",
        "fixtures": "eval/fixtures/fidelity_cases.json",
        "live_model_calls": 0,
        "chapter_cost_time": "TO-RUN",
    },
    "metrics": [
        {"id": "source_check_flagged",
         "label": "Planted inventions flagged", "value": "7 of 9",
         "detail": "2 missed: red bicycle; three weeks"},
        {"id": "source_check_false_flags",
         "label": "False flags on the clean draft", "value": "0",
         "detail": "One small clean draft, 3 candidates checked",
         "caveat": "Not a general false-flag rate."},
        {"id": "count_corrections_adopted",
         "label": "Deliberate count corrections adopted",
         "value": "3 of 3"},
        {"id": "full_suite", "label": "Full behaviour suite",
         "value": "270 of 270 passed"},
    ],
    "where_it_fails": ["The check misses lowercase details."],
}


def _write_sample(directory):
    path = Path(directory) / "SCORECARD.json"
    path.write_text(json.dumps(SAMPLE_DOCUMENT), encoding="utf-8")
    return path


class TestScorecardJson(unittest.TestCase):
    def test_metrics_and_metadata_are_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = scorecard.scorecard_payload(
                _write_sample(tmp))
        self.assertTrue(payload["available"])
        self.assertEqual(payload["status"], "measured")
        self.assertEqual(payload["metadata"]["date"],
                         "November 10, 2026")
        labels = [m["label"] for m in payload["metrics"]]
        self.assertNotIn("Date", labels)
        self.assertNotIn("Harness", labels)
        self.assertEqual(payload["numbers"][0],
                         {"label": "Planted inventions flagged",
                          "value": "7 of 9"})

    def test_headline_metrics_are_the_measured_three(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = scorecard.scorecard_payload(
                _write_sample(tmp))
        headline = payload["headline_metrics"]
        self.assertEqual(
            [m["id"] for m in headline],
            ["source_check_flagged", "source_check_false_flags",
             "count_corrections_adopted"])
        self.assertEqual(headline[0]["value"], "7 of 9")
        self.assertIn("red bicycle", headline[0]["detail"])
        self.assertEqual(headline[1]["value"], "0")
        self.assertIn("caveat", headline[1])

    def test_missing_file_is_evaluation_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = scorecard.scorecard_payload(
                Path(tmp) / "SCORECARD.json")
        self.assertFalse(payload["available"])
        self.assertEqual(payload["status"], "evaluation pending")
        self.assertEqual(payload["metrics"], [])
        self.assertEqual(payload["numbers"], [])

    def test_markdown_is_never_a_metric_source(self):
        # A SCORECARD.md full of plausible numbers must not leak
        # into the payload: the JSON is the only source.
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "SCORECARD.md"
            md.write_text("| Planted inventions | 99 |\n",
                          encoding="utf-8")
            payload = scorecard.scorecard_payload(
                Path(tmp) / "SCORECARD.json")
        self.assertFalse(payload["available"])
        self.assertEqual(payload["metrics"], [])

    def test_endpoint_and_page_render_cleanly(self):
        status, payload = app.handle_scorecard()
        self.assertEqual(status, 200)
        self.assertIn("metrics", payload)
        self.assertIn("metadata", payload)
        page = scorecard.render_scorecard_html(payload)
        if payload["metrics"]:
            self.assertIn("Measured metrics", page)
            self.assertIn("About this evaluation", page)
            for metric in payload["metrics"]:
                self.assertIn(metric["value"], page)
            # No raw markdown artifacts anywhere on the page.
            self.assertNotIn("**", page)
            self.assertNotIn("`", page)
        else:
            self.assertIn("Evaluation pending", page)

    def test_page_labels_metadata_as_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            payload = scorecard.scorecard_payload(
                _write_sample(tmp))
        page = scorecard.render_scorecard_html(payload)
        about = page.split("About this evaluation", 1)[1] \
            .split("Measured metrics", 1)[0]
        self.assertIn("November 10, 2026", about)
        self.assertIn("eval/run_eval.py", about)
        metrics_part = page.split("Measured metrics", 1)[1]
        self.assertIn("Planted inventions flagged", metrics_part)


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

    def test_three_numbers_selected_by_metric_id(self):
        self.assertIn('id="scorecard-numbers"', self.html)
        self.assertIn('href="/scorecard"', self.html)
        self.assertIn("/api/scorecard", self.js)
        for metric_id in ("source_check_flagged",
                          "source_check_false_flags",
                          "count_corrections_adopted"):
            self.assertIn(metric_id, self.js)
        # Never again the first three parsed entries, whatever
        # order the file happens to be in.
        self.assertNotIn("numbers.slice(0, 3)", self.js)

    def test_named_model_stack(self):
        for marker in ("Muse Spark 1.3", "Muse Voice Transcribe 1.0",
                       "SAM 3.1", "Muse Image 1.0",
                       "There is no companion",
                       "Tellers who can't type can't tell",
                       "guess at photographs",
                       "The keepsake is text only"):
            self.assertIn(marker, self.html)

    def test_privacy_copy_describes_the_real_data_path(self):
        # RT-03 regression: no surface may claim or imply that
        # nothing leaves unless approved. Approval gates
        # publication; the model-service sending is named.
        self.assertNotIn("no one else. Nothing leaves", self.html)
        self.assertNotIn("Nothing leaves", self.html)
        self.assertIn("Who can see it, and where it goes:",
                      self.html)
        self.assertIn("Meta's model services", self.html)
        self.assertIn("does not publish a\n        chapter", self.html)
        self.assertIn("Closing or refreshing the tab does "
                      "<em>not</em> delete", self.html)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("What Liv sends, and what approval gates",
                      readme)
        self.assertIn("Approval does not gate that processing.",
                      readme)
        self.assertIn("Closing or refreshing the tab does not "
                      "delete a sitting.", readme)

    def test_values_second_and_where_it_fails(self):
        self.assertIn('class="landing-values"', self.html)
        self.assertIn("Where it fails", self.html)
        self.assertIn("sessions live in the server's memory",
                      self.html)
        self.assertIn("a refresh strands", self.html)
        values = self.html.index('class="landing-values"')
        models = self.html.index('id="landing-models-heading"')
        self.assertLess(models, values)


if __name__ == "__main__":
    unittest.main()
