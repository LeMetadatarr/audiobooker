from dataclasses import dataclass

from audiobooker.base import AudioBook
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, iter_sitemap_urls


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
            genres=["Fantasy"],
            language="en",
        )


class HPTalesAudioBooks(AudioBookSource):

    def iterate_popular(self):
        soup = get_soup("https://hpaudiotales.com")
        if not soup:
            return
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if "hpaudiotales.com" not in href or href in seen:
                continue
            if any(x in href for x in ["/category/", "/tag/", "/page/", "/#", "/wp-"]):
                continue
            seen.add(href)
            try:
                book = HPTalesAudioBook(url=href).parse_page()
                if book:
                    yield self._tag(book)
            except Exception:
                continue

    def iterate_all(self):
        for url in iter_sitemap_urls("https://hpaudiotales.com/wp-sitemap-posts-post-1.xml"):
            try:
                book = HPTalesAudioBook(url=url).parse_page()
                if book:
                    yield self._tag(book)
            except Exception:
                continue
