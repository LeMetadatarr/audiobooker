"""Extra coverage for audiobooker.utils."""
import unittest
from unittest.mock import patch, MagicMock

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.utils import (
    check_url_availability, get_html, get_soup, iter_sitemap_urls,
    random_user_agent, score_book, USER_AGENTS,
)


class TestUserAgent(unittest.TestCase):
    def test_returns_listed_agent(self):
        ua = random_user_agent()
        self.assertIn(ua, USER_AGENTS)


class TestGetHtml(unittest.TestCase):
    def test_returns_text_on_success(self):
        from audiobooker.scrappers import AudioBookSource
        with patch.object(AudioBookSource.session, "get") as g:
            g.return_value.text = "<html>"
            self.assertEqual(get_html("http://x"), "<html>")

    def test_falls_back_to_verify_false(self):
        from audiobooker.scrappers import AudioBookSource
        ok = MagicMock()
        ok.text = "<html2>"
        with patch.object(AudioBookSource.session, "get",
                          side_effect=[Exception("ssl"), ok]):
            self.assertEqual(get_html("http://x"), "<html2>")

    def test_returns_none_on_total_failure(self):
        from audiobooker.scrappers import AudioBookSource
        with patch.object(AudioBookSource.session, "get",
                          side_effect=Exception("nope")):
            self.assertIsNone(get_html("http://x"))

    def test_get_soup_returns_none_on_failure(self):
        with patch("audiobooker.utils.get_html", return_value=None):
            self.assertIsNone(get_soup("http://x"))

    def test_get_soup_parses(self):
        with patch("audiobooker.utils.get_html",
                   return_value="<html><body><p>hi</p></body></html>"):
            soup = get_soup("http://x")
            self.assertEqual(soup.p.text, "hi")


class TestCheckUrlAvailability(unittest.TestCase):
    def test_returns_true_for_2xx(self):
        from audiobooker.scrappers import AudioBookSource
        resp = MagicMock(status_code=200)
        with patch.object(AudioBookSource.session, "head", return_value=resp):
            self.assertTrue(check_url_availability("http://x"))

    def test_returns_false_for_4xx(self):
        from audiobooker.scrappers import AudioBookSource
        resp = MagicMock(status_code=404)
        with patch.object(AudioBookSource.session, "head", return_value=resp):
            self.assertFalse(check_url_availability("http://x"))

    def test_returns_false_on_exception(self):
        from audiobooker.scrappers import AudioBookSource
        with patch.object(AudioBookSource.session, "head",
                          side_effect=Exception("network")):
            self.assertFalse(check_url_availability("http://x"))


class TestIterSitemapUrls(unittest.TestCase):
    def test_handles_parser_failure(self):
        with patch("sitemapparser.SiteMapParser",
                   side_effect=Exception("bad")):
            # Should yield nothing without raising
            self.assertEqual(list(iter_sitemap_urls("http://x/sitemap.xml")), [])

    def test_yields_urls(self):
        sm = MagicMock()
        sm.has_urls.return_value = True
        sm.has_sitemaps.return_value = False
        sm.get_urls.return_value = ["http://x/a", "http://x/b"]
        with patch("sitemapparser.SiteMapParser", return_value=sm):
            result = list(iter_sitemap_urls("http://x/s.xml"))
        self.assertEqual(result, ["http://x/a", "http://x/b"])

    def test_recurses_into_sitemap_index(self):
        index_sm = MagicMock()
        index_sm.has_urls.return_value = False
        index_sm.has_sitemaps.return_value = True
        child = MagicMock()
        child.loc = "http://x/child.xml"
        index_sm.get_sitemaps.return_value = [child]

        leaf_sm = MagicMock()
        leaf_sm.has_urls.return_value = True
        leaf_sm.has_sitemaps.return_value = False
        leaf_sm.get_urls.return_value = ["http://x/page1"]

        with patch("sitemapparser.SiteMapParser",
                   side_effect=[index_sm, leaf_sm]):
            result = list(iter_sitemap_urls("http://x/index.xml"))
        self.assertEqual(result, ["http://x/page1"])


class TestScoreBookEdges(unittest.TestCase):
    def test_iterate_all_method_returns_zero(self):
        book = AudioBook(title="X")
        self.assertEqual(score_book("anything", book, "iterate_all"), 0.0)

    def test_unknown_method_falls_back_to_search(self):
        book = AudioBook(
            title="Dracula",
            authors=[BookAuthor(first_name="Bram", last_name="Stoker")],
        )
        score = score_book("Dracula", book, "totally_unknown_method")
        self.assertGreater(score, 0)


if __name__ == "__main__":
    unittest.main()
