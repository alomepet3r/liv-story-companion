"""Generate the SYNTHETIC sample Download Your Information export.

    python3 tests/make_sample_export.py

Writes tests/fixtures/sample_dyi_export.zip in the documented DYI
layout (posts/album/<n>.json + posts/your_posts_1.json, media files
at the referenced URIs, all under one top-level folder). Every image
is a simple scene drawn pixel by pixel with the standard library —
no real people's photos, no real data of any kind. Captions, names,
and dates are invented for the fixture.
"""
import io
import json
import struct
import zipfile
import zlib
from pathlib import Path

ROOT = "facebook-synthetic.storyteller"
OUT = Path(__file__).resolve().parent / "fixtures" / "sample_dyi_export.zip"


# --- tiny stdlib PNG painter -------------------------------------------
class Canvas:
    def __init__(self, width, height, color):
        self.w, self.h = width, height
        self.px = [list(color) for _ in range(width * height)]

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = list(color)

    def rect(self, x0, y0, x1, y1, color):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, color)

    def disc(self, cx, cy, r, color):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, color)

    def triangle(self, cx, top, half, height, color):
        for i in range(height):
            span = int(half * i / max(height, 1))
            for x in range(cx - span, cx + span + 1):
                self.set(x, top + i, color)

    def png(self):
        raw = b""
        for y in range(self.h):
            raw += b"\x00" + b"".join(
                bytes(self.px[y * self.w + x]) for x in range(self.w))

        def chunk(kind, data):
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data)))

        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw))
                + chunk(b"IEND", b""))


SKY = (168, 205, 232)
SUN = (250, 205, 60)
GROUND = (110, 165, 90)
HOUSE = (190, 45, 40)
ROOF = (120, 70, 40)
WATER = (70, 130, 190)
BOAT = (40, 80, 160)
SAIL = (245, 245, 240)
TRUNK = (110, 80, 50)
LEAVES = (60, 140, 70)


def house_scene():
    c = Canvas(120, 90, SKY)
    c.disc(102, 14, 9, SUN)
    c.rect(0, 62, 120, 90, GROUND)
    c.rect(38, 38, 82, 64, HOUSE)
    c.triangle(60, 18, 30, 22, ROOF)
    c.rect(55, 50, 66, 64, ROOF)
    return c.png()


def boat_scene():
    c = Canvas(120, 90, SKY)
    c.disc(16, 12, 8, SUN)
    c.rect(0, 52, 120, 90, WATER)
    c.triangle(60, 22, 4, 30, SAIL)
    c.rect(38, 52, 84, 60, BOAT)
    return c.png()


def tree_scene():
    c = Canvas(120, 90, SKY)
    c.rect(0, 66, 120, 90, GROUND)
    c.rect(56, 44, 65, 68, TRUNK)
    c.disc(60, 32, 20, LEAVES)
    return c.png()


def main():
    album = {
        "name": "Family Days",
        "description": "Synthetic album for the demo fixture.",
        "photos": [
            {
                "uri": f"{ROOT}/posts/album/house.png",
                "creation_timestamp": 1557619200,  # 12 May 2019 (UTC)
                "media_metadata": {"photo_metadata": {"exif_data": [{}]}},
                "description": "The red house on the hill, the "
                               "summer we painted it.",
            },
            {
                "uri": f"{ROOT}/posts/album/boat.png",
                "creation_timestamp": 1609459200,  # 1 January 2021
                "media_metadata": {"photo_metadata": {"exif_data": [{}]}},
            },
        ],
        "cover_photo": {
            "uri": f"{ROOT}/posts/album/house.png",
            "creation_timestamp": 1557619200,
        },
        "last_modified_timestamp": 1609459200,
    }
    posts = [
        {
            "timestamp": 1496275200,  # 1 June 2017
            "data": [{"post": "A quiet morning at the old school."}],
            "attachments": [
                {"data": [
                    {"media": {
                        "uri": f"{ROOT}/posts/your_posts/tree.png",
                        "creation_timestamp": 1496275200,
                        "media_metadata": {"photo_metadata": {}},
                        "description": "The mango tree behind the "
                                       "school.",
                    }},
                ]},
            ],
            "title": "Synthetic Storyteller added a new photo.",
        },
        {
            "timestamp": 1514764800,
            "data": [{"post": "Text only — no photo attached."}],
            "title": "Synthetic Storyteller updated their status.",
        },
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{ROOT}/posts/album/0.json", json.dumps(album))
        z.writestr(f"{ROOT}/posts/album/house.png", house_scene())
        z.writestr(f"{ROOT}/posts/album/boat.png", boat_scene())
        z.writestr(f"{ROOT}/posts/your_posts_1.json", json.dumps(posts))
        z.writestr(f"{ROOT}/posts/your_posts/tree.png", tree_scene())
    OUT.write_bytes(buffer.getvalue())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
