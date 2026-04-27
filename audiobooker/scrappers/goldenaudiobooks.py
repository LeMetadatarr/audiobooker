from dataclasses import dataclass

from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, normalize_name

# Root sitemap auto-discovers all post-sitemap*.xml pages
_ROOT_SITEMAP = "https://goldenaudiobook.co/sitemap.xml"


def _iter_post_sitemaps():
    """Yield all post-sitemap URLs from the root sitemap index."""
    try:
        sm = SiteMapParser(_ROOT_SITEMAP)
        for url in sm.get_urls():
            url = str(url)
            if "post-sitemap" in url:
                yield url
    except Exception:
        pass


@dataclass
class GoldenAudioBooksAudioBook:
    url: str

    def parse_page(self):
        soup = get_soup(self.url)
        if not soup:
            return None

        h1 = soup.find("h1", {"class": "title-page"})
        if not h1:
            return None
        title = h1.text.replace(" Audiobook", "")

        cat = soup.find("span", {"class": "post-meta-category"})
        tags = [t for t in cat.text.split(" ") if len(t) > 2] if cat else []

        figure = soup.find("figure")
        img_tag = figure.find("img") if figure else None
        img = img_tag["src"] if img_tag else ""

        authors = []
        if "–" in title:
            pts = title.split("–")
            f, l = normalize_name(pts[0])
            authors = [BookAuthor(first_name=f, last_name=l)]
            title = " ".join(pts[1:])

        streams = []
        for audio in soup.find_all("audio"):
            a = audio.find("a")
            if a:
                streams.append(a.text)

        return AudioBook(
            title=title.strip(),
            streams=streams,
            image=img,
            tags=tags,
            authors=authors,
            language="en",
        )


class GoldenAudioBooks(AudioBookSource):

    def iterate_all(self):
        for sitemap_url in _iter_post_sitemaps():
            try:
                sm = SiteMapParser(sitemap_url)
            except Exception:
                continue
            for url in sm.get_urls():
                try:
                    book = GoldenAudioBooksAudioBook(url=str(url)).parse_page()
                    if book:
                        yield book
                except Exception:
                    continue
