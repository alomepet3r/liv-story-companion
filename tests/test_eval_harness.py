"""Tests for the eval harness (eval/run_eval.py).

Synthetic fixtures only; the source-check assertions run the real
shipped `server.chapter.source_check` through the harness's own
accounting. Run: python3 -m unittest discover -s tests
"""
import unittest

from eval.run_eval import (evaluate_count_correction,
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


if __name__ == "__main__":
    unittest.main()
