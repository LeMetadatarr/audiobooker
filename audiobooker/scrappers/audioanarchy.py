from dataclasses import dataclass

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup

_BASE = "https://www.audioanarchy.org"

# AudioAnarchy has two sections with books
_SECTIONS = [_BASE, _BASE + "/radio/"]


@dataclass
class AudioAnarchyAudioBook:
    url: str
    image: str = ""
    tags: list = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = ["Anarchy"]

    def parse_page(self) -> AudioBook:
        soup = get_soup(self.url)
        if not soup:
            return None

        streams = []
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if href.endswith(".mp3"):
                streams.append(_BASE + "/" + href.lstrip("/"))

        title_tag = soup.find("title")
        title = title_tag.text.split(" - ")[-1].split(" :: ")[-1] if title_tag else ""

        return AudioBook(
            title=title,
            streams=streams,
            image=self.image,
            tags=self.tags,
            authors=[BookAuthor(last_name="Audio Anarchy")],
            language="en",
        )


def _scrape_section(section_url, tags):
    soup = get_soup(section_url)
    if not soup:
        return
    for entry in soup.find_all("div", {"id": "album"}):
        try:
            a = entry.find("a")
            img = entry.find("img")
            if not a:
                continue
            book = AudioAnarchyAudioBook(
                url=_BASE + "/" + a["href"].lstrip("/"),
                image=_BASE + "/" + img["src"].lstrip("/") if img else "",
                tags=tags,
            ).parse_page()
            if book:
                yield book
        except Exception:
            continue


class AudioAnarchy(AudioBookSource):

    def iterate_all(self):
        for b in _scrape_section(_BASE, ["Anarchy"]):
            yield self._tag(b)
        for b in _scrape_section(_BASE + "/radio/", ["Anarchy", "Radio Drama"]):
            yield self._tag(b)

    def iterate_popular(self):
        # Front page listing is already the curated catalogue
        return self.iterate_all()
