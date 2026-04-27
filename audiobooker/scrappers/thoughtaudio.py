from dataclasses import dataclass

from sitemapparser import SiteMapParser

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.scrappers import AudioBookSource
from audiobooker.utils import get_soup, extract_year, normalize_name


@dataclass
class ThoughtAudioAudioBook:
    url: str

    def parse_page(self):
        soup = get_soup(self.url)
        streams = []
        img = None
        for url in soup.find_all("a"):
            if url["href"].endswith(".mp3"):
                streams.append(url["href"])
        for url in soup.find_all("iframe"):
            if "youtube" not in url["src"]:
                continue
            vid = url["src"].split("/")[-1].split("?")[0]
            img = f"https://img.youtube.com/vi/{vid}/0.jpg"
            streams.append(
                url["src"].split("?feature=oembed")[0].
                replace("https://www.youtube.com/embed/", "https://www.youtube.com/watch?v=")
            )
        title = soup.find("title").text.split(" – ThoughtAudio")[0].split(": ")[-1]

        if not title:
            title = soup.find("span", {"class": "Text-Head"}).text

        narrator = None
        author = None
        desc = ""
        for s in soup.find_all("p"):
            if "WRITTEN BY:" in s.text:
                name = s.text.split("WRITTEN BY:")[-1]
                f, l = normalize_name(name)
                author = BookAuthor(first_name=f, last_name=l)

            elif "NARRATED BY:" in s.text:
                name = s.text.split("NARRATED BY:")[-1]
                f, l = normalize_name(name)
                narrator = AudiobookNarrator(first_name=f, last_name=l)
            elif s.text.strip() and narrator and author:
                desc = s.text.split("\n")[0]
                break
        if not img:
            pics = soup.find_all("img")
            pic = pics[1] if len(pics) > 1 else pics[0] if pics else None
            img = pic["src"] if pic else ""
        return AudioBook(
            title=title.strip(),
            streams=streams,
            image=img or "",
            description=desc,
            narrator=narrator,
            year=extract_year(desc),
            authors=[author] if author else [],
            tags=["ThoughtAudio"],
            language="en"
        )


class ThoughtAudio(AudioBookSource):

    def iterate_all(self):
        sm = SiteMapParser('http://thoughtaudio.com/wp-sitemap-posts-post-1.xml')  # reads /sitemap.xml
        urls = sm.get_urls()  # returns iterator of sitemapper.Url instances
        for url in urls:
            url = str(url)
            yield ThoughtAudioAudioBook(url=url).parse_page()


if __name__ == "__main__":
    from pprint import pprint

    scraper = ThoughtAudio()
    for book in scraper.iterate_all():
        pprint(book)
