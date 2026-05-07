"""Edge-case coverage for individual scraper modules (offline)."""
import unittest
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from audiobooker.exceptions import ParseErrorException
from audiobooker.scrappers.audioanarchy import (
    AudioAnarchy,
    AudioAnarchyAudioBook,
    _scrape_section,
)
from audiobooker.scrappers.darkerprojects import (
    DarkerProjects,
    DarkerProjectsAudioBook,
)
from audiobooker.scrappers.goldenaudiobooks import (
    GoldenAudioBooksAudioBook,
    GoldenAudioBooks,
)
from audiobooker.scrappers.hpaudiotales import (
    HPTalesAudioBook,
    HPTalesAudioBooks,
)
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks, calc_runtime, from_rss
from audiobooker.scrappers.stephenkingaudiobooks import (
    StephenKingAudioBook,
    StephenKingAudioBooks,
)


def _soup(html):
    return BeautifulSoup(html, "html.parser")


class TestAudioAnarchy(unittest.TestCase):
    def test_parse_page_returns_none_when_soup_none(self):
        with patch("audiobooker.scrappers.audioanarchy.get_soup",
                   return_value=None):
            self.assertIsNone(AudioAnarchyAudioBook(url="http://x").parse_page())

    def test_parse_page_basic(self):
        html = '<title>Site - Section :: My Book</title>' \
               '<a href="/audio.mp3">x</a>'
        with patch("audiobooker.scrappers.audioanarchy.get_soup",
                   return_value=_soup(html)):
            book = AudioAnarchyAudioBook(url="http://x").parse_page()
        self.assertEqual(book.title, "My Book")
        self.assertTrue(book.streams)

    def test_scrape_section_handles_none_soup(self):
        with patch("audiobooker.scrappers.audioanarchy.get_soup",
                   return_value=None):
            self.assertEqual(list(_scrape_section("http://x", ["t"])), [])

    def test_scrape_section_skips_no_anchor(self):
        html = '<div id="album"><img src="i.jpg"/></div>'
        with patch("audiobooker.scrappers.audioanarchy.get_soup",
                   return_value=_soup(html)):
            self.assertEqual(list(_scrape_section("http://x", ["t"])), [])

    def test_scrape_section_absolute_href(self):
        html = '<div id="album"><a href="http://elsewhere/book"></a></div>'
        with patch("audiobooker.scrappers.audioanarchy.get_soup",
                   return_value=_soup(html)), \
             patch.object(AudioAnarchyAudioBook, "parse_page",
                          return_value=None):
            list(_scrape_section("http://x", ["t"]))

    def test_iterate_all(self):
        with patch("audiobooker.scrappers.audioanarchy._scrape_section",
                   return_value=iter([])):
            self.assertEqual(list(AudioAnarchy().iterate_all()), [])

    def test_iterate_popular_alias(self):
        src = AudioAnarchy()
        with patch.object(src, "iterate_all", return_value=iter([])):
            self.assertEqual(list(src.iterate_popular()), [])


class TestDarkerProjects(unittest.TestCase):
    def test_parse_page_returns_none(self):
        with patch("audiobooker.scrappers.darkerprojects.get_soup",
                   return_value=None):
            self.assertIsNone(DarkerProjectsAudioBook(url="x").parse_page())

    def test_iterate_all_handles_no_soup(self):
        with patch("audiobooker.scrappers.darkerprojects.get_soup",
                   return_value=None):
            self.assertEqual(list(DarkerProjects().iterate_all()), [])


class TestGoldenAudioBooks(unittest.TestCase):
    def test_parse_returns_none_no_soup(self):
        with patch("audiobooker.scrappers.goldenaudiobooks.get_soup",
                   return_value=None):
            self.assertIsNone(GoldenAudioBooksAudioBook(url="x").parse_page())

    def test_iterate_all_handles_no_soup(self):
        with patch("audiobooker.scrappers.goldenaudiobooks.get_soup",
                   return_value=None):
            self.assertEqual(list(GoldenAudioBooks().iterate_all()), [])


class TestHPTales(unittest.TestCase):
    def test_parse_returns_none(self):
        with patch("audiobooker.scrappers.hpaudiotales.get_soup",
                   return_value=None):
            self.assertIsNone(HPTalesAudioBook(url="x").parse_page())

    def test_iterate_all_handles_no_soup(self):
        with patch("audiobooker.scrappers.hpaudiotales.iter_sitemap_urls",
                   return_value=iter([])):
            self.assertEqual(list(HPTalesAudioBooks().iterate_all()), [])


class TestStephenKing(unittest.TestCase):
    def test_parse_returns_none_no_soup(self):
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=None):
            self.assertIsNone(StephenKingAudioBook(url="x").parse_page())

    def test_parse_returns_none_when_no_h1(self):
        html = '<html></html>'
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=_soup(html)):
            self.assertIsNone(StephenKingAudioBook(url="x").parse_page())

    def test_parse_returns_none_when_no_content(self):
        html = '<h1 class="title-page">T</h1>'
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=_soup(html)):
            self.assertIsNone(StephenKingAudioBook(url="x").parse_page())

    def test_parse_raises_when_no_streams(self):
        html = ('<h1 class="title-page">My Title</h1>'
                '<div class="post-single clearfix"><p>desc</p></div>')
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=_soup(html)):
            with self.assertRaises(ParseErrorException):
                StephenKingAudioBook(url="x").parse_page()

    def test_parse_harry_potter_branch(self):
        html = (
            '<span class="post-meta-category">Harry Potter</span>'
            '<h1 class="title-page">Stephen Fry HP1 Audiobook</h1>'
            '<div class="post-single clearfix"><p>desc 1997</p>'
            '<audio><a>http://x/a.mp3</a></audio></div>'
        )
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=_soup(html)):
            b = StephenKingAudioBook(url="x").parse_page()
        self.assertEqual(b.authors[0].last_name, "Rowling")
        self.assertEqual(b.narrator.last_name, "Fry")
        self.assertEqual(b.year, 1997)

    def test_iterate_all_handles_no_streams_exception(self):
        with patch("audiobooker.scrappers.stephenkingaudiobooks.iter_sitemap_urls",
                   return_value=iter(["http://x"])), \
             patch.object(StephenKingAudioBook, "parse_page",
                          side_effect=ParseErrorException("no streams")):
            self.assertEqual(list(StephenKingAudioBooks().iterate_all()), [])

    def test_parse_page_pagination_classmethod_no_soup(self):
        with patch("audiobooker.scrappers.stephenkingaudiobooks.get_soup",
                   return_value=None):
            self.assertEqual(
                list(StephenKingAudioBooks._parse_page(url="http://x")),
                [],
            )


class TestLoyalBooks(unittest.TestCase):
    def test_calc_runtime_invalid_returns_zero(self):
        self.assertEqual(calc_runtime({"itunes_duration": "abc"}), 0)

    def test_from_rss_no_chapters(self):
        with patch("audiobooker.scrappers.loyalbooks.feedparser.parse",
                   return_value={"feed": {}, "entries": []}):
            self.assertEqual(list(from_rss("http://x")), [])

    def test_from_rss_yields_book(self):
        feed = {
            "feed": {"title": "B", "language": "en", "summary": "d",
                     "tags": [{"term": "Horror"}],
                     "image": {"href": "http://i.jpg"}},
            "entries": [{
                "title": "Ch1",
                "authors": [{"name": "Mary Shelley"}, {"name": ""},
                            {"name": "Mary Shelley"}],
                "itunes_duration": "1:00",
                "links": [{"type": "audio/mpeg", "href": "http://a.mp3"}],
            }],
        }
        with patch("audiobooker.scrappers.loyalbooks.feedparser.parse",
                   return_value=feed):
            books = list(from_rss("http://x"))
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "B")
        self.assertEqual(len(books[0].authors), 1)

    def test_from_rss_calc_runtime_exception(self):
        # Provide an entry with an authors field that triggers no exception,
        # but force calc_runtime to fail by passing bad iterable.
        feed = {
            "feed": {"title": "B"},
            "entries": [{"title": "Ch1", "authors": [],
                         "itunes_duration": ["weird-list"]}],
        }
        with patch("audiobooker.scrappers.loyalbooks.feedparser.parse",
                   return_value=feed):
            books = list(from_rss("http://x"))
        # chap_runtime fell back to 0 — but a chapter was still appended
        self.assertEqual(len(books), 1)

    def test_search_by_narrator_empty(self):
        self.assertEqual(list(LoyalBooks().search_by_narrator("any")), [])

    def test_search_by_tag_no_match(self):
        # No genre fuzzy-matches "ZZZNOMATCH"
        self.assertEqual(list(LoyalBooks().search_by_tag("ZZZNOMATCH")), [])

    def test_search_by_tag_with_match(self):
        # 'Horror' matches 'Horror_and_Supernatural_Fiction'
        with patch("audiobooker.scrappers.loyalbooks.get_soup",
                   return_value=_soup(
                       '<a href="/book/dracula"></a>'
                       '<a href="http://www.loyalbooks.com/book/dracula"></a>'
                       '<a href="/other"></a>'
                   )), \
             patch("audiobooker.scrappers.loyalbooks.from_rss",
                   return_value=iter([])):
            list(LoyalBooks().search_by_tag("Horror"))

    def test_search_by_tag_handles_rss_exception(self):
        with patch("audiobooker.scrappers.loyalbooks.get_soup",
                   return_value=_soup('<a href="/book/x"></a>')), \
             patch("audiobooker.scrappers.loyalbooks.from_rss",
                   side_effect=Exception("rss bad")):
            self.assertEqual(list(LoyalBooks().search_by_tag("Horror")), [])

    def test_search_by_tag_no_soup(self):
        with patch("audiobooker.scrappers.loyalbooks.get_soup",
                   return_value=None):
            self.assertEqual(list(LoyalBooks().search_by_tag("Horror")), [])

    def test_iterate_popular_no_soup(self):
        with patch("audiobooker.scrappers.loyalbooks.get_soup",
                   return_value=None):
            self.assertEqual(list(LoyalBooks().iterate_popular()), [])

    def test_iterate_popular_handles_rss_exception(self):
        with patch("audiobooker.scrappers.loyalbooks.get_soup",
                   return_value=_soup('<a href="/book/x"></a>')), \
             patch("audiobooker.scrappers.loyalbooks.from_rss",
                   side_effect=Exception("bad")):
            self.assertEqual(list(LoyalBooks().iterate_popular()), [])

    def test_iterate_all_handles_exception(self):
        with patch("audiobooker.scrappers.loyalbooks.iter_sitemap_urls",
                   return_value=iter(["http://x/book/y"])), \
             patch("audiobooker.scrappers.loyalbooks.from_rss",
                   side_effect=Exception("bad")):
            self.assertEqual(list(LoyalBooks().iterate_all()), [])

    def test_search_skips_non_book_urls(self):
        with patch("audiobooker.scrappers.loyalbooks.iter_sitemap_urls",
                   return_value=iter(["http://x/notabook",
                                      "http://x/book/zzznotmatching"])):
            self.assertEqual(list(LoyalBooks().search("randomnotmatching")), [])


class TestLibrivox(unittest.TestCase):
    def test_iterate_all_handles_no_data(self):
        with patch("audiobooker.scrappers.librivox._api_get",
                   return_value={}):
            self.assertEqual(list(Librivox().iterate_all()), [])


if __name__ == "__main__":
    unittest.main()
