"""Bring-your-archive: parse a Facebook "Download Your Information"
(DYI) export, in memory, for the photos it contains.

Doctrine (SOCIAL-IMPORT-DIRECTION.md, consent architecture):
  * The export is read ONCE, in the storyteller's own session, and
    held only in memory — nothing is written to disk, ever, and the
    parsed items die with the session/tab, like all demo media.
  * Only PHOTOS and their captions/dates are extracted. The words of
    posts are never imported as items in this slice.
  * Nothing here reaches the companion: items sit in the session's
    archive store until the storyteller ticks them and shares them
    explicitly (see handle_archive_select in app.py). Bulk import
    by default would be a doctrine violation.
  * PLATFORM-STAGE NOTE: at platform stage, imported photos must be
    masked-by-default for third parties (the SAM privacy-masking
    direction) before they are kept or shown onward. This demo
    slice does NOT implement SAM masking and must never claim to.

DYI layout (documented Facebook export structure; the feasibility
spike file was not yet present when this was built, so the parser
is deliberately layout-tolerant rather than schema-exact):
  * The zip holds JSON files plus the media files they reference.
  * Albums live at posts/album/<n>.json:
        {"name": ..., "description": ...,
         "photos": [{"uri": "posts/album/...", 
                     "creation_timestamp": 1557619200,
                     "media_metadata": {...},
                     "description": ..., "title": ...}, ...]}
  * Posts live at posts/your_posts_1.json (a list): each entry may
    carry attachments whose data[].media.uri points at a photo,
    with the media's own description/title/creation_timestamp.
  * "uri" values are relative to the export root; zip entry names
    may carry an extra top-level folder prefix
    (e.g. "facebook-user/posts/album/x.jpg").
The parser therefore walks EVERY JSON file generically: any object
with a "uri" naming an image file that exists in the zip becomes a
photo item, inheriting caption/date/album context from its
ancestors in the JSON tree. Image files sitting in album/post
folders that no JSON references are included too (no caption), so
export variants still work. Facebook's JSON famously mangles UTF-8
into latin-1 code points; captions are repaired when possible.

Safety: the zip is only ever read through zipfile into memory —
no path from the archive is ever used as a filesystem path, and
entries with traversal/absolute names are skipped outright
(zip-slip cannot reach a disk we never write to, and is refused
anyway). Caps are enforced: zip size (checked by the caller),
total uncompressed size, per-photo size, per-JSON size, item count.
"""
import io
import json
import zipfile
from datetime import datetime, timezone

ARCHIVE_ZIP_CAP = 200 * 1024 * 1024         # the .zip as uploaded
ARCHIVE_TOTAL_UNCOMPRESSED_CAP = 500 * 1024 * 1024
ARCHIVE_PHOTO_CAP = 10 * 1024 * 1024        # matches the photo cap
ARCHIVE_JSON_CAP = 20 * 1024 * 1024
ARCHIVE_MAX_ITEMS = 500

IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# Folders whose unreferenced images still count as archive photos.
_PHOTO_DIR_HINTS = ("/album/", "/your_posts/", "photos_and_videos")


class ArchiveError(Exception):
    """A plain-language failure the storyteller can be told."""


def _fix_fb_text(value):
    """Repair Facebook's latin-1-mangled UTF-8, when it is that."""
    if not isinstance(value, str):
        return ""
    try:
        return value.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def _is_safe_entry(name):
    """Refuse absolute paths and traversal — zip-slip hygiene."""
    normalized = name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("~"):
        return False
    if ":" in normalized.split("/", 1)[0]:  # drive-letter style
        return False
    return ".." not in normalized.split("/")


def _extension(name):
    lowered = name.lower()
    for ext in IMAGE_TYPES:
        if lowered.endswith(ext):
            return ext
    return None


def _date_str(timestamp):
    if not isinstance(timestamp, (int, float)) or timestamp <= 0:
        return ""
    seconds = timestamp / 1000 if timestamp > 10_000_000_000 else timestamp
    try:
        moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return ""
    return moment.strftime("%d %B %Y")


def _walk_json(node, context, refs):
    """Collect photo references ({uri, caption, date_ts, album}).

    Context flows down the tree: an album's name, a media object's
    own description/title, the nearest creation_timestamp.
    """
    if isinstance(node, dict):
        ctx = dict(context)
        album = node.get("name")
        if isinstance(album, str) and "photos" in node:
            ctx["album"] = _fix_fb_text(album).strip()
        for key in ("creation_timestamp", "timestamp"):
            value = node.get(key)
            if isinstance(value, (int, float)) and value > 0:
                ctx["date_ts"] = value
                break
        uri = node.get("uri")
        if isinstance(uri, str) and _extension(uri):
            # The caption belongs to the media object ITSELF (its
            # own description/title). An ancestor's description —
            # an album blurb, a post's title — is not the photo's
            # caption and is never borrowed as one.
            caption = ""
            for key in ("description", "title"):
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    caption = _fix_fb_text(value).strip()[:300]
                    break
            refs.append({
                "uri": uri.replace("\\", "/"),
                "caption": caption,
                "date_ts": ctx.get("date_ts"),
                "album": ctx.get("album", ""),
            })
        for value in node.values():
            _walk_json(value, ctx, refs)
    elif isinstance(node, list):
        for item in node:
            _walk_json(item, context, refs)


def parse_dyi_zip(data):
    """Parse DYI zip bytes -> {"items": [...], "skipped": int}.

    Each item: {name, content_type, data, caption, date_ts,
    date_str, album, size}. Raises ArchiveError with plain-language
    copy when the export cannot be read at all or holds no photos;
    partial problems (missing/oversize/traversal entries) count as
    "skipped" instead of failing the whole import.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ArchiveError(
            "That file could not be opened as an archive. Please "
            "choose the .zip file from Download Your Information.")
    infos = [i for i in archive.infolist() if not i.is_dir()]
    total_uncompressed = sum(i.file_size for i in infos)
    if total_uncompressed > ARCHIVE_TOTAL_UNCOMPRESSED_CAP:
        raise ArchiveError(
            "That archive is very large when opened up — larger "
            "than this demo can read. A photos-only export from "
            "Download Your Information should fit.")

    entries = {}       # normalized name -> ZipInfo
    suffix_index = {}  # name without first folder -> ZipInfo
    skipped = 0
    for info in infos:
        name = info.filename.replace("\\", "/")
        if not _is_safe_entry(name):
            skipped += 1
            continue
        entries[name] = info
        if "/" in name:
            suffix_index.setdefault(name.split("/", 1)[1], info)

    def resolve(uri):
        if uri in entries:
            return entries[uri]
        if uri in suffix_index:
            return suffix_index[uri]
        for name, info in entries.items():
            if name.endswith("/" + uri):
                return info
        return None

    # 1) References from every JSON file in the export.
    refs = []
    for name, info in list(entries.items()):
        if not name.lower().endswith(".json"):
            continue
        if info.file_size > ARCHIVE_JSON_CAP:
            skipped += 1
            continue
        try:
            parsed = json.loads(
                archive.read(info).decode("utf-8", "replace"))
        except Exception:
            continue  # an unreadable sidecar never sinks the import
        _walk_json(parsed, {}, refs)

    items = []
    seen_entries = set()

    def add_item(info, caption="", date_ts=None, album=""):
        nonlocal skipped
        if len(items) >= ARCHIVE_MAX_ITEMS:
            skipped += 1
            return
        if info.file_size > ARCHIVE_PHOTO_CAP:
            skipped += 1
            return
        ext = _extension(info.filename)
        raw = archive.read(info)
        if len(raw) > ARCHIVE_PHOTO_CAP:
            skipped += 1
            return
        items.append({
            "name": info.filename.replace("\\", "/").rsplit("/", 1)[-1],
            "content_type": IMAGE_TYPES[ext],
            "data": raw,
            "caption": caption,
            "date_ts": date_ts,
            "date_str": _date_str(date_ts),
            "album": album,
            "size": len(raw),
        })
        seen_entries.add(info.filename)

    for ref in refs:
        info = resolve(ref["uri"])
        if info is None or info.filename in seen_entries:
            if info is None:
                skipped += 1
            continue
        add_item(info, caption=ref["caption"],
                 date_ts=ref["date_ts"], album=ref["album"])

    # 2) Unreferenced photos in the photo folders — export variants
    # whose JSON we did not recognise still give up their pictures.
    for name, info in entries.items():
        if info.filename in seen_entries:
            continue
        if not _extension(name):
            continue
        lowered = "/" + name.lower()
        if any(hint in lowered for hint in _PHOTO_DIR_HINTS):
            add_item(info)

    if not items:
        raise ArchiveError(
            "I could not find any photos in that export. In "
            "Download Your Information, make sure Photos is included "
            "and the format is JSON, then try that .zip here.")
    items.sort(key=lambda item: (item["date_ts"] or 0))
    return {"items": items, "skipped": skipped}
