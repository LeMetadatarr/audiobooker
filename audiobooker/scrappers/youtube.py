"""YouTube channel/playlist scraper (optional dependency: tutubo).

Usage requires `pip install audiobooker[youtube]` or `pip install tutubo`.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import fuzzy_match

try:
    from tutubo.models import Channel as _YTChannel, Playlist as _YTPlaylist
    _TUTUBO_AVAILABLE = True
except ImportError:
    _TUTUBO_AVAILABLE = False


def _require_tutubo():
    if not _TUTUBO_AVAILABLE:
        raise ImportError(
            "tutubo is required for YouTube sources. "
            "Install it with: pip install tutubo"
        )


def _length_to_seconds(s: str) -> int:
    if not s:
        return 0
    parts = s.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 0


def _parse_video_item(item: dict) -> Optional[dict]:
    """Parse a richItemRenderer dict into a plain dict, handling both
    the old videoRenderer and the new lockupViewModel layouts."""
    ri = item.get("richItemRenderer", {})
    content = ri.get("content", {})

    # Old layout
    vr = content.get("videoRenderer", {})
    if vr:
        vid_id = vr.get("videoId", "")
        title = vr.get("title", {}).get("runs", [{}])[0].get("text", "")
        length_str = vr.get("lengthText", {}).get("simpleText", "")
        thumb = vr.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "")
        desc = vr.get("descriptionSnippet", {}).get("runs", [{}])[0].get("text", "")
        if vid_id and title:
            return {"id": vid_id, "title": title, "length": length_str,
                    "thumb": thumb, "desc": desc}
        return None

    # New layout (lockupViewModel)
    lvm = content.get("lockupViewModel", {})
    if lvm:
        title = (lvm.get("metadata", {})
                    .get("lockupMetadataViewModel", {})
                    .get("title", {})
                    .get("content", ""))
        sources = (lvm.get("contentImage", {})
                      .get("thumbnailViewModel", {})
                      .get("image", {})
                      .get("sources", []))
        thumb = sources[-1]["url"] if sources else ""
        m = re.search(r"/vi/([^/]+)/", thumb)
        vid_id = m.group(1) if m else ""
        # duration from bottom overlay badge
        length_str = ""
        overlays = (lvm.get("contentImage", {})
                       .get("thumbnailViewModel", {})
                       .get("overlays", []))
        for overlay in overlays:
            for badge in overlay.get("thumbnailBottomOverlayViewModel", {}).get("badges", []):
                t = badge.get("thumbnailBadgeViewModel", {}).get("text", "")
                if ":" in t:
                    length_str = t
                    break
        if vid_id and title:
            return {"id": vid_id, "title": title, "length": length_str,
                    "thumb": thumb, "desc": ""}
        return None

    return None


def _iter_channel_videos(channel_url: str):
    """Yield raw video dicts from a YouTube channel page (first page only)."""
    _require_tutubo()
    ch = _YTChannel(channel_url)
    data = ch.initial_data
    # walk tabs and take the first richGridRenderer we find
    tabs = (data.get("contents", {})
                .get("twoColumnBrowseResultsRenderer", {})
                .get("tabs", []))
    for tab in tabs:
        tr = tab.get("tabRenderer", {})
        rgr = tr.get("content", {}).get("richGridRenderer", {})
        if not rgr:
            continue
        for item in rgr.get("contents", []):
            result = _parse_video_item(item)
            if result:
                yield result
        break


def _parse_playlist_video(item: dict) -> Optional[dict]:
    """Parse a playlistVideoRenderer item into a plain dict."""
    pvr = item.get("playlistVideoRenderer", {})
    if not pvr:
        return None
    vid_id = pvr.get("videoId", "")
    title = pvr.get("title", {}).get("runs", [{}])[0].get("text", "")
    length_str = pvr.get("lengthText", {}).get("simpleText", "")
    thumbs = pvr.get("thumbnail", {}).get("thumbnails", [{}])
    thumb = thumbs[-1].get("url", "") if thumbs else ""
    if vid_id and title:
        return {"id": vid_id, "title": title, "length": length_str,
                "thumb": thumb, "desc": ""}
    return None


def _iter_playlist_videos(playlist_url: str):
    """Yield raw video dicts from a YouTube playlist (via tutubo.Playlist)."""
    _require_tutubo()
    try:
        data = _YTPlaylist(playlist_url).initial_data
    except Exception:
        return

    tabs = (data.get("contents", {})
                .get("twoColumnBrowseResultsRenderer", {})
                .get("tabs", []))
    for tab in tabs:
        tr = tab.get("tabRenderer", {})
        slr = tr.get("content", {}).get("sectionListRenderer", {})
        if not slr:
            continue
        for section in slr.get("contents", []):
            isr = section.get("itemSectionRenderer", {})
            for inner in isr.get("contents", []):
                pvlr = inner.get("playlistVideoListRenderer", {})
                if pvlr:
                    for item in pvlr.get("contents", []):
                        result = _parse_playlist_video(item)
                        if result:
                            yield result
                    return


def _video_to_book(v: dict, authors: List[BookAuthor],
                   tags: List[str], language: str) -> AudioBook:
    return AudioBook(
        title=v["title"],
        description=v.get("desc", ""),
        image=v.get("thumb", ""),
        streams=[f"https://www.youtube.com/watch?v={v['id']}"],
        authors=authors,
        tags=tags,
        language=language,
        runtime=_length_to_seconds(v.get("length", "")),
    )


@dataclass
class YoutubeChannelSource(AudioBookSource):
    """Generic AudioBookSource backed by a YouTube channel.

    Parameters
    ----------
    channel_url:
        Full channel URL, e.g. ``https://www.youtube.com/@HorrorBabble/videos``
    authors:
        Author list stamped on every yielded AudioBook.
    tags:
        Tag list stamped on every yielded AudioBook.
    language:
        ISO 639-1 language code (default ``"en"``).
    min_runtime:
        Skip videos shorter than this many seconds (filters out trailers/shorts).
        Default 300 (5 minutes).
    """
    channel_url: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    min_runtime: int = 300

    def iterate_all(self):
        for v in _iter_channel_videos(self.channel_url):
            if _length_to_seconds(v.get("length", "")) < self.min_runtime:
                continue
            book = _video_to_book(v, self.authors, self.tags, self.language)
            yield self._tag(book)

    def iterate_popular(self):
        # First page = most recent/featured — good enough as "popular"
        return self.iterate_all()

    def search_by_title(self, query):
        for b in self.iterate_all():
            if fuzzy_match(query, b.title):
                yield b

    def search_by_author(self, query):
        for b in self.iterate_all():
            for a in b.authors:
                full = f"{a.first_name} {a.last_name}".strip()
                if fuzzy_match(query, full) or fuzzy_match(query, a.last_name):
                    yield b
                    break

    def search_by_tag(self, query):
        for b in self.iterate_all():
            if any(fuzzy_match(query, t) for t in b.tags):
                yield b


@dataclass
class YoutubePlaylistSource(AudioBookSource):
    """Generic AudioBookSource backed by a YouTube playlist.

    Parameters
    ----------
    playlist_url:
        Full playlist URL, e.g.
        ``https://www.youtube.com/playlist?list=PLxxxxxx``
    authors:
        Author list stamped on every yielded AudioBook.
    tags:
        Tag list stamped on every yielded AudioBook.
    language:
        ISO 639-1 language code (default ``"en"``).
    min_runtime:
        Skip videos shorter than this many seconds (default 300 / 5 min).
    """
    playlist_url: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    min_runtime: int = 300

    def iterate_all(self):
        for v in _iter_playlist_videos(self.playlist_url):
            if _length_to_seconds(v.get("length", "")) < self.min_runtime:
                continue
            book = _video_to_book(v, self.authors, self.tags, self.language)
            yield self._tag(book)

    def iterate_popular(self):
        return self.iterate_all()

    def search_by_title(self, query):
        for b in self.iterate_all():
            if fuzzy_match(query, b.title):
                yield b

    def search_by_author(self, query):
        for b in self.iterate_all():
            for a in b.authors:
                full = f"{a.first_name} {a.last_name}".strip()
                if fuzzy_match(query, full) or fuzzy_match(query, a.last_name):
                    yield b
                    break

    def search_by_tag(self, query):
        for b in self.iterate_all():
            if any(fuzzy_match(query, t) for t in b.tags):
                yield b


# ---------------------------------------------------------------------------
# Pre-configured channel sources
# ---------------------------------------------------------------------------

class TheCybrarian(YoutubeChannelSource):
    """Robert E. Howard audiobooks (Conan, Solomon Kane, Kull…) read by The Cybrarian."""

    def __init__(self):
        super().__init__(
            channel_url="https://www.youtube.com/@TheCybrarian/videos",
            authors=[BookAuthor(first_name="Robert E.", last_name="Howard")],
            tags=["Fantasy", "Sword and Sorcery", "Robert E. Howard", "Conan"],
            language="en",
            min_runtime=120,  # some shorts are under 5 min; keep anything >2 min
        )


class HorrorBabble(YoutubeChannelSource):
    """Horror short fiction audiobooks narrated by Ian Gordon (HorrorBabble)."""

    def __init__(self):
        super().__init__(
            channel_url="https://www.youtube.com/@HorrorBabble/videos",
            authors=[BookAuthor(last_name="Various")],
            tags=["Horror", "Lovecraft", "Weird Fiction", "Short Stories"],
            language="en",
            min_runtime=300,
        )
