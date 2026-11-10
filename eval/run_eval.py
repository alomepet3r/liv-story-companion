"""Fidelity evaluation harness for the Fireside/Liv build.

Repeatable, SYNTHETIC fixtures only, ZERO live model calls
(canned/deterministic paths only). It measures, using the real
shipped code — never a reimplementation:

(a) Source-check integrity — `server.chapter.source_check`
    (the deterministic check that flags names, dates and places
    in a draft chapter that do NOT appear in the storyteller's
    own words). Planted inventions in a synthetic draft are
    counted as flagged / missed; a clean synthetic draft is run
    for false flags.
(b) Count-correction adoption — `server.app._note_count_correction`
    (the storyteller's deliberate count correction is persisted
    as `owner_count` beside, never overwriting, the measured
    count), plus the shipped `TestCountCorrection` test class run
    as a subprocess.
(c) Behaviour suite — the FULL existing test suite, run as a
    subprocess (`python -m unittest discover -s tests -t .`).
(d) Chapter cost/time — NOT measured here: the harness makes no
    live model calls and the repo holds no cost/time artifacts,
    so the scorecard marks it TO-RUN rather than inventing a
    number.

Run from the repo root, either way:
    python3 -m eval.run_eval
    python3 eval/run_eval.py
Prints a summary; exits 0 only if the suite subprocess passes.
"""
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

FIXTURE_PATH = os.path.join(_HERE, "fixtures", "fidelity_cases.json")


# ------------------------------------------------------------------
# Fixtures + draft/source shapes (exactly what server.chapter uses)
# ------------------------------------------------------------------

def load_fixtures(path=FIXTURE_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def make_sources(fixture):
    return [{"id": "s%d" % (i + 1), "kind": "words",
             "label": "A telling you gave Liv", "media_id": None,
             "text": text}
            for i, text in enumerate(fixture["source_texts"])]


def make_draft(paragraphs):
    return {"title": "A synthetic chapter", "dedication": "",
            "mode": "canned",
            "sections": [{"heading": "Your words", "media_ids": [],
                          "paragraphs": [
                              {"text": p, "source_ids": ["s1"]}
                              for p in paragraphs]}]}


# ------------------------------------------------------------------
# (a) Source-check integrity, via the shipped source_check
# ------------------------------------------------------------------

def planted_outcome(planted_items, flags):
    """Accounting: a planted item is 'flagged' when some flag's
    text equals it, or one contains the other (case-insensitive)
    — so a planted 'Tomas' surfaced inside a flagged phrase
    'Uncle Tomas' still counts, and a planted full phrase
    surfaced in part counts too. Returns (flagged, missed)."""
    flag_texts = [f["text"].lower() for f in flags]
    flagged, missed = [], []
    for item in planted_items:
        needle = item["text"].lower()
        hit = any(needle == ft or needle in ft or ft in needle
                  for ft in flag_texts)
        (flagged if hit else missed).append(item)
    return flagged, missed


def evaluate_source_check(fixture):
    from server import chapter  # the real shipped code path
    sources = make_sources(fixture)
    planted_result = chapter.source_check(
        make_draft(fixture["planted_draft_paragraphs"]), sources)
    flagged, missed = planted_outcome(
        fixture["planted_items"], planted_result["flags"])
    clean_result = chapter.source_check(
        make_draft(fixture["clean_draft_paragraphs"]), sources)
    return {
        "planted_total": len(fixture["planted_items"]),
        "planted_flagged": len(flagged),
        "planted_missed": len(missed),
        "missed_items": [i["text"] for i in missed],
        "flagged_items": [i["text"] for i in flagged],
        "all_flag_texts": [f["text"] for f in planted_result["flags"]],
        "planted_checked": planted_result["checked"],
        "clean_checked": clean_result["checked"],
        "clean_false_flags": len(clean_result["flags"]),
        "clean_flag_texts": [f["text"] for f in clean_result["flags"]],
    }


# ------------------------------------------------------------------
# (b) Count-correction adoption, via the shipped note-taker
# ------------------------------------------------------------------

def _fresh_session(measured):
    return {"media": {"m1": {"kind": "photo",
                             "scene_facts": {"person_count": measured}}}}


def evaluate_count_correction():
    from server import app  # real shipped _note_count_correction
    deliberate = [
        (8, "There are nine of us in that photo.", 9),
        (8, "No \u2014 there are 10 of us, not 8.", 10),
        (8, "Yes \u2014 eleven is a correction.", 11),
    ]
    controls = [
        (9, "One of us still tells that story every Christmas."),
        (8, "That photo was taken at our house."),
    ]
    adopted = 0
    for measured, words, expected in deliberate:
        sess = _fresh_session(measured)
        noted = app._note_count_correction(sess, words)
        facts = sess["media"]["m1"]["scene_facts"]
        if noted and facts.get("owner_count") == expected \
                and facts["person_count"] == measured:
            adopted += 1
    held = 0
    for measured, words in controls:
        sess = _fresh_session(measured)
        noted = app._note_count_correction(sess, words)
        facts = sess["media"]["m1"]["scene_facts"]
        if not noted and "owner_count" not in facts:
            held += 1
    return {"deliberate_total": len(deliberate), "adopted": adopted,
            "controls_total": len(controls), "controls_held": held}


# ------------------------------------------------------------------
# (c) Test suites, as subprocesses (the way a developer runs them)
# ------------------------------------------------------------------

def run_unittest(args):
    proc = subprocess.run(
        [sys.executable, "-m", "unittest"] + args,
        cwd=_REPO, capture_output=True, text=True)
    out = proc.stdout + proc.stderr
    m = re.search(r"Ran (\d+) tests", out)
    ran = int(m.group(1)) if m else 0
    failures = errors = skipped = 0
    m = re.search(r"\(([^)]*)\)\s*$", out.strip().splitlines()[-1]
                  if out.strip() else "")
    if m:
        for key, var in (("failures=", "f"), ("errors=", "e"),
                         ("skipped=", "s")):
            mm = re.search(key + r"(\d+)", m.group(1))
            if mm:
                if var == "f":
                    failures = int(mm.group(1))
                elif var == "e":
                    errors = int(mm.group(1))
                else:
                    skipped = int(mm.group(1))
    ok = proc.returncode == 0 and "\nOK" in out
    return {"ran": ran, "failures": failures, "errors": errors,
            "skipped": skipped,
            "passed": ran - failures - errors - skipped,
            "ok": ok}


def main():
    fixture = load_fixtures()
    print("=== Fireside/Liv fidelity eval (synthetic, canned only, "
          "no live model calls) ===")
    a = evaluate_source_check(fixture)
    print("\n(a) Source-check integrity "
          "(server.chapter.source_check)")
    print("    planted inventions total : %d" % a["planted_total"])
    print("    flagged                  : %d" % a["planted_flagged"])
    print("    missed                   : %d  %s"
          % (a["planted_missed"], a["missed_items"]))
    print("    candidates checked       : %d (planted draft), "
          "%d (clean draft)"
          % (a["planted_checked"], a["clean_checked"]))
    print("    clean-draft false flags  : %d  %s"
          % (a["clean_false_flags"], a["clean_flag_texts"]))
    b = evaluate_count_correction()
    print("\n(b) Count-correction adoption "
          "(server.app._note_count_correction)")
    print("    deliberate corrections adopted : %d/%d"
          % (b["adopted"], b["deliberate_total"]))
    print("    non-correction controls held   : %d/%d"
          % (b["controls_held"], b["controls_total"]))
    cc = run_unittest(["tests.test_sam.TestCountCorrection"])
    print("    shipped TestCountCorrection    : ran %d, passed %d, "
          "failures %d, errors %d"
          % (cc["ran"], cc["passed"], cc["failures"], cc["errors"]))
    print("\n(c) Full behaviour suite "
          "(python -m unittest discover -s tests -t .)")
    full = run_unittest(["discover", "-s", "tests", "-t", "."])
    print("    ran %d, passed %d, failures %d, errors %d, skipped %d "
          "-> %s"
          % (full["ran"], full["passed"], full["failures"],
             full["errors"], full["skipped"],
             "OK" if full["ok"] else "FAILED"))
    print("\n(d) Chapter cost/time: TO-RUN — no live model calls in "
          "this harness and no cost/time artifacts in the repo; "
          "no number is claimed.")
    summary = {"source_check": a, "count_correction": b,
               "count_correction_tests": cc, "full_suite": full,
               "chapter_cost_time": "TO-RUN"}
    print("\n--- machine-readable summary ---")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if full["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
