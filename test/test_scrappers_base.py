"""Tests for audiobooker.scrappers base AudioBookSource methods."""
import unittest

from audiobooker.base import AudioBook, AudiobookNarrator, BookAuthor
from audiobooker.scrappers import AudioBookSource


class FakeSrc(AudioBookSource):
    def __init__(self, books):
        self._books = books

    def iterate_all(self):
        for b in self._books:
            yield b


def _b(title, author_last="X", first="Y", tags=None, narrator=None):
    return AudioBook(
        title=title,
        authors=[BookAuthor(first_name=first, last_name=author_last)],
        tags=tags or [],
        narrator=narrator,
    )


class TestSourceMethods(unittest.TestCase):
    def test_search_combines_title_author_tag(self):
        src = FakeSrc([
            _b("Dracula", author_last="Stoker"),
            _b("Frankenstein", author_last="Shelley", tags=["Gothic"]),
        ])
        results = list(src.search("Dracula"))
        self.assertTrue(any(b.title == "Dracula" for b in results))

    def test_search_dedups_by_id(self):
        b = _b("Dracula", author_last="Stoker", tags=["Dracula"])
        src = FakeSrc([b])
        # b matches title query and tag query, but iterate_all returns the
        # same instance — the id-based dedup in search() should drop dupes.
        results = list(src.search("Dracula"))
        self.assertEqual(len(results), 1)

    def test_search_by_title(self):
        src = FakeSrc([_b("Dracula"), _b("Frankenstein")])
        results = list(src.search_by_title("Dracula"))
        self.assertEqual(len(results), 1)

    def test_search_by_author_requires_last_name_match(self):
        src = FakeSrc([
            _b("X", author_last="Lovecraft", first="H. P."),
            _b("Y", author_last="Crane"),
        ])
        results = list(src.search_by_author("Lovecraft"))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "X")

    def test_search_by_author_full_name(self):
        src = FakeSrc([_b("X", author_last="Lovecraft", first="H. P.")])
        results = list(src.search_by_author("H. P. Lovecraft"))
        self.assertEqual(len(results), 1)

    def test_search_by_tag(self):
        src = FakeSrc([_b("X", tags=["Horror"]), _b("Y", tags=["Comedy"])])
        results = list(src.search_by_tag("Horror"))
        self.assertEqual(len(results), 1)

    def test_search_by_narrator(self):
        n = AudiobookNarrator(first_name="Frank", last_name="Muller")
        src = FakeSrc([_b("X", narrator=n), _b("Y")])
        results = list(src.search_by_narrator("Muller"))
        self.assertEqual(len(results), 1)

    def test_iterate_popular_default(self):
        src = FakeSrc([_b("A"), _b("B")])
        self.assertEqual(len(list(src.iterate_popular())), 2)

    def test_iterate_by_author(self):
        src = FakeSrc([
            _b("X", author_last="Lovecraft"),
            _b("Y", author_last="Crane"),
        ])
        self.assertEqual(len(list(src.iterate_by_author("Lovecraft"))), 1)

    def test_iterate_by_tag_exact_match(self):
        src = FakeSrc([_b("X", tags=["Horror"]), _b("Y", tags=["Comedy"])])
        self.assertEqual(len(list(src.iterate_by_tag("Horror"))), 1)

    def test_tag_stamps_source(self):
        src = FakeSrc([_b("X", tags=["Horror"])])
        results = list(src.search_by_tag("Horror"))
        self.assertEqual(results[0].source, "FakeSrc")

    def test_tag_does_not_overwrite_source(self):
        b = _b("X", tags=["Horror"])
        b.source = "Custom"
        src = FakeSrc([b])
        results = list(src.search_by_tag("Horror"))
        self.assertEqual(results[0].source, "Custom")

    def test_source_name_property(self):
        src = FakeSrc([])
        self.assertEqual(src.source_name, "FakeSrc")


if __name__ == "__main__":
    unittest.main()
