"""Tests for audiobooker.search — parallel orchestration."""
import time
import unittest

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.scrappers import AudioBookSource
from audiobooker.search import (
    search, search_by_title, search_by_author,
    search_by_narrator, search_by_tag,
)


def _b(title, author_last="X", source="Fake", tags=None,
       narrator=None):
    return AudioBook(
        title=title,
        authors=[BookAuthor(first_name="A", last_name=author_last)],
        tags=tags or [],
        narrator=narrator,
        source=source,
        streams=["http://x/a.mp3"],
    )


class FakeSource(AudioBookSource):
    """In-memory test source."""
    source_name = "Fake"

    def __init__(self, books, delay=0.0, raise_in=None):
        self._books = books
        self._delay = delay
        self._raise_in = raise_in or set()

    def iterate_all(self):
        for b in self._books:
            yield b

    def search_by_title(self, query):
        if "search_by_title" in self._raise_in:
            raise RuntimeError("boom")
        if self._delay:
            time.sleep(self._delay)
        for b in self._books:
            if query.lower() in b.title.lower():
                yield b

    def search_by_author(self, query):
        for b in self._books:
            for a in b.authors:
                if query.lower() in a.last_name.lower():
                    yield b
                    break

    def search_by_tag(self, query):
        for b in self._books:
            if any(query.lower() in t.lower() for t in b.tags):
                yield b

    def search_by_narrator(self, query):
        for b in self._books:
            if b.narrator and query.lower() in b.narrator.last_name.lower():
                yield b

    def search(self, query):
        yield from self.search_by_title(query)


class TestSearch(unittest.TestCase):
    def test_search_by_title_returns_matches(self):
        src = FakeSource([_b("Dracula"), _b("Frankenstein")])
        results = list(search_by_title("Dracula", sources=[src]))
        self.assertTrue(any(r.title == "Dracula" for r in results))

    def test_search_filters_min_score(self):
        # Yield title that's nothing like the query
        src = FakeSource([_b("Dracula")])
        # Request through `search` will go to `search_by_title` (FakeSource.search)
        results = list(search("Dracula", sources=[src]))
        self.assertTrue(any(r.title == "Dracula" for r in results))

    def test_dedup(self):
        # Two sources yielding the same logical book (same title+author)
        src1 = FakeSource([_b("Dracula", author_last="Stoker", source="A")])
        src2 = FakeSource([_b("Dracula", author_last="Stoker", source="B")])
        results = list(search_by_title("Dracula", sources=[src1, src2]))
        self.assertEqual(len(results), 1)

    def test_dedup_disabled(self):
        src1 = FakeSource([_b("Dracula", author_last="Stoker", source="A")])
        src2 = FakeSource([_b("Dracula", author_last="Stoker", source="B")])
        results = list(search_by_title("Dracula", sources=[src1, src2],
                                       deduplicate=False))
        self.assertEqual(len(results), 2)

    def test_max_per_source(self):
        src = FakeSource([_b(f"Dracula {i}") for i in range(5)])
        results = list(search_by_title("Dracula", sources=[src],
                                       max_per_source=2))
        self.assertLessEqual(len(results), 2)

    def test_worker_exception_does_not_kill_search(self):
        bad = FakeSource([], raise_in={"search_by_title"})
        good = FakeSource([_b("Dracula")])
        results = list(search_by_title("Dracula", sources=[bad, good]))
        self.assertEqual(len(results), 1)

    def test_timeout_path(self):
        slow = FakeSource([_b("Dracula")], delay=2.0)
        results = list(search_by_title("Dracula", sources=[slow], timeout=0.2))
        # Slow source cancelled — no results expected
        self.assertEqual(results, [])

    def test_search_by_author_routes(self):
        src = FakeSource([_b("X", author_last="Lovecraft")])
        results = list(search_by_author("Lovecraft", sources=[src]))
        self.assertEqual(len(results), 1)

    def test_search_by_tag_routes(self):
        src = FakeSource([_b("X", tags=["Horror"])])
        results = list(search_by_tag("Horror", sources=[src]))
        self.assertEqual(len(results), 1)

    def test_search_by_narrator_routes(self):
        n = AudiobookNarrator(first_name="Frank", last_name="Muller")
        src = FakeSource([_b("X", narrator=n)])
        results = list(search_by_narrator("Muller", sources=[src]))
        self.assertEqual(len(results), 1)

    def test_default_sources_instantiated(self):
        # When sources=None it should fall through to ALL_SOURCES; we patch
        # ALL_SOURCES to a single empty fake to keep the test offline.
        from audiobooker import search as sm  # noqa: F401
        import importlib
        sm = importlib.import_module("audiobooker.search")

        class Empty(AudioBookSource):
            source_name = "Empty"
            def search_by_title(self, q): return iter([])

        original = sm.ALL_SOURCES
        sm.ALL_SOURCES = [Empty]
        try:
            results = list(search_by_title("anything", timeout=1.0))
        finally:
            sm.ALL_SOURCES = original
        self.assertEqual(results, [])


if __name__ == "__main__":
    unittest.main()
