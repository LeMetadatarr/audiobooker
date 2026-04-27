from dataclasses import dataclass

from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup


@dataclass
class HPTalesAudioBook:
    url: str

    def parse_page(self):
        soup = get_soup(self.url)
        if not soup:
            return None

        h1 = soup.find("h1", {"class": "entry-title"})
        if not h1:
            return None
        title = h1.text.strip()

        tags = ["Harry Potter", "Fantasy", "Magic"]

        root = soup.find("div", {"class": "audioigniter-root"})
        if not root or not root.get("data-tracks-url"):
            return None
        data = AudioBookSource.session.get(root["data-tracks-url"]).json()

        tags += list(set(s["subtitle"] for s in data if s.get("subtitle")))
        streams = [s["audio"] for s in data if s.get("audio")]

        return AudioBook(
            title=title,
            streams=streams,
            tags=tags,
            language="en",
        )


class HPTalesAudioBooks(AudioBookSource):

    def iterate_all(self):
        sm = SiteMapParser("https://hpaudiotales.com/wp-sitemap-posts-post-1.xml")
        for url in sm.get_urls():
            try:
                book = HPTalesAudioBook(url=str(url)).parse_page()
                if book:
                    yield self._tag(book)
            except Exception:
                continue
