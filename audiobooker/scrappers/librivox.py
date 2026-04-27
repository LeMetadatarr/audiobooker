from typing import Iterable

import feedparser

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import normalize_name


def _parse_playtime(playtime: str) -> int:
    parts = [int(p) for p in playtime.split(":")]
    if len(parts) == 1:
        return parts[0]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


class Librivox(AudioBookSource):
    base_url = "https://librivox.org/api/feed/audiobooks/?%s&format=json"
    authors_url = "https://librivox.org/api/feed/authors/?%s&format=json"

    def iterate_all(self, offset=0, max_offset=100000):
        url = "https://librivox.org/api/feed/audiobooks"
        params = {
            "limit": 50,
            "offset": offset,
            "extended": 1,
            "format": "json"
        }
        json_data = AudioBookSource.session.get(url, params=params).json()
        for k in json_data['books']:
            for book in self._parse_res(k):
                yield book
        if offset < max_offset:
            offset += 50
            for k in self.iterate_all(offset):
                yield k

    def search_by_author(self, query) -> Iterable[AudioBook]:
        url = "https://librivox.org/api/feed/audiobooks"
        params = {
            "author": query,
            "limit": 50,
            "extended": 1,
            "format": "json"
        }
        json_data = AudioBookSource.session.get(url, params=params).json()
        for k in json_data['books']:
            for book in self._parse_res(k):
                yield book

    def search_by_narrator(self, query) -> Iterable[AudioBook]:
        url = "https://librivox.org/api/feed/audiobooks"
        params = {
            "reader": query,
            "limit": 50,
            "extended": 1,
            "format": "json"
        }
        json_data = AudioBookSource.session.get(url, params=params).json()
        for k in json_data['books']:
            for book in self._parse_res(k):
                yield book

    def search_by_tag(self, query) -> Iterable[AudioBook]:
        url = "https://librivox.org/api/feed/audiobooks"
        params = {
            "tag": query,
            "limit": 50,
            "extended": 1,
            "format": "json"
        }
        json_data = AudioBookSource.session.get(url, params=params).json()
        for k in json_data['books']:
            for book in self._parse_res(k):
                yield book

    def search_by_title(self, query) -> Iterable[AudioBook]:
        url = "https://librivox.org/api/feed/audiobooks"
        params = {
            "title": query,
            "limit": 50,
            "extended": 1,
            "format": "json"
        }
        json_data = AudioBookSource.session.get(url, params=params).json()
        for k in json_data['books']:
            for book in self._parse_res(k):
                yield book

    def _parse_res(self, k):
        rss = feedparser.parse(k['url_rss'])
        streams = [stream['media_content'][0]["url"]
                   for stream in rss["entries"]]

        for idx, s in enumerate(k["sections"]):

            if len(s["readers"]) > 1:
                narrator = AudiobookNarrator(last_name="Various")
            else:
                f, l = normalize_name(s["readers"][0]['display_name'])
                narrator = AudiobookNarrator(last_name=l, first_name=f)

            yield AudioBook(
                streams=[streams[idx]],
                narrator=narrator,
                tags=[g["name"] for g in k["genres"]],
                authors=[BookAuthor(first_name=a["first_name"],
                                    last_name=a["last_name"])
                         for a in k["authors"]],
                title=k["title"] + " | " + s["title"],
                description=k["description"],
                year=int(k['copyright_year']),
                runtime=_parse_playtime(s['playtime']),
                language=k["language"]  # TODO - convert to lang code
            )


if __name__ == "__main__":
    l = Librivox()
    for book in l.search_by_title("Art of War"):
        print(book)
    for book in l.search_by_author("Lovecraft"):
        print(book)
