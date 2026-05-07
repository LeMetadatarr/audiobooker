from typing import Iterable

import feedparser

from audiobooker.base import (
    AudioBook,
    AudioBookChapter,
    AudiobookNarrator,
    BookAuthor,
)
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import normalize_name

_API = "https://librivox.org/api/feed/audiobooks"


def _parse_playtime(playtime: str) -> int:
    if not playtime:
        return 0
    parts = [int(p) for p in playtime.split(":")]
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _api_get(params: dict) -> dict:
    """Query the LibriVox API.

    LibriVox returns HTTP 500 for some parameter combinations (e.g.,
    ``title=^X`` combined with ``author=Y``).  Treat any non-2xx response or
    JSON-decode failure as an empty result rather than raising.
    """
    try:
        resp = AudioBookSource.session.get(
            _API, params={"extended": 1, "format": "json", "limit": 50, **params}
        )
        if resp.status_code >= 400:
            return {}
        return resp.json()
    except Exception:
        return {}


def _section_streams(rss_url: str) -> list:
    rss = feedparser.parse(
        rss_url,
        agent=AudioBookSource.session.headers.get("User-Agent"),
        request_headers={"Connection": "close"},
    )
    return [
        e["media_content"][0]["url"]
        for e in rss.get("entries", [])
        if e.get("media_content")
    ]


def _build_book(k: dict) -> AudioBook:
    """Convert one LibriVox API record into a single typed ``AudioBook``."""
    rss_streams = _section_streams(k["url_rss"])

    chapters: list = []
    narrators: list = []
    seen_readers: set = set()
    offset = 0.0

    for idx, s in enumerate(k.get("sections", [])):
        playtime = _parse_playtime(s.get("playtime", "0"))
        stream = (
            rss_streams[idx]
            if idx < len(rss_streams)
            else s.get("listen_url", "")
        )
        chapters.append(
            AudioBookChapter(
                title=s.get("title", ""),
                offset=offset,
                runtime=float(playtime),
                stream=stream,
            )
        )
        offset += playtime
        for r in s.get("readers", []) or []:
            display = r.get("display_name", "")
            if not display or display in seen_readers:
                continue
            seen_readers.add(display)
            f, l = normalize_name(display)
            narrators.append(AudiobookNarrator(first_name=f, last_name=l))

    # Total runtime: prefer the API-supplied figure, fall back to summed sections.
    total_secs = int(k.get("totaltimesecs") or 0) or int(offset)

    # Streams: book-level list is every section URL in order.
    streams = [c.stream for c in chapters if c.stream]

    external_ids: dict = {}
    if k.get("id"):
        external_ids["librivox_id"] = str(k["id"])

    genres = [g["name"] for g in k.get("genres") or []]

    book = AudioBook(
        streams=streams,
        narrators=narrators,
        tags=genres,
        genres=list(genres),
        authors=[
            BookAuthor(
                first_name=a.get("first_name", ""),
                last_name=a.get("last_name", ""),
            )
            for a in k.get("authors") or []
        ],
        title=k.get("title", ""),
        description=k.get("description", ""),
        year=int(k.get("copyright_year") or 0),
        runtime=total_secs,
        language=k.get("language", ""),
        chapters=chapters,
        codec="mp3",  # LibriVox publishes 64/128 kbps MP3 by policy
        bitrate="",
        external_ids=external_ids,
    )
    return book


class Librivox(AudioBookSource):

    def iterate_all(self, offset=0, max_offset=100000) -> Iterable[AudioBook]:
        data = _api_get({"offset": offset})
        for k in data.get("books", []):
            yield self._tag(_build_book(k))
        if offset < max_offset and data.get("books"):
            yield from self.iterate_all(offset + 50, max_offset)

    def search_by_author(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"author": query}).get("books", []):
            yield self._tag(_build_book(k))

    def search_by_narrator(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"reader": query}).get("books", []):
            yield self._tag(_build_book(k))

    def search_by_tag(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"tag": query}).get("books", []):
            yield self._tag(_build_book(k))

    def search_by_title(self, query) -> Iterable[AudioBook]:
        # Librivox's title= param returns 404; use the generic search= param
        for k in _api_get({"search": query}).get("books", []):
            yield self._tag(_build_book(k))
