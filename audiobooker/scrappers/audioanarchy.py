from dataclasses import dataclass

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup

_BASE = "https://www.audioanarchy.org"


@dataclass
class AudioAnarchyAudioBook:
    url: str
    image: str = ""

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
            tags=["Anarchy"],
            authors=[BookAuthor(last_name="Audio Anarchy")],
            language="en",
        )


class AudioAnarchy(AudioBookSource):

    def iterate_all(self):
        soup = get_soup(_BASE)
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
                ).parse_page()
                if book:
                    yield book
            except Exception:
                continue
