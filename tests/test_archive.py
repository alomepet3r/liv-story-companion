"""Offline unit tests for server.archive (DYI export parsing).

All fixtures are synthetic and built in memory — no real exports,
no real photos. Run: python3 -m unittest discover -s tests
"""
import io
import json
import unittest
import zipfile

from server import archive
from server.archive import ArchiveError, parse_dyi_zip

PNG = b"\x89PNG\r\n\x1a\n" + b"synthetic-image-bytes"
JPG = b"\xff\xd8\xff" + b"synthetic-jpeg-bytes"


def make_zip(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            if isinstance(data, str):
                data = data.encode("utf-8")
            z.writestr(name, data)
    return buffer.getvalue()


def album_export():
    album = {
        "name": "Family Days",
        "description": "Album blurb — not a photo caption.",
        "photos": [
            {"uri": "posts/album/house.png",
             "creation_timestamp": 1557619200,
             "description": "The red house on the hill."},
            {"uri": "posts/album/boat.jpg",
             "creation_timestamp": 1609459200},
        ],
        "cover_photo": {"uri": "posts/album/house.png",
                        "creation_timestamp": 1557619200},
    }
    return make_zip({
        "facebook-synthetic/posts/album/0.json": json.dumps(album),
        "facebook-synthetic/posts/album/house.png": PNG,
        "facebook-synthetic/posts/album/boat.jpg": JPG,
    })


class TestParse(unittest.TestCase):
    def test_album_export_found_with_caption_and_date(self):
        result = parse_dyi_zip(album_export())
        self.assertEqual(len(result["items"]), 2)  # cover deduped
        house, boat = result["items"]  # sorted by date
        self.assertEqual(house["name"], "house.png")
        self.assertEqual(house["caption"], "The red house on the hill.")
        self.assertEqual(house["date_str"], "12 May 2019")
        self.assertEqual(house["album"], "Family Days")
        self.assertEqual(house["content_type"], "image/png")
        self.assertEqual(boat["caption"], "")  # album blurb not borrowed
        self.assertEqual(boat["date_str"], "01 January 2021")

    def test_post_attachment_media_found(self):
        posts = [{
            "timestamp": 1496275200,
            "data": [{"post": "A quiet morning."}],
            "attachments": [{"data": [{"media": {
                "uri": "posts/your_posts/tree.png",
                "creation_timestamp": 1496275200,
                "description": "The mango tree.",
            }}]}],
            "title": "Added a new photo.",
        }]
        data = make_zip({
            "posts/your_posts_1.json": json.dumps(posts),
            "posts/your_posts/tree.png": PNG,
        })
        result = parse_dyi_zip(data)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["caption"], "The mango tree.")
        self.assertEqual(result["items"][0]["date_str"], "01 June 2017")

    def test_unreferenced_album_photo_included_without_caption(self):
        data = make_zip({
            "posts/album/0.json": json.dumps({"name": "A", "photos": []}),
            "posts/album/orphan.png": PNG,
        })
        result = parse_dyi_zip(data)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["caption"], "")

    def test_facebook_mangled_utf8_caption_repaired(self):
        album = {"name": "Cafés", "photos": [
            {"uri": "posts/album/a.png", "creation_timestamp": 1,
             "description": "Le cafÃ© du village"}]}
        data = make_zip({
            "posts/album/0.json": json.dumps(album, ensure_ascii=False),
            "posts/album/a.png": PNG,
        })
        result = parse_dyi_zip(data)
        self.assertEqual(result["items"][0]["caption"],
                         "Le café du village")

    def test_zip_slip_entries_never_become_items(self):
        album = {"name": "Evil", "photos": [
            {"uri": "../evil.png", "creation_timestamp": 1},
            {"uri": "posts/album/good.png", "creation_timestamp": 2,
             "description": "Good one."}]}
        data = make_zip({
            "posts/album/0.json": json.dumps(album),
            "../evil.png": PNG,
            "posts/album/../../evil2.png": PNG,
            "posts/album/good.png": PNG,
        })
        result = parse_dyi_zip(data)
        names = [item["name"] for item in result["items"]]
        self.assertEqual(names, ["good.png"])
        self.assertGreaterEqual(result["skipped"], 2)

    def test_oversize_photo_skipped_not_fatal(self):
        big = b"x" * (archive.ARCHIVE_PHOTO_CAP + 1)
        album = {"name": "Mix", "photos": [
            {"uri": "posts/album/big.png", "creation_timestamp": 1},
            {"uri": "posts/album/small.png", "creation_timestamp": 2}]}
        data = make_zip({
            "posts/album/0.json": json.dumps(album),
            "posts/album/big.png": big,
            "posts/album/small.png": PNG,
        })
        result = parse_dyi_zip(data)
        self.assertEqual([i["name"] for i in result["items"]],
                         ["small.png"])
        self.assertGreaterEqual(result["skipped"], 1)

    def test_total_uncompressed_cap(self):
        data = make_zip({"posts/album/a.png": PNG})
        original = archive.ARCHIVE_TOTAL_UNCOMPRESSED_CAP
        archive.ARCHIVE_TOTAL_UNCOMPRESSED_CAP = 10
        try:
            with self.assertRaises(ArchiveError):
                parse_dyi_zip(data)
        finally:
            archive.ARCHIVE_TOTAL_UNCOMPRESSED_CAP = original

    def test_missing_referenced_photo_counts_skipped(self):
        album = {"name": "Gaps", "photos": [
            {"uri": "posts/album/gone.png", "creation_timestamp": 1},
            {"uri": "posts/album/here.png", "creation_timestamp": 2}]}
        data = make_zip({
            "posts/album/0.json": json.dumps(album),
            "posts/album/here.png": PNG,
        })
        result = parse_dyi_zip(data)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["skipped"], 1)

    def test_malformed_zip_raises_plain_error(self):
        with self.assertRaises(ArchiveError):
            parse_dyi_zip(b"this is not a zip at all")

    def test_zip_without_photos_raises_plain_error(self):
        data = make_zip({"readme.txt": "hello",
                         "posts/your_posts_1.json": "[]"})
        with self.assertRaises(ArchiveError):
            parse_dyi_zip(data)

    def test_text_only_posts_never_become_items(self):
        posts = [{"timestamp": 1, "data": [{"post": "just words"}]}]
        data = make_zip({"posts/your_posts_1.json": json.dumps(posts)})
        with self.assertRaises(ArchiveError):
            parse_dyi_zip(data)


if __name__ == "__main__":
    unittest.main()
