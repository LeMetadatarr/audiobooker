from dataclasses import dataclass
from typing import Iterable

from sitemapparser import SiteMapParser

from audiobooker.exceptions import ParseErrorException
from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, extractor_narrator, extract_year

_BASE = "https://stephenkingaudiobooks.com"
_SITEMAP = "https://stephenkingaudiobooks.com/wp-sitemap-posts-post-1.xml"


@dataclass
class StephenKingAudioBook:
    url: str

    def parse_page(self):
        soup = get_soup(self.url)
        if not soup:
            return None

        tags = soup.find("span", {"class": "post-meta-category"})
        h1 = soup.find("h1", {"class": "title-page"})
        if not h1:
            return None
        title = h1.text.replace("\xa0", " ")

        content = soup.find("div", {"class": "post-single clearfix"})
        if not content:
            return None

        p = content.find("p")
        desc = p.text.replace("\xa0", " ") if p else ""

        img_tag = content.find("img")
        img = img_tag["src"] if img_tag else ""

        if tags and "Harry Potter" not in tags.text:
            authors = [BookAuthor(first_name="Stephen", last_name="King")]
        else:
            authors = [BookAuthor(first_name="J.K.", last_name="Rowling")]

        if tags and "Stephen Fry" in title and "Harry Potter" in tags.text:
            narrator = AudiobookNarrator(first_name="Stephen", last_name="Fry")
        else:
            narrator = extractor_narrator(title) or extractor_narrator(desc)

        streams = []
        for audio in content.find_all("audio"):
            a = audio.find("a")
            if a:
                streams.append(a.text)

        if not streams:
            raise ParseErrorException("No streams found")

        return AudioBook(
            title=title.replace(" Audiobook", ""),
            streams=streams,
            description=desc,
            narrator=narrator,
            image=img,
            tags=[],
            authors=authors,
            year=extract_year(title) or extract_year(desc),
            language="en",
        )


class StephenKingAudioBooks(AudioBookSource):

    @classmethod
    def _parse_page(cls, url=_BASE, limit=-1, **params) -> Iterable[AudioBook]:
        soup = get_soup(url, **params)
        if not soup:
            return
        for entry in soup.find_all("article"):
            try:
                a = entry.find("a")
                if not a:
                    continue
                book = StephenKingAudioBook(url=a["href"]).parse_page()
                if book:
                    yield book
            except Exception:
                continue
        if limit == -1 or limit > 0:
            next_page = soup.find("div", {"class": "nav-previous"})
            if next_page:
                a = next_page.find("a")
                if a:
                    yield from cls._parse_page(url=a["href"], limit=limit - 1, **params)

    def search(self, query) -> Iterable[AudioBook]:
        return self._parse_page(params={"s": query})

    def iterate_all(self) -> Iterable[AudioBook]:
        sm = SiteMapParser(_SITEMAP)
        for url in sm.get_urls():
            try:
                book = StephenKingAudioBook(url=str(url)).parse_page()
                if book:
                    yield book
            except Exception:
                continue
