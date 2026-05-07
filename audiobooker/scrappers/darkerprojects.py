from dataclasses import dataclass

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, iter_sitemap_urls

_SITEMAP = "https://darkerprojects.com/wp-sitemap-posts-post-1.xml"
_BASE = "https://darkerprojects.com"


@dataclass
class DarkerProjectsAudioBook:
    url: str

    def parse_page(self):
        soup = get_soup(self.url)
        if not soup:
            return None

        title_tag = soup.find("title")
        title = title_tag.text if title_tag else self.url.split("/")[-1]

        desc = ""
        content = soup.find("div", {"class": "inner-entry-content"})
        if content:
            for d in content.find_all("i"):
                desc = d.text
                break

        img = ""
        imgs = soup.find_all("img")
        if len(imgs) > 1:
            img = imgs[1].get("src", "")

        streams = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.endswith(".mp3") and href not in streams:
                streams.append(href)

        return AudioBook(
            title=title,
            streams=streams,
            image=img,
            tags=["audio drama"],
            genres=["Audio Drama"],
            description=desc,
            authors=[BookAuthor(last_name="Darker Projects")],
            language="en",
        )


class DarkerProjects(AudioBookSource):

    def iterate_popular(self):
        """Yield shows listed on the DarkerProjects front page."""
        soup = get_soup(_BASE)
        if not soup:
            return
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if _BASE not in href or href in seen:
                continue
            path = href.replace(_BASE, "").strip("/")
            if not path or "?" in path or "." in path:
                continue
            seen.add(href)
            try:
                book = DarkerProjectsAudioBook(url=href).parse_page()
                if book and book.streams:
                    yield self._tag(book)
            except Exception:
                continue

    def iterate_all(self):
        for url in iter_sitemap_urls(_SITEMAP):
            try:
                book = DarkerProjectsAudioBook(url=url).parse_page()
                if book:
                    yield self._tag(book)
            except Exception:
                continue
