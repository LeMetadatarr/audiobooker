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


# ---------------------------------------------------------------------------
# Metadata extraction from video title + description
# ---------------------------------------------------------------------------

# "by Author Name", "de Author Name" (Portuguese), "by Author1 and Author2"
_BY_RE = re.compile(
    r'\b(?:by|de)\s+([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+){0,3})'
    r'(?:\s+and\s+([A-Z][a-z.]+(?:\s+[A-Z][a-z.]+){0,3}))?',
    re.UNICODE,
)
# "Narrated by Name", "Read by Name"
_NARRATOR_RE = re.compile(
    r'\b(?:narrated|read)\s+by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',
    re.IGNORECASE,
)
# Hashtags: #audiobook  OR  # audiobook (space after #)
_HASHTAG_RE = re.compile(r'#\s*(\w+)')
# Year: "published in 1934", "publication in January 1934", "March 1933"
_YEAR_RE = re.compile(r'\b(1[6-9]\d{2}|20[0-2]\d)\b')
# Pipe/dash noise suffixes: "| HorrorBabble", "| Clark Ashton Smith's Zothique Cycle",
# "| A Cthulhu Mythos Story by …", "/ Doctor Satan"
_NOISE_SUFFIX_RE = re.compile(
    r'\s*[|/–\-]\s*(?:HorrorBabble|The Cybrarian'
    r"|[A-Z][a-zA-Z ']+Cycle"
    r'|(?:A\s+)?(?:Cthulhu Mythos|Doctor Satan|Clean Read).*'
    r'|(?:FULL\s+)?AUDIOBOOK.*'
    r'|(?:AUDIO\s*DRAMA|AUDIODRAMA).*'
    r'|in\s+INFOVISION.*'
    r'|INFOVISION.*)',
    re.IGNORECASE,
)
# Trailing standalone noise not preceded by a separator
_TRAILING_NOISE_RE = re.compile(
    r'\s*[-–]?\s*(?:FULL\s+AUDIOBOOK|AUDIOBOOK|AUDIO\s*DRAMA|AUDIODRAMA'
    r'|(?:in|an)\s+INFOVISION(?:\s+Audio\s+Drama)?|INFOVISION'
    r'|REMASTERED)\s*[!]?\s*$',
    re.IGNORECASE,
)
# Bracketed noise: [PREVIEW], [REMASTERED], [English], [unabridged], etc.
_BRACKET_RE = re.compile(r'\s*\[(?:PREVIEW|REMASTERED|English|Português|unabridged)[^\]]*\]', re.IGNORECASE)


def _parse_name(name_str: str):
    """Split 'First Last' or 'First M. Last' into (first, last)."""
    parts = name_str.strip().split()
    if len(parts) == 1:
        return "", parts[0]
    return " ".join(parts[:-1]), parts[-1]


def extract_yt_metadata(title: str, desc: str) -> dict:
    """Extract author, narrator, year, tags, and clean title from a video.

    Returns a dict with keys: ``authors``, ``narrator``, ``year``,
    ``extra_tags``, ``clean_title``.  All values may be empty/None.
    The caller decides which fields to trust vs override with configured values.
    """
    combined = title + "\n" + desc

    # --- authors (search raw combined before noise stripping) ---
    authors = []
    m = _BY_RE.search(combined)
    if m:
        first, last = _parse_name(m.group(1))
        authors.append(BookAuthor(first_name=first, last_name=last))
        if m.group(2):
            first2, last2 = _parse_name(m.group(2))
            authors.append(BookAuthor(first_name=first2, last_name=last2))

    # --- narrator ---
    narrator = None
    from audiobooker.base import AudiobookNarrator
    nm = _NARRATOR_RE.search(combined)
    if nm:
        first, last = _parse_name(nm.group(1))
        narrator = AudiobookNarrator(first_name=first, last_name=last)

    # --- year: prefer description (more reliable than title) ---
    year = 0
    ym = _YEAR_RE.search(desc) or _YEAR_RE.search(title)
    if ym:
        year = int(ym.group(1))

    # --- extra tags from hashtags (deduplicated) ---
    extra_tags = []
    _SKIP_HASHTAGS = {"audiobook", "audiolivro", "asmr", "mtg"}
    seen_tags: set = set()
    for tag in _HASHTAG_RE.findall(combined.lower()):
        if tag not in _SKIP_HASHTAGS and len(tag) > 3 and tag not in seen_tags:
            seen_tags.add(tag)
            extra_tags.append(tag)

    # --- clean title: strip hashtags, noise suffixes, bracketed labels ---
    clean = _BRACKET_RE.sub("", title)
    clean = _NOISE_SUFFIX_RE.sub("", clean)
    clean = _TRAILING_NOISE_RE.sub("", clean)
    clean = _HASHTAG_RE.sub("", clean).strip(" ,–-|")
    # collapse multiple spaces
    clean = re.sub(r'\s{2,}', ' ', clean).strip()

    return {
        "authors": authors,
        "narrator": narrator,
        "year": year,
        "extra_tags": extra_tags,
        "clean_title": clean,
    }


def _video_to_book(v: dict, authors: List[BookAuthor], tags: List[str],
                   language: str, narrator=None,
                   extract_metadata: bool = True) -> AudioBook:
    """Build an AudioBook from a raw video dict.

    When ``extract_metadata=True`` (default), author, narrator, year, and
    extra tags are inferred from the title and description.  Configured
    ``authors`` and ``narrator`` take precedence: they are only replaced by
    extracted values when not explicitly set.
    """

    title = v["title"]
    desc = v.get("desc", "")

    if extract_metadata:
        meta = extract_yt_metadata(title, desc)
        # Use clean title if extraction found something (otherwise keep original)
        if meta["clean_title"]:
            title = meta["clean_title"]
        # Authors: use configured if provided, else fall back to extracted
        resolved_authors = authors if authors else meta["authors"]
        # Narrator: use configured if provided, else extracted
        resolved_narrator = narrator if narrator is not None else meta["narrator"]
        # Year
        year = meta["year"]
        # Tags: use per-video hashtags when available; fall back to channel base tags
        resolved_tags = meta["extra_tags"] if meta["extra_tags"] else tags
    else:
        resolved_authors = authors
        resolved_narrator = narrator
        year = 0
        resolved_tags = tags

    return AudioBook(
        title=title,
        description=desc,
        image=v.get("thumb", ""),
        streams=[f"https://www.youtube.com/watch?v={v['id']}"],
        authors=resolved_authors,
        narrator=resolved_narrator,
        tags=resolved_tags,
        language=language,
        year=year,
        runtime=_length_to_seconds(v.get("length", "")),
    )


# ---------------------------------------------------------------------------
# Source base mixin — shared iterate/search for channel and playlist
# ---------------------------------------------------------------------------

class _YtSourceMixin(AudioBookSource):
    """Shared search methods for YouTube channel and playlist sources."""

    authors: List[BookAuthor]
    tags: List[str]
    language: str
    min_runtime: int
    narrator: Optional[object]  # AudiobookNarrator or None
    extract_metadata: bool
    title_blacklist: List[str]  # skip books whose title contains any of these strings

    def _title_blocked(self, title: str) -> bool:
        tl = title.lower()
        return any(s.lower() in tl for s in self.title_blacklist)

    def _make_book(self, v: dict) -> AudioBook:
        return _video_to_book(
            v,
            authors=self.authors,
            tags=self.tags,
            language=self.language,
            narrator=self.narrator,
            extract_metadata=self.extract_metadata,
        )

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

    def search_by_narrator(self, query):
        for b in self.iterate_all():
            if b.narrator:
                full = f"{b.narrator.first_name} {b.narrator.last_name}".strip()
                if fuzzy_match(query, full) or fuzzy_match(query, b.narrator.last_name):
                    yield b


@dataclass
class YoutubeChannelSource(_YtSourceMixin):
    """Generic AudioBookSource backed by a YouTube channel.

    Parameters
    ----------
    channel_url:
        Full channel URL, e.g. ``https://www.youtube.com/@HorrorBabble/videos``
    authors:
        Default author list. When ``extract_metadata=True`` and the video title
        contains a ``by <Name>`` pattern, the extracted author replaces this
        default only if ``authors`` is empty.
    narrator:
        Default narrator. Overridden by ``Narrated by`` extraction only when
        ``narrator`` is ``None``.
    tags:
        Base tag list merged with hashtag-derived tags from each video.
    language:
        ISO 639-1 language code (default ``"en"``).
    min_runtime:
        Skip videos shorter than this many seconds (default 300 s / 5 min).
    extract_metadata:
        When True (default), infer author, narrator, year, and extra tags
        from video title and description.
    """
    channel_url: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    narrator: Optional[object] = None
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    min_runtime: int = 300
    extract_metadata: bool = True
    title_blacklist: List[str] = field(default_factory=list)

    def iterate_all(self):
        for v in _iter_channel_videos(self.channel_url):
            if _length_to_seconds(v.get("length", "")) < self.min_runtime:
                continue
            book = self._make_book(v)
            if self._title_blocked(book.title):
                continue
            yield self._tag(book)


@dataclass
class YoutubePlaylistSource(_YtSourceMixin):
    """Generic AudioBookSource backed by a YouTube playlist.

    Parameters
    ----------
    playlist_url:
        Full playlist URL, e.g. ``https://www.youtube.com/playlist?list=PLxxxxxx``
    authors:
        Default author list (see ``YoutubeChannelSource.authors``).
    narrator:
        Default narrator (see ``YoutubeChannelSource.narrator``).
    tags:
        Base tag list merged with hashtag-derived tags.
    language:
        ISO 639-1 language code (default ``"en"``).
    min_runtime:
        Skip videos shorter than this many seconds (default 300 s / 5 min).
    extract_metadata:
        When True (default), infer metadata from title and description.
    """
    playlist_url: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    narrator: Optional[object] = None
    tags: List[str] = field(default_factory=list)
    language: str = "en"
    min_runtime: int = 300
    extract_metadata: bool = True
    title_blacklist: List[str] = field(default_factory=list)

    def iterate_all(self):
        for v in _iter_playlist_videos(self.playlist_url):
            if _length_to_seconds(v.get("length", "")) < self.min_runtime:
                continue
            book = self._make_book(v)
            if self._title_blocked(book.title):
                continue
            yield self._tag(book)


# ---------------------------------------------------------------------------
# Pre-configured channel sources
# ---------------------------------------------------------------------------

class TheCybrarian(YoutubeChannelSource):
    """Robert E. Howard audiobooks (Conan, Solomon Kane, Kull…) read by The Cybrarian."""

    def __init__(self):
        from audiobooker.base import AudiobookNarrator
        super().__init__(
            channel_url="https://www.youtube.com/@TheCybrarian/videos",
            # Configured author is the fallback; extraction will override per-video
            # when a "by <Name>" pattern is found (handles co-authored pieces).
            authors=[BookAuthor(first_name="Robert E.", last_name="Howard")],
            narrator=AudiobookNarrator(first_name="The", last_name="Cybrarian"),
            tags=["Fantasy", "Sword and Sorcery", "Robert E. Howard", "Conan"],
            language="en",
            min_runtime=120,
            title_blacklist=["update", "preview", "cracking packs", "magic the gathering",
                             "board game", "tabletop", "mtg"],
        )


class HorrorBabble(YoutubeChannelSource):
    """Horror short fiction narrated by Ian Gordon (HorrorBabble)."""

    def __init__(self):
        from audiobooker.base import AudiobookNarrator
        super().__init__(
            channel_url="https://www.youtube.com/@HorrorBabble/videos",
            # Authors left empty so extraction fills in per-video author from title
            authors=[],
            narrator=AudiobookNarrator(first_name="Ian", last_name="Gordon"),
            tags=["Horror", "Lovecraft", "Weird Fiction", "Short Stories"],
            language="en",
            min_runtime=300,
        )


class TheDustyTome(YoutubeChannelSource):
    """Classic literature, horror, and weird fiction audiobooks by The Dusty Tome."""

    def __init__(self):
        super().__init__(
            channel_url="https://www.youtube.com/@TheDustyTome/videos",
            authors=[],  # extracted per-video from title
            narrator=None,  # extracted per-video
            tags=["Classic Literature", "Horror", "Weird Fiction", "Audiobook"],
            language="en",
            min_runtime=600,
            extract_metadata=True,
        )
