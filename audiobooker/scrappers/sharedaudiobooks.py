from dataclasses import dataclass

from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, normalize_name


@dataclass
class SharedAudioBook:
    url: str
    image: str = ""

    def parse_page(self):
        soup = get_soup(self.url)
        title = soup.find("h1", {"class": "entry-title"}).text
        tags = [t for t in soup.find("ul", {"class": "post-categories"}).text.split("\n") if t.strip()]

        img = soup.find_all("img")[-1]["src"]

        authors = []

        if "–" in title:
            pts = title.split("–")
            author_name = pts[0]
            title = " ".join(pts[1:])

            f, l = normalize_name(author_name)

            authors = [BookAuthor(first_name=f, last_name=l)]

        streams = [s.find("a").text for s in soup.find_all("audio")]

        return AudioBook(
            title=title.strip(),
            streams=streams,
            image=img,
            tags=tags,
            authors=authors,
            language="en"
        )


class SharedAudioBooks(AudioBookSource):
    # NOTE: sharedaudiobooks.com returns HTTP 500 — site appears to be down

    @classmethod
    def iterate_all(cls, limit=-1, offset=0):
        sm = SiteMapParser('https://sharedaudiobooks.com/post-sitemap.xml')  # reads /sitemap.xml
        urls = sm.get_urls()  # returns iterator of sitemapper.Url instances
        for url in urls:
            url = str(url)
            if url == "https://sharedaudiobooks.com/":
                continue
            yield SharedAudioBook(url=str(url)).parse_page()

        for i in range(2, 10):
            sm = SiteMapParser(f'https://sharedaudiobooks.com/post-sitemap{i}.xml')  # reads /sitemap.xml
            urls = sm.get_urls()  # returns iterator of sitemapper.Url instances
            for url in urls:
                yield SharedAudioBook(url=str(url)).parse_page()


if __name__ == "__main__":
    from pprint import pprint

    scraper = SharedAudioBooks()
    for book in scraper.iterate_all():
        pprint(book)
