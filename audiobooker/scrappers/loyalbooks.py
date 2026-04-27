import feedparser
from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import normalize_name


def calc_runtime(rss_data):
    runtime = rss_data["itunes_duration"].split(":")
    if len(runtime) == 1:  # seconds
        return int(runtime[0])
    elif len(runtime) == 2:  # minutes : seconds
        return int(runtime[1]) + (int(runtime[0]) * 60)
    elif len(runtime) == 3:  # hours : minutes : seconds
        return int(runtime[2]) + (int(runtime[1]) * 60) + \
            (int(runtime[0]) * 3600)
    return 0


def from_rss(rss_url):
    data = feedparser.parse(rss_url)
    for rss in data["entries"]:
        authors = []
        streams = [s['href'] for s in rss["links"]
                   if "audio" in s["type"]]
        for rss_data in rss["authors"]:
            if not rss_data:
                continue
            f, l = normalize_name(rss_data["name"])
            author = BookAuthor(first_name=f, last_name=l)
            authors.append(author)
        yield AudioBook(
            language=data["feed"]["language"],
            description=data["feed"]["summary"],
            tags=[t['term'] for t in data["feed"]["tags"]],
            image=data["feed"]["image"]["href"],
            streams=streams,
            title=data["feed"]["title"] + " | " + rss["title"],
            runtime=calc_runtime(rss),
            authors=authors
        )


class LoyalBooks(AudioBookSource):

    def search(self, query):
        sm = SiteMapParser("https://www.loyalbooks.com/sitemap.xml")  # reads /sitemap.xml
        for url in sm.get_urls():
            url = str(url)
            if not url.startswith("https://www.loyalbooks.com/book/"):
                continue
            t = url.split("/")[-1].replace("-", " ").lower()
            if query.lower() in t:
                yield from from_rss(url + "/feed")

    def search_by_narrator(self, query):
        return iter([])  # narrator info unavailable

    def search_by_title(self, query):
        return self.search(query)

    def search_by_author(self, query):
        return self.search(query)

    def iterate_all(self):
        """
        Generator, yields AudioBook objects
        """
        sm = SiteMapParser("https://www.loyalbooks.com/sitemap.xml")  # reads /sitemap.xml
        for url in sm.get_urls():
            url = str(url)
            if not url.startswith("https://www.loyalbooks.com/book/"):
                continue
            yield from from_rss(url + "/feed")


if __name__ == "__main__":
    from pprint import pprint

    for book in LoyalBooks().search_by_author("lovecraft"):
        print(book)

