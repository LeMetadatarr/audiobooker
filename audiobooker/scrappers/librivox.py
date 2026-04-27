from typing import Iterable

import feedparser

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import normalize_name

_API = "https://librivox.org/api/feed/audiobooks"


def _parse_playtime(playtime: str) -> int:
    parts = [int(p) for p in playtime.split(":")]
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def _api_get(params: dict) -> dict:
    resp = AudioBookSource.session.get(_API, params={"extended": 1, "format": "json", "limit": 50, **params})
    return resp.json()


class Librivox(AudioBookSource):

    def iterate_all(self, offset=0, max_offset=100000) -> Iterable[AudioBook]:
        data = _api_get({"offset": offset})
        for k in data.get("books", []):
            for b in self._parse_res(k):
                yield self._tag(b)
        if offset < max_offset:
            yield from self.iterate_all(offset + 50, max_offset)

    def search_by_author(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"author": query}).get("books", []):
            for b in self._parse_res(k):
                yield self._tag(b)

    def search_by_narrator(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"reader": query}).get("books", []):
            for b in self._parse_res(k):
                yield self._tag(b)

    def search_by_tag(self, query) -> Iterable[AudioBook]:
        for k in _api_get({"tag": query}).get("books", []):
            for b in self._parse_res(k):
                yield self._tag(b)

    def search_by_title(self, query) -> Iterable[AudioBook]:
        # Librivox's title= param returns 404; use the generic search= param
        for k in _api_get({"search": query}).get("books", []):
            for b in self._parse_res(k):
                yield self._tag(b)

    def _parse_res(self, k) -> Iterable[AudioBook]:
        rss = feedparser.parse(k["url_rss"],
                               agent=AudioBookSource.session.headers.get("User-Agent"),
                               request_headers={"Connection": "close"})
        rss_streams = [e["media_content"][0]["url"]
                       for e in rss["entries"] if e.get("media_content")]

        for idx, s in enumerate(k["sections"]):
            if len(s["readers"]) > 1:
                narrator = AudiobookNarrator(last_name="Various")
            else:
                f, l = normalize_name(s["readers"][0]["display_name"])
                narrator = AudiobookNarrator(first_name=f, last_name=l)

            stream = rss_streams[idx] if idx < len(rss_streams) else s.get("listen_url", "")

            yield AudioBook(
                streams=[stream] if stream else [],
                narrator=narrator,
                tags=[g["name"] for g in k["genres"]],
                authors=[BookAuthor(first_name=a["first_name"], last_name=a["last_name"])
                         for a in k["authors"]],
                title=k["title"] + " | " + s["title"],
                description=k["description"],
                year=int(k["copyright_year"]),
                runtime=_parse_playtime(s["playtime"]),
                language=k["language"],
            )
