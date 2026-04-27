import feedparser
from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import normalize_name, get_soup, fuzzy_match

_BASE = "https://www.loyalbooks.com"
_SITEMAP = _BASE + "/sitemap.xml"

# Genre browsing pages exposed by LoyalBooks
_GENRE_PATHS = [
    "Action_and_Adventure", "Ancient_Texts", "Animals", "Art,_Design_and_Architecture",
    "Biography_and_Memoir", "Classics_(Antiquity)", "Children_in_Fiction",
    "Children_Non-fiction", "Comedy_and_Humour", "Drama", "Early_Modern",
    "Fantasy", "General_Fiction", "Historical_Fiction", "History", "Horror_and_Supernatural_Fiction",
    "Humor", "Instruction_and_How-To", "Language", "Literary_Fiction",
    "Love,_Romance_and_Marriage", "Modern_(19th_C)", "Music_and_Theatre",
    "Myths,_Legends_and_Fairy_Tales", "Nature_and_Wildlife", "Non-fiction",
    "Philosophy", "Poetry", "Politics_and_Economics", "Psychology",
    "Religion", "Science", "Science_Fiction", "Short_Stories", "Short_Works",
    "Spiritual_and_Inspirational", "Sport_and_Recreation", "Tragedy",
    "Travel_and_Geography", "War_and_Military", "Westerns",
]


def calc_runtime(rss_data):
    runtime = rss_data.get("itunes_duration", "0").split(":")
    if len(runtime) == 1:
        return int(runtime[0]) if runtime[0].isdigit() else 0
    elif len(runtime) == 2:
        return int(runtime[1]) + (int(runtime[0]) * 60)
    elif len(runtime) == 3:
        return int(runtime[2]) + (int(runtime[1]) * 60) + (int(runtime[0]) * 3600)
    return 0


def from_rss(rss_url):
    data = feedparser.parse(rss_url)
    feed = data.get("feed", {})
    lang = feed.get("language", "en")
    desc = feed.get("summary", "")
    tags = [t['term'] for t in feed.get("tags", [])]
    img = (feed.get("image") or {}).get("href", "")
    feed_title = feed.get("title", "")

    for rss in data.get("entries", []):
        authors = []
        streams = [s['href'] for s in rss.get("links", []) if "audio" in s.get("type", "")]
        for rss_data in rss.get("authors", []):
            if not rss_data:
                continue
            f, l = normalize_name(rss_data.get("name", ""))
            authors.append(BookAuthor(first_name=f, last_name=l))
        try:
            runtime = calc_runtime(rss)
        except Exception:
            runtime = 0
        yield AudioBook(
            language=lang,
            description=desc,
            tags=tags,
            image=img,
            streams=streams,
            title=f"{feed_title} | {rss.get('title', '')}",
            runtime=runtime,
            authors=authors,
        )


class LoyalBooks(AudioBookSource):

    def search(self, query):
        sm = SiteMapParser(_SITEMAP)
        for url in sm.get_urls():
            url = str(url)
            if "/book/" not in url:
                continue
            slug = url.split("/")[-1].replace("-", " ")
            if fuzzy_match(query, slug):
                for b in from_rss(url + "/feed"):
                    yield self._tag(b)

    def search_by_narrator(self, query):
        return iter([])  # narrator info unavailable in RSS

    def search_by_title(self, query):
        return self.search(query)

    def search_by_author(self, query):
        return self.search(query)

    def search_by_tag(self, query):
        for genre in _GENRE_PATHS:
            if not fuzzy_match(query, genre.replace("_", " ")):
                continue
            soup = get_soup(f"{_BASE}/genre/{genre}")
            if not soup:
                continue
            for a in soup.find_all("a", href=True):
                href = str(a["href"])
                if "/book/" in href:
                    url = href if href.startswith("http") else _BASE + href
                    try:
                        for b in from_rss(url + "/feed"):
                            yield self._tag(b)
                    except Exception:
                        continue

    def iterate_popular(self):
        soup = get_soup(_BASE)
        if not soup:
            return
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if "/book/" in href:
                url = href if href.startswith("http") else _BASE + href
                try:
                    for b in from_rss(url + "/feed"):
                        yield self._tag(b)
                except Exception:
                    continue

    def iterate_all(self):
        sm = SiteMapParser(_SITEMAP)
        for url in sm.get_urls():
            url = str(url)
            if "/book/" not in url:
                continue
            try:
                for b in from_rss(url + "/feed"):
                    yield self._tag(b)
            except Exception:
                continue


if __name__ == "__main__":
    from pprint import pprint

    for book in LoyalBooks().search_by_author("lovecraft"):
        print(book)

