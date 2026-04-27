from dataclasses import dataclass

import requests
from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook
from audiobooker.exceptions import ParseErrorException
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, extractor_narrator


@dataclass
class StoryNoryAudioBook:
    url: str
    image: str = ""

    def parse_page(self):
        soup = get_soup(self.url)
        streams = []
        for url in soup.find_all("a"):
            if not url.get("href"):
                continue
            if url.get("download") or url["href"].endswith(".mp3"):
                url = url["href"]
                if url.startswith("//"):
                    url = "https:" + url
                streams.append(url.strip())

        title = soup.find("title").text.strip().replace(" - Storynory", "")
        img = soup.find("img")
        if img and img.get("src"):
            img = img["src"].strip()
            if img.startswith("//"):
                img = "https:" + img
        else:
            img = self.image
        if not streams:
            raise ParseErrorException("No streams found")
        for d in soup.find_all("p"):
            if d.text.lower().startswith("download"):
                continue
            desc = d.text.split("\n")[0][:100]
            break
        else:
            desc = ""
        return AudioBook(
            title=title.strip(),
            description=desc,
            streams=streams,
            narrator=extractor_narrator(desc),
            image=img,
            language="en"
        )


class StoryNory(AudioBookSource):
    # NOTE: storynory.com migrated to a SvelteKit SPA — HTML scraping no longer works

    @classmethod
    def _parse_search_page(cls, url="https://www.storynory.com",
                           limit=-1, **params):
        soup = get_soup(url, **params)

        for entry in soup.find_all("div", {"class": "panel-body"}):
            try:
                a = entry.find("a")
                img = entry.find("img")
                yield StoryNoryAudioBook(url=a["href"],
                                         image= img["src"] if img else "").parse_page()
            except:
                continue

        if limit == -1 or limit > 0:
            limit -= 1
            next_page = soup.find("li", {"class": "bpn-next-link"})
            if next_page:
                url = next_page.find("a")["href"]
                for ntry in cls._parse_search_page(url=url, limit=limit, **params):
                    yield ntry

    def search(self, query):
        return self._parse_search_page(params={"s": query})

    def iterate_all(self):
        for u in [
            'https://www.storynory.com/post-sitemap1.xml',
            'https://www.storynory.com/post-sitemap2.xml'
        ]:
            sm = SiteMapParser(u)  # reads /sitemap.xml
            urls = sm.get_urls()  # returns iterator of sitemapper.Url instances
            for url in urls:
                try:
                    yield StoryNoryAudioBook(url=str(url)).parse_page()
                except ParseErrorException:
                    # not a book, just a blog post
                    continue


if __name__ == "__main__":
    scraper = StoryNory()
    for book in scraper.search("snow white"):
        print(book)
