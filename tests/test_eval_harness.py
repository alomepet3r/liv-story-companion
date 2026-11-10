"""Tests for the eval harness (eval/run_eval.py).

Synthetic fixtures only; the source-check assertions run the real
shipped `server.chapter.source_check` through the harness's own
accounting. Run: python3 -m unittest discover -s tests
"""
import unittest

from eval.run_eval import (build_metrics_document,
                           evaluate_count_correction,
                           evaluate_source_check, load_fixtures,
                           make_draft, make_sources, planted_outcome)
from server import chapter


class TestEvalFixtures(unittest.TestCase):
    def test_fixtures_load(self):
        fixture = load_fixtures()
        self.assertTrue(fixture["source_texts"])
        self.assertTrue(fixture["clean_draft_paragraphs"])
        self.assertTrue(fixture["planted_draft_paragraphs"])
        self.assertTrue(fixture["planted_items"])
        # Every planted item is genuinely absent from the source
        # telling (otherwise it would not be an invention).
        corpus = " ".join(fixture["source_texts"]).lower()
        for item in fixture["planted_items"]:
            self.assertNotIn(item["text"].lower(), corpus, item)

    def test_sources_and_draft_shapes(self):
        fixture = load_fixtures()
        sources = make_sources(fixture)
        self.assertEqual([s["id"] for s in sources],
                         ["s1", "s2"][:len(sources)])
        draft = make_draft(fixture["clean_draft_paragraphs"])
        self.assertEqual(draft["sections"][0]["paragraphs"][0]
                         ["source_ids"], ["s1"])


class TestPlantedAccounting(unittest.TestCase):
    def test_accounting_on_a_tiny_case(self):
        planted = [{"text": "Zanzibar", "kind": "name or place"},
                   {"text": "red bicycle", "kind": "detail"}]
        flags = [{"text": "Zanzibar", "kind": "name or place"}]
        flagged, missed = planted_outcome(planted, flags)
        self.assertEqual([i["text"] for i in flagged], ["Zanzibar"])
        self.assertEqual([i["text"] for i in missed],
                         ["red bicycle"])

    def test_accounting_matches_inside_a_flagged_phrase(self):
        planted = [{"text": "Tomas", "kind": "name or place"}]
        flags = [{"text": "Uncle Tomas", "kind": "name or place"}]
        flagged, missed = planted_outcome(planted, flags)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(missed, [])

    def test_full_fixture_run_is_consistent(self):
        result = evaluate_source_check(load_fixtures())
        self.assertEqual(result["planted_total"],
                         result["planted_flagged"]
                         + result["planted_missed"])
        self.assertGreaterEqual(result["planted_flagged"], 1)
        # Direct check of the shipped function agrees with the
        # harness on the clean draft's false-flag count.
        fixture = load_fixtures()
        direct = chapter.source_check(
            make_draft(fixture["clean_draft_paragraphs"]),
            make_sources(fixture))
        self.assertEqual(result["clean_false_flags"],
                         len(direct["flags"]))

    def test_count_correction_exercise_adopts_and_holds(self):
        result = evaluate_count_correction()
        self.assertEqual(result["adopted"], result["deliberate_total"])
        self.assertEqual(result["controls_held"],
                         result["controls_total"])


class TestMetricsDocument(unittest.TestCase):
    """The harness's structured output (SCORECARD.json): metrics
    are data, metadata is separate, and the first three metrics
    are the landing's measured headlines (RT-01/RT-02)."""

    def _document(self):
        summary = {
            "source_check": evaluate_source_check(load_fixtures()),
            "count_correction": evaluate_count_correction(),
            "count_correction_tests": {
                "ran": 9, "passed": 9, "failures": 0, "errors": 0,
                "skipped": 0, "ok": True},
            "full_suite": {
                "ran": 270, "passed": 270, "failures": 0,
                "errors": 0, "skipped": 0, "ok": True},
            "chapter_cost_time": "TO-RUN",
        }
        return build_metrics_document(summary)

    def test_headlines_are_the_measured_metrics(self):
        document = self._document()
        first_three = document["metrics"][:3]
        self.assertEqual(
            [m["id"] for m in first_three],
            ["source_check_flagged", "source_check_false_flags",
             "count_corrections_adopted"])
        self.assertEqual(first_three[0]["value"], "7 of 9")
        self.assertEqual(first_three[0]["missed_items"],
                         ["red bicycle", "three weeks"])
        self.assertEqual(first_three[1]["value"], "0")
        self.assertIn("caveat", first_three[1])
        self.assertEqual(first_three[2]["value"], "3 of 3")

    def test_metadata_is_not_a_metric(self):
        document = self._document()
        self.assertIn("date", document["metadata"])
        self.assertIn("harness", document["metadata"])
        ids = [m["id"] for m in document["metrics"]]
        self.assertNotIn("date", ids)
        self.assertNotIn("harness", ids)
        for metric in document["metrics"]:
            self.assertNotIn("**", metric["label"])
            self.assertNotIn("`", metric["value"])


if __name__ == "__main__":
    unittest.main()
