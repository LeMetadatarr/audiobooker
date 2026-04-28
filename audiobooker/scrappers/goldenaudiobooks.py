from dataclasses import dataclass

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, normalize_name, iter_sitemap_urls

_ROOT_SITEMAP = "https://goldenaudiobook.co/sitemap.xml"
_FRONT_PAGE = "https://goldenaudiobook.co"


def _iter_post_sitemaps():
    """Yield all post-sitemap leaf URLs from the root sitemap index."""
    for url in iter_sitemap_urls(_ROOT_SITEMAP):
        if "post-sitemap" in url:
            yield url


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

    def iterate_popular(self):
        """Yield books featured on the front page (curated selection)."""
        soup = get_soup(_FRONT_PAGE)
        if not soup:
            return
        seen = set()
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if _FRONT_PAGE not in href or href in seen:
                continue
            # Front page book links contain a slug-style path with no query string
            path = href.replace(_FRONT_PAGE, "").strip("/")
            if not path or "?" in path or "." in path or "/" in path:
                continue
            seen.add(href)
            try:
                book = GoldenAudioBooksAudioBook(url=href).parse_page()
                if book:
                    yield self._tag(book)
            except Exception:
                continue

    def iterate_all(self):
        for sitemap_url in _iter_post_sitemaps():
            for url in iter_sitemap_urls(sitemap_url):
                try:
                    book = GoldenAudioBooksAudioBook(url=url).parse_page()
                    if book:
                        yield self._tag(book)
                except Exception:
                    continue
