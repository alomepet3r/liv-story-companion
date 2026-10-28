"""API-level tests for the Bring-your-archive slice (server.app).

Handlers are exercised directly (no HTTP, no API key): the live
client is disabled so chat turns land on the canned companion.
All data is synthetic. Run: python3 -m unittest discover -s tests
"""
import json
import unittest

from server import app
from tests.test_archive import PNG, album_export, make_zip


class ArchiveApiCase(unittest.TestCase):
    def setUp(self):
        app._sessions.clear()
        self._saved_key = app.MODEL_API_KEY
        app.MODEL_API_KEY = ""  # canned path only
        self.session = "test-session"
        self.fields = {"session_id": self.session,
                       "consent": "true", "age_confirmed": "true"}

    def tearDown(self):
        app.MODEL_API_KEY = self._saved_key
        app._sessions.clear()

    def upload(self, data=None, fields=None, filename="export.zip"):
        files = {"file": (filename, "application/zip",
                          album_export() if data is None else data)}
        return app.handle_archive_upload(fields or self.fields, files)

    def select(self, item_ids, **overrides):
        payload = {"session_id": self.session, "consent": True,
                   "age_confirmed": True, "item_ids": item_ids}
        payload.update(overrides)
        return app.handle_archive_select(payload)


class TestUploadGates(ArchiveApiCase):
    def test_unconsented_upload_403(self):
        fields = dict(self.fields, consent="false")
        status, _ = self.upload(fields=fields)
        self.assertEqual(status, 403)

    def test_age_unconfirmed_upload_403(self):
        fields = dict(self.fields, age_confirmed="false")
        status, _ = self.upload(fields=fields)
        self.assertEqual(status, 403)

    def test_wrong_file_type_400(self):
        status, body = self.upload(filename="notes.txt")
        self.assertEqual(status, 400)
        self.assertIn(".zip", body["error"])

    def test_oversize_zip_413(self):
        saved = app.ARCHIVE_ZIP_CAP
        app.ARCHIVE_ZIP_CAP = 100
        try:
            status, body = self.upload()
        finally:
            app.ARCHIVE_ZIP_CAP = saved
        self.assertEqual(status, 413)
        self.assertIn("200 MB", body["error"])

    def test_malformed_zip_400_and_nothing_half_imported(self):
        status, _ = self.upload()
        self.assertEqual(status, 200)
        before = dict(app._session(self.session)["archive"])
        self.assertTrue(before)
        status, body = self.upload(data=b"not a zip")
        self.assertEqual(status, 400)
        after = app._session(self.session)["archive"]
        self.assertEqual(set(after), set(before))  # store untouched


class TestSelectionGating(ArchiveApiCase):
    def test_upload_lists_items_but_media_store_stays_empty(self):
        status, body = self.upload()
        self.assertEqual(status, 200)
        self.assertEqual(body["found"], 2)
        captions = {item["name"]: item["caption"]
                    for item in body["items"]}
        self.assertEqual(captions["house.png"],
                         "The red house on the hill.")
        dates = {item["name"]: item["date"] for item in body["items"]}
        self.assertEqual(dates["house.png"], "12 May 2019")
        sess = app._session(self.session)
        # THE doctrine check: nothing has reached the media store
        # (the only road to Liv) before explicit selection.
        self.assertEqual(sess["media"], {})

    def test_select_moves_only_ticked_items(self):
        _, body = self.upload()
        house = [i for i in body["items"]
                 if i["name"] == "house.png"][0]
        status, shared = self.select([house["id"]])
        self.assertEqual(status, 200)
        self.assertEqual(len(shared["media"]), 1)
        sess = app._session(self.session)
        self.assertEqual(len(sess["media"]), 1)
        media = sess["media"][shared["media"][0]["id"]]
        self.assertEqual(media["source"], "archive")
        self.assertEqual(media["caption"], "The red house on the hill.")
        self.assertEqual(media["date_str"], "12 May 2019")
        self.assertEqual(media["data"], PNG)

    def test_select_unconsented_403(self):
        _, body = self.upload()
        status, _ = self.select([body["items"][0]["id"]],
                                consent=False)
        self.assertEqual(status, 403)

    def test_select_nothing_400(self):
        self.upload()
        status, _ = self.select([])
        self.assertEqual(status, 400)


class TestEndToEnd(ArchiveApiCase):
    def _shared_media_id(self):
        _, body = self.upload()
        house = [i for i in body["items"]
                 if i["name"] == "house.png"][0]
        _, shared = self.select([house["id"]])
        return shared["media"][0]["id"]

    def test_chat_turn_carries_caption_and_date_in_history(self):
        media_id = self._shared_media_id()
        status, body = app.handle_chat({
            "session_id": self.session, "consent": True,
            "age_confirmed": True,
            "message": "This one is from the hill above town.",
            "media_ids": [media_id],
        })
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "canned")
        history = app._session(self.session)["history"]
        user_turns = [h["content"] for h in history
                      if h["role"] == "user"]
        self.assertTrue(any("from their archive" in t
                            and "12 May 2019" in t
                            and "The red house on the hill." in t
                            for t in user_turns), user_turns)

    def test_model_view_includes_caption_date_and_album(self):
        media_id = self._shared_media_id()
        sess = app._session(self.session)
        item = sess["media"][media_id]
        messages = [{"role": "user", "content": "Here it is."}]
        shaped = app._media_turn_messages(messages, [item], "Here it is.")
        parts = shaped[0]["content"]
        text = "".join(p.get("text", "") for p in parts
                       if isinstance(p, dict))
        self.assertIn("The red house on the hill.", text)
        self.assertIn("12 May 2019", text)
        self.assertIn("Family Days", text)
        self.assertTrue(any(p.get("type") == "image_url"
                            for p in parts if isinstance(p, dict)))

    def test_model_view_plain_photo_has_no_archive_context(self):
        item = {"kind": "photo", "content_type": "image/png",
                "data": PNG, "name": "plain.png"}
        messages = [{"role": "user", "content": "A photo."}]
        shaped = app._media_turn_messages(messages, [item], "A photo.")
        text = "".join(p.get("text", "") for p in shaped[0]["content"]
                       if isinstance(p, dict))
        self.assertNotIn("archive", text.lower())

    def test_archive_intent_walkthrough_names_the_button(self):
        # Day 3 conversation-first composer: the walkthrough names
        # the one attach control and the picker choice, not the
        # retired media-bar button.
        status, body = app.handle_chat({
            "session_id": self.session, "consent": True,
            "age_confirmed": True,
            "message": "Can I show you my facebook archive?",
        })
        self.assertEqual(status, 200)
        self.assertIn("\u201c+\u201d button", body["reply"])
        self.assertIn("Document or archive", body["reply"])

    def test_unselected_items_never_enter_model_view(self):
        # Upload, share nothing: a chat turn has no media at all,
        # and the session media store is still empty.
        self.upload()
        status, _ = app.handle_chat({
            "session_id": self.session, "consent": True,
            "age_confirmed": True, "message": "Hello again.",
        })
        self.assertEqual(status, 200)
        self.assertEqual(app._session(self.session)["media"], {})


if __name__ == "__main__":
    unittest.main()
