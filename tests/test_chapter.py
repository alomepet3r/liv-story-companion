"""Tests for the chapter slice (server.app handlers + server.chapter).

Flow under test: outline (plan) -> re-plan -> draft -> source-check
-> approve -> keepsake share link. All content is synthetic.
The live drafter is exercised through a fake client; the canned
path runs with no API key. Run: python3 -m unittest discover -s tests
"""
import unittest

from server import app, chapter
from tests.test_archive import PNG

STORY_TURNS = [
    "Call me Margaret.",
    "My father took me to Bamenda in 1984, to ride the first "
    "elevator the town had ever seen.",
    "I was seven years old, and the doors closed and the room "
    "moved, and I held his hand the whole way up.",
    "He told me that day: never be afraid of new things, "
    "Margaret. Little by little, drop by drop.",
]


class FakeClient:
    """Stands in for MetaClient on the live drafting path."""

    def __init__(self, text):
        self.text = text
        self.calls = []

    def chat(self, messages, model=None, **kwargs):
        self.calls.append(messages)
        return self.text, {"fake": True}


class ChapterCase(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        chapter._shares.clear()
        self._saved_key = app.MODEL_API_KEY
        self._saved_client = app._live_client
        app.MODEL_API_KEY = ""       # canned path unless faked
        app._live_client = None
        self.session = "chapter-test"
        self.payload = {"session_id": self.session, "consent": True,
                        "age_confirmed": True}

    def tearDown(self):
        app.MODEL_API_KEY = self._saved_key
        app._live_client = self._saved_client
        app._sessions.clear()
        chapter._shares.clear()

    def tell_story(self):
        for turn in STORY_TURNS:
            status, body = app.handle_chat(
                dict(self.payload, message=turn))
            self.assertEqual(status, 200, body)

    def add_photo(self):
        fields = {"session_id": self.session, "consent": "true",
                  "age_confirmed": "true", "kind": "photo"}
        files = {"file": ("hill.png", "image/png", PNG)}
        status, body = app.handle_media_upload(fields, files)
        self.assertEqual(status, 200, body)
        return body["media_id"]

    def outline(self):
        status, view = app.handle_chapter_outline(self.payload)
        self.assertEqual(status, 200, view)
        return view


class TestGates(ChapterCase):
    def test_chapter_routes_require_consent(self):
        for handler in (app.handle_chapter_outline,
                        app.handle_chapter_replan,
                        app.handle_chapter_draft,
                        app.handle_chapter_approve,
                        app.handle_chapter_view):
            status, _ = handler(dict(self.payload, consent=False))
            self.assertEqual(status, 403, handler.__name__)

    def test_chapter_routes_require_age_confirmation(self):
        for handler in (app.handle_chapter_outline,
                        app.handle_chapter_draft,
                        app.handle_chapter_approve):
            status, _ = handler(dict(self.payload,
                                     age_confirmed=False))
            self.assertEqual(status, 403, handler.__name__)

    def test_no_chapter_before_any_story(self):
        status, body = app.handle_chapter_outline(self.payload)
        self.assertEqual(status, 400)
        self.assertIn("story", body["error"])

    def test_view_before_chapter_is_empty_not_an_error(self):
        status, view = app.handle_chapter_view(self.payload)
        self.assertEqual(status, 200)
        self.assertIsNone(view["chapter"])
        self.assertTrue(all(not item["done"]
                            for item in view["checklist"]))


class TestOutlineAndReplan(ChapterCase):
    def test_outline_records_real_steps_and_checklist(self):
        self.tell_story()
        self.add_photo()
        view = self.outline()
        ch = view["chapter"]
        self.assertEqual(ch["stage"], "outline")
        step_ids = [s["id"] for s in view["steps"]]
        self.assertEqual(step_ids, ["gather", "plan"])
        done = {i["id"]: i["done"] for i in view["checklist"]}
        self.assertTrue(done["materials"])
        self.assertTrue(done["outline"])
        self.assertFalse(done["outline_ok"])
        self.assertFalse(done["draft"])
        self.assertFalse(done["approved"])
        kinds = {m["kind"] for m in ch["materials_all"]}
        self.assertIn("words", kinds)
        self.assertIn("photo", kinds)
        self.assertIsNone(view["share_url"])

    def test_replan_excludes_material_and_keeps_dedication(self):
        self.tell_story()
        self.add_photo()
        view = self.outline()
        photo = [m for m in view["chapter"]["materials_all"]
                 if m["kind"] == "photo"][0]
        status, view = app.handle_chapter_replan(dict(
            self.payload, title="The Elevator",
            dedication="my children",
            exclude_source_ids=[photo["id"]]))
        self.assertEqual(status, 200, view)
        ch = view["chapter"]
        self.assertEqual(ch["outline"]["title"], "The Elevator")
        self.assertEqual(ch["outline"]["dedication"], "my children")
        self.assertIn(photo["id"], ch["excluded"])
        kept = [m for m in ch["materials_all"] if m["included"]]
        self.assertTrue(all(m["kind"] != "photo" for m in kept))
        step_ids = [s["id"] for s in view["steps"]]
        self.assertEqual(step_ids, ["gather", "plan", "replan"])
        # …and the excluded photo stays out of the draft too.
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        draft = view["chapter"]["draft"]
        self.assertEqual(draft["dedication"], "my children")
        for section in draft["sections"]:
            self.assertEqual(section["media_ids"], [])

    def test_replan_after_draft_is_refused(self):
        self.tell_story()
        self.outline()
        status, _ = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200)
        status, _ = app.handle_chapter_replan(
            dict(self.payload, dedication="too late"))
        self.assertEqual(status, 400)


class TestDraftCheckApprove(ChapterCase):
    def test_canned_flow_end_to_end(self):
        self.tell_story()
        self.add_photo()
        self.outline()
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        ch = view["chapter"]
        self.assertEqual(ch["stage"], "review")
        self.assertEqual(ch["draft"]["mode"], "canned")
        done = {i["id"]: i["done"] for i in view["checklist"]}
        self.assertTrue(done["outline_ok"])
        self.assertTrue(done["draft"])
        self.assertTrue(done["check"])
        self.assertFalse(done["approved"])
        # Unverified until approved: no share link exists yet.
        self.assertIsNone(view["share_url"])
        # The canned draft is arranged from the sources, so the
        # source-check finds nothing foreign.
        self.assertEqual(ch["check"]["flags"], [])
        self.assertGreaterEqual(ch["check"]["checked"], 2)
        # Evidence: every paragraph names its source.
        self.assertTrue(view["evidence"])
        for ev in view["evidence"]:
            self.assertTrue(ev["sources"], ev)
        # Approval mints the one share link.
        status, view = app.handle_chapter_approve(self.payload)
        self.assertEqual(status, 200, view)
        self.assertTrue(view["share_url"].startswith("/keepsake/"))
        token = view["share_url"].split("/")[-1]
        snapshot = chapter.get_share(token)
        self.assertIsNotNone(snapshot)
        html = chapter.render_keepsake_html(snapshot)
        self.assertIn("Bamenda", html)
        self.assertIn("approved by the storyteller", html)

    def test_no_approval_before_draft(self):
        self.tell_story()
        self.outline()
        status, _ = app.handle_chapter_approve(self.payload)
        self.assertEqual(status, 400)
        self.assertEqual(chapter._shares, {})

    def test_unknown_share_token_is_nothing(self):
        self.assertIsNone(chapter.get_share("no-such-token"))

    def test_keepsake_escapes_storyteller_text(self):
        snapshot = {"title": "T <b>x</b>", "dedication": "my <kids>",
                    "sections": [], "session_id": "s"}
        html = chapter.render_keepsake_html(snapshot)
        self.assertIn("&lt;b&gt;", html)
        self.assertNotIn("<b>x</b>", html)


class TestSourceCheck(unittest.TestCase):
    def setUp(self):
        self.sources = [{
            "id": "s1", "kind": "words", "label": "Something you "
            "told Liv", "media_id": None,
            "text": "My father took me to Bamenda in 1984, to ride "
                    "the first elevator in town.",
        }]

    def test_invented_name_and_date_are_flagged(self):
        draft = {"title": "T", "dedication": "", "mode": "canned",
                 "sections": [{"heading": "H", "media_ids": [],
                               "paragraphs": [{
                                   "text": "My father took me to "
                                           "Bamenda in 1984, and "
                                           "years later we sailed to "
                                           "Zanzibar in 1977.",
                                   "source_ids": ["s1"]}]}]}
        result = chapter.source_check(draft, self.sources)
        flagged = {f["text"] for f in result["flags"]}
        self.assertIn("Zanzibar", flagged)
        self.assertIn("1977", flagged)
        self.assertNotIn("Bamenda", flagged)
        self.assertNotIn("1984", flagged)

    def test_grounded_draft_has_no_flags(self):
        draft = {"title": "T", "dedication": "", "mode": "canned",
                 "sections": [{"heading": "H", "media_ids": [],
                               "paragraphs": [{
                                   "text": self.sources[0]["text"],
                                   "source_ids": ["s1"]}]}]}
        result = chapter.source_check(draft, self.sources)
        self.assertEqual(result["flags"], [])
        self.assertGreaterEqual(result["checked"], 2)


class TestLiveDrafting(ChapterCase):
    def test_arrangement_prompt_is_grounded_and_labelled(self):
        self.tell_story()
        sess = app._session(self.session)
        sources = chapter.gather_sources(sess)
        outline = chapter.build_outline(sources)
        messages = chapter.build_arrangement_messages(
            sources, outline, "Liv")
        joined = "\n".join(m["content"] for m in messages)
        self.assertIn("ONLY", joined)
        self.assertIn("Invent nothing", joined)
        self.assertIn("leave it out", joined.lower())
        self.assertIn("[S1]", joined)
        self.assertIn("Bamenda", joined)

    def test_parse_live_draft_maps_sources(self):
        sess = {"history": [
            {"role": "user", "content": "First part of the tale."},
            {"role": "user", "content": "Second part of the tale."},
        ], "media": {}, "chapter": None}
        sources = chapter.gather_sources(sess)
        outline = chapter.build_outline(sources)
        text = ("SECTION: The beginning\n"
                "First part of the tale, arranged. [S1]\n"
                "SECTION: Where it rests\n"
                "Second part of the tale, arranged. [S2]\n")
        draft = chapter.parse_live_draft(text, sources, outline)
        self.assertIsNotNone(draft)
        self.assertEqual(draft["mode"], "live")
        self.assertEqual(draft["sections"][0]["paragraphs"][0]
                         ["source_ids"], ["s1"])
        self.assertEqual(draft["sections"][1]["paragraphs"][0]
                         ["source_ids"], ["s2"])
        self.assertIsNone(chapter.parse_live_draft(
            "no shape here at all", sources, outline))

    def test_live_drafter_used_when_client_present(self):
        self.tell_story()
        fake = FakeClient(
            "SECTION: The beginning\n"
            "My father took me to Bamenda in 1984. [S2]\n"
            "SECTION: The heart of it\n"
            "I was seven years old and held his hand. [S3]\n"
            "SECTION: Where it rests\n"
            "He told me: never be afraid of new things. [S4]\n")
        app._live_client = fake
        self.outline()
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        self.assertEqual(view["chapter"]["draft"]["mode"], "live")
        self.assertEqual(len(fake.calls), 1)
        # The live draft also passes through the source-check.
        self.assertIsNotNone(view["chapter"]["check"])

    def test_live_failure_falls_back_to_canned(self):
        self.tell_story()
        app._live_client = FakeClient("")   # empty -> no draft
        self.outline()
        status, view = app.handle_chapter_draft(self.payload)
        self.assertEqual(status, 200, view)
        self.assertEqual(view["chapter"]["draft"]["mode"], "canned")


class TestWartFixes(unittest.TestCase):
    """Day 4 wart fixes: recognisable material labels, clean
    suggested titles, and housekeeping turns kept out of the
    chapter's sources. Synthetic sessions only."""

    def sources(self, turns, media=None):
        sess = {"history": [{"role": "user", "content": t}
                            for t in turns],
                "media": media or {}, "chapter": None}
        return chapter.gather_sources(sess)

    # --- Wart 3: housekeeping turns are not story material ---

    def test_name_answers_are_not_sources(self):
        for answer in ("Call me Petro.", "Petro.", "My name is Ana.",
                       "I'm Margaret.", "Just call me Tita.",
                       "No name, thanks.", "I'd rather not say."):
            srcs = self.sources(
                [answer, "My father took me to Bamenda in 1984."])
            self.assertEqual(len(srcs), 1, answer)
            self.assertIn("Bamenda", srcs[0]["text"])

    def test_name_declaration_before_a_telling_keeps_the_telling(self):
        srcs = self.sources(
            ["Call me Petro. My dad had just passed that spring."])
        self.assertEqual(len(srcs), 1)
        self.assertTrue(srcs[0]["text"].startswith("My dad"))
        self.assertNotIn("Call me", srcs[0]["text"])

    def test_greeting_before_a_telling_keeps_the_telling(self):
        srcs = self.sources(
            ["Hello. Yesterday in Douala the rain came early."])
        self.assertEqual(len(srcs), 1)
        self.assertTrue(srcs[0]["text"].startswith("Yesterday"))

    def test_short_substantive_tellings_survive(self):
        for telling in ("It did not stay with me.",
                        "I'm from Bamenda.",
                        "Boxing saved me."):
            srcs = self.sources(["Call me Ana.", telling])
            self.assertEqual(len(srcs), 1, telling)
            self.assertEqual(srcs[0]["text"], telling)

    def test_meta_and_closing_turns_are_not_sources(self):
        srcs = self.sources([
            "Call me Ana.",
            "My father took me to Bamenda in 1984.",
            "What do you think about our conversation so far?",
            "Finish for today",
        ])
        self.assertEqual(len(srcs), 1)
        self.assertIn("Bamenda", srcs[0]["text"])

    # --- Wart 1: labels identify the material ---

    def test_telling_labels_use_their_opening_words(self):
        srcs = self.sources([
            "Call me Ana.",
            "My father took me to Bamenda in 1984, to ride the "
            "first elevator the town had ever seen.",
            "It did not stay with me.",
        ])
        labels = [s["label"] for s in srcs]
        self.assertNotIn("Something you told Liv", labels)
        self.assertIn("Bamenda", labels[0])
        self.assertIn("It did not stay with me.", labels[1])

    def test_no_two_materials_share_a_label(self):
        opening = ("The house on the hill above the town had a "
                   "wide veranda where we all gathered.")
        srcs = self.sources([
            "Call me Ana.",
            "The house on the hill above the town had a red roof "
            "and a wide veranda where we all gathered.",
            "The house on the hill above the town had a blue door "
            "my grandfather painted one dry season.",
            opening,
        ])
        labels = [s["label"] for s in srcs]
        self.assertEqual(len(labels), len(set(labels)))

    def test_media_labels_use_the_detail_the_item_carries(self):
        media = {
            "m1": {"kind": "photo", "source": "archive",
                   "caption": "Christmas at home in Bamenda with "
                              "everyone gathered around the tree",
                   "date_str": "December 1978", "album": "Family"},
            "m2": {"kind": "photo", "source": "archive",
                   "caption": "", "date_str": "1979", "album": ""},
            "m3": {"kind": "photo", "source": "archive",
                   "caption": "", "date_str": "",
                   "album": "Bamenda Days"},
            "m4": {"kind": "photo", "shared_at": "2:41 PM"},
            "m5": {"kind": "audio",
                   "transcript": "The shape did not stay with me "
                                 "after I left Bamenda.",
                   "shared_at": "2:52 PM"},
        }
        srcs = self.sources(
            ["My father took me to Bamenda in 1984."], media)
        by_id = {s["media_id"]: s for s in srcs if s["media_id"]}
        self.assertIn("Christmas at home", by_id["m1"]["label"])
        self.assertIn("dated 1979", by_id["m2"]["label"])
        self.assertIn("Bamenda Days", by_id["m3"]["label"])
        self.assertIn("2:41 PM", by_id["m4"]["label"])
        self.assertIn("Words you spoke in a recording",
                      by_id["m5"]["label"])
        self.assertIn("The shape did not stay",
                      by_id["m5"]["label"])

    # --- Wart 2: suggested titles are never fragments ---

    def title(self, tellings):
        return chapter.suggest_title(self.sources(
            ["Call me Ana."] + tellings))

    def test_title_from_a_clause_boundary(self):
        self.assertEqual(
            self.title(["My dad had just passed and I was lost, "
                        "and my sister heard of a boxing club."]),
            "My dad had just passed")
        self.assertEqual(
            self.title(["We are in Bamenda Cameroon, in the late "
                        "1970s, I would have been one year old."]),
            "We are in Bamenda Cameroon")
        self.assertEqual(
            self.title(["My father took me to Bamenda in 1984, "
                        "to ride the first elevator in town."]),
            "My father took me to Bamenda in 1984")

    def test_short_complete_sentence_stands_whole(self):
        self.assertEqual(self.title(["It did not stay with me."]),
                         "It did not stay with me")

    def test_no_clean_derivation_falls_back_honestly(self):
        title = self.title([
            "Alpha bravo charlie delta echo foxtrot golf hotel "
            "india juliet kilo lima mike november oscar papa."])
        self.assertEqual(title, "Untitled \u2014 yours to name")

    def test_titles_never_carry_a_truncation_ellipsis(self):
        for tellings in (
                ["My dad had just passed and I was lost, and my "
                 "sister Pamela heard of a new boxing club."],
                ["We are in Bamenda Cameroon, in the late 1970s, "
                 "close to 1976, a studio portrait."]):
            self.assertNotIn("\u2026", self.title(tellings))


class TestWartFixesEndToEnd(ChapterCase):
    def test_outline_excludes_the_name_answer(self):
        self.tell_story()   # opens with "Call me Margaret."
        view = self.outline()
        materials = view["chapter"]["materials_all"]
        self.assertEqual(len(materials), 3)
        self.assertTrue(all("Margaret." not in m["label"] or
                            "father" in m["label"]
                            for m in materials))
        texts = [m["label"] for m in materials]
        self.assertTrue(any("Bamenda" in t for t in texts))

    def test_outline_title_is_a_clean_clause(self):
        self.tell_story()
        view = self.outline()
        self.assertEqual(view["chapter"]["outline"]["title"],
                         "My father took me to Bamenda in 1984")


if __name__ == "__main__":
    unittest.main()
