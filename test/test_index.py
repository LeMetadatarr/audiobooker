"""Tests for audiobooker.index — BookIndex and IndexedSource."""
import tempfile
import unittest
from pathlib import Path

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.index import BookIndex, IndexedSource, _fts_query


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _book(title, authors=None, tags=None, narrator=None,
          source="TestSource", language="en", year=0, runtime=0):
    return AudioBook(
        title=title,
        authors=authors or [],
        tags=tags or [],
        narrator=narrator,
        source=source,
        language=language,
        year=year,
        runtime=runtime,
        streams=["http://example.com/book.mp3"],
    )


LOVECRAFT = _book(
    "The Call of Cthulhu",
    authors=[BookAuthor(first_name="H. P.", last_name="Lovecraft")],
    tags=["Horror", "Weird Fiction"],
    narrator=AudiobookNarrator(first_name="Wayne", last_name="June"),
    year=1926, runtime=3600,
)
DOYLE = _book(
    "The Hound of the Baskervilles",
    authors=[BookAuthor(first_name="Arthur Conan", last_name="Doyle")],
    tags=["Mystery", "Detective"],
    year=1902, runtime=7200,
)
DICKENS = _book(
    "A Tale of Two Cities",
    authors=[BookAuthor(first_name="Charles", last_name="Dickens")],
    tags=["Historical Fiction", "Classic"],
    year=1859, runtime=54000,
)
KING = _book(
    "The Shining",
    authors=[BookAuthor(first_name="Stephen", last_name="King")],
    tags=["Horror", "Thriller"],
    narrator=AudiobookNarrator(first_name="Campbell", last_name="Scott"),
    year=1977, runtime=14400,
    source="StephenKingAudioBooks",
)
TOLKIEN = _book(
    "The Fellowship of the Ring",
    authors=[BookAuthor(first_name="J.R.R.", last_name="Tolkien")],
    tags=["Fantasy", "Epic"],
    year=1954, runtime=28800,
)
GERMAN_BOOK = _book(
    "Faust",
    authors=[BookAuthor(first_name="Johann Wolfgang von", last_name="Goethe")],
    tags=["Classic", "Drama"],
    language="de", year=1808,
)

ALL_BOOKS = [LOVECRAFT, DOYLE, DICKENS, KING, TOLKIEN, GERMAN_BOOK]


def _make_index(books=None) -> BookIndex:
    """Create a temporary in-memory index pre-populated with test books."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    idx = BookIndex(tmp.name)
    for book in (books or ALL_BOOKS):
        idx._upsert(book)
    idx._con.commit()
    idx._fts_rebuild()
    return idx


# ---------------------------------------------------------------------------
# FTS query builder
# ---------------------------------------------------------------------------

class TestFtsQuery(unittest.TestCase):

    def test_single_word_prefix(self):
        q = _fts_query("love")
        self.assertIn('"love"*', q)

    def test_multi_word_or(self):
        q = _fts_query("sherlock holmes")
        self.assertIn('"sherlock"*', q)
        self.assertIn('"holmes"*', q)
        self.assertIn(" OR ", q)

    def test_field_restriction(self):
        q = _fts_query("horror", field="tags_text")
        self.assertTrue(q.startswith("tags_text:"))

    def test_strips_punctuation(self):
        q = _fts_query("lovecraft,")
        self.assertIn('"lovecraft"*', q)
        self.assertNotIn(",", q)

    def test_empty_query(self):
        q = _fts_query("")
        self.assertEqual(q, '""')


# ---------------------------------------------------------------------------
# BookIndex — building
# ---------------------------------------------------------------------------

class TestBookIndexBuild(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_len(self):
        self.assertEqual(len(self.idx), len(ALL_BOOKS))

    def test_stats_total(self):
        s = self.idx.stats()
        self.assertEqual(s["total"], len(ALL_BOOKS))

    def test_stats_by_source(self):
        s = self.idx.stats()
        self.assertIn("TestSource", s["by_source"])
        self.assertIn("StephenKingAudioBooks", s["by_source"])

    def test_stats_by_language(self):
        s = self.idx.stats()
        self.assertIn("en", s["by_language"])
        self.assertIn("de", s["by_language"])

    def test_iterate_all(self):
        books = list(self.idx.iterate_all())
        self.assertEqual(len(books), len(ALL_BOOKS))

    def test_iterate_all_source_filter(self):
        books = list(self.idx.iterate_all(source="StephenKingAudioBooks"))
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "The Shining")

    def test_iterate_all_language_filter(self):
        books = list(self.idx.iterate_all(language="de"))
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "Faust")

    def test_roundtrip_fields(self):
        books = {b.title: b for b in self.idx.iterate_all()}
        b = books["The Call of Cthulhu"]
        self.assertEqual(b.authors[0].last_name, "Lovecraft")
        self.assertEqual(b.narrator.last_name, "June")
        self.assertEqual(b.year, 1926)
        self.assertEqual(b.runtime, 3600)
        self.assertEqual(b.language, "en")
        self.assertEqual(b.tags, ["Horror", "Weird Fiction"])
        self.assertEqual(b.streams, ["http://example.com/book.mp3"])

    def test_build_clears_source(self):
        """build() for a source replaces its existing records."""
        new_book = _book("New Book", source="TestSource")
        self.idx._upsert(new_book)
        self.idx._con.commit()
        self.idx._fts_rebuild()
        # build with a fake source that yields only one book
        class _FakeSource:
            __class__ = type("TestSource", (), {"__name__": "TestSource"})()
            def iterate_all(self_):
                yield LOVECRAFT
        self.idx.build(sources=[_FakeSource()], progress=False)
        books = list(self.idx.iterate_all(source="TestSource"))
        self.assertEqual(len(books), 1)

    def test_context_manager(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        with BookIndex(tmp.name) as idx:
            idx._upsert(LOVECRAFT)
            idx._con.commit()
            idx._fts_rebuild()
            self.assertEqual(len(idx), 1)


# ---------------------------------------------------------------------------
# BookIndex — update / deduplication
# ---------------------------------------------------------------------------

class TestBookIndexUpdate(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index([LOVECRAFT, DOYLE])

    def tearDown(self):
        self.idx.close()

    def test_update_adds_new(self):
        class _Src:
            __class__ = type("TestSource", (), {"__name__": "TestSource"})()
            def iterate_all(self_):
                yield DICKENS
        added = self.idx.update(sources=[_Src()], progress=False)
        self.assertEqual(added, 1)
        self.assertEqual(len(self.idx), 3)

    def test_update_skips_existing(self):
        class _Src:
            __class__ = type("TestSource", (), {"__name__": "TestSource"})()
            def iterate_all(self_):
                yield LOVECRAFT   # already present
                yield DICKENS     # new
        added = self.idx.update(sources=[_Src()], progress=False)
        self.assertEqual(added, 1)

    def test_duplicate_hash_not_double_inserted(self):
        self.idx._upsert(LOVECRAFT)  # same hash — INSERT OR REPLACE
        self.idx._con.commit()
        self.idx._fts_rebuild()
        self.assertEqual(len(self.idx), 2)  # still 2, not 3


# ---------------------------------------------------------------------------
# BookIndex — search_by_title
# ---------------------------------------------------------------------------

class TestSearchByTitle(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_exact_match(self):
        results = self.idx.search_by_title("The Shining")
        self.assertTrue(any(b.title == "The Shining" for b in results))

    def test_partial_word(self):
        results = self.idx.search_by_title("Cthulhu")
        self.assertTrue(any("Cthulhu" in b.title for b in results))

    def test_scores_sorted(self):
        results = self.idx.search_by_title("The Shining")
        scores = [b.score for b in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_max_results(self):
        results = self.idx.search_by_title("the", max_results=2)
        self.assertLessEqual(len(results), 2)

    def test_min_score_filters(self):
        results = self.idx.search_by_title("xyz_no_match", min_score=0.45)
        self.assertEqual(results, [])

    def test_typo_fallback(self):
        # "Shinng" — FTS won't match prefix, should fall back to rapidfuzz
        results = self.idx.search_by_title("The Shinng", min_score=0.5)
        self.assertTrue(any("Shining" in b.title for b in results))

    def test_source_filter(self):
        results = self.idx.search_by_title("The Shining",
                                           source="StephenKingAudioBooks")
        self.assertTrue(all(b.source == "StephenKingAudioBooks" for b in results))

    def test_language_filter_excludes(self):
        results = self.idx.search_by_title("Faust", language="en")
        self.assertFalse(any(b.title == "Faust" for b in results))

    def test_language_filter_includes(self):
        results = self.idx.search_by_title("Faust", language="de",
                                           min_score=0.5)
        self.assertTrue(any(b.title == "Faust" for b in results))


# ---------------------------------------------------------------------------
# BookIndex — search_by_author
# ---------------------------------------------------------------------------

class TestSearchByAuthor(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_last_name(self):
        results = self.idx.search_by_author("Lovecraft")
        self.assertTrue(any("Lovecraft" in b.title or
                            any(a.last_name == "Lovecraft" for a in b.authors)
                            for b in results))

    def test_full_name(self):
        results = self.idx.search_by_author("Arthur Conan Doyle")
        self.assertTrue(any(b.title == "The Hound of the Baskervilles"
                            for b in results))

    def test_no_cross_contamination(self):
        # search_by_author scores on author only — should not match on title
        results = self.idx.search_by_author("Cthulhu", min_score=0.8)
        # "Cthulhu" is in the title, not any author — should not score well
        self.assertFalse(any("Cthulhu" in b.title and
                             not any("Cthulhu" in a.last_name for a in b.authors)
                             for b in results))


# ---------------------------------------------------------------------------
# BookIndex — search_by_tag
# ---------------------------------------------------------------------------

class TestSearchByTag(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_exact_tag(self):
        results = self.idx.search_by_tag("Horror")
        titles = {b.title for b in results}
        self.assertIn("The Call of Cthulhu", titles)
        self.assertIn("The Shining", titles)

    def test_partial_tag(self):
        results = self.idx.search_by_tag("Myste")
        self.assertTrue(any(b.title == "The Hound of the Baskervilles"
                            for b in results))

    def test_no_match(self):
        results = self.idx.search_by_tag("Zombies", min_score=0.9)
        self.assertEqual(results, [])


# ---------------------------------------------------------------------------
# BookIndex — search_by_narrator
# ---------------------------------------------------------------------------

class TestSearchByNarrator(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_finds_narrator(self):
        results = self.idx.search_by_narrator("Wayne June")
        self.assertTrue(any(b.title == "The Call of Cthulhu" for b in results))

    def test_last_name_only(self):
        results = self.idx.search_by_narrator("June")
        self.assertTrue(any(b.title == "The Call of Cthulhu" for b in results))

    def test_no_narrator_books_excluded(self):
        # Books without a narrator should never appear regardless of min_score
        results = self.idx.search_by_narrator("Wayne", min_score=0.0)
        for b in results:
            self.assertIsNotNone(b.narrator)


# ---------------------------------------------------------------------------
# BookIndex — general search
# ---------------------------------------------------------------------------

class TestSearch(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()

    def tearDown(self):
        self.idx.close()

    def test_scores_all_fields(self):
        # "Lovecraft" matches via author and title — high enough for general search
        results = self.idx.search("Lovecraft")
        self.assertTrue(len(results) > 0)

    def test_returns_sorted(self):
        results = self.idx.search("Lovecraft")
        scores = [b.score for b in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_min_score_default(self):
        for b in self.idx.search("anything"):
            self.assertGreaterEqual(b.score, 0.45)


# ---------------------------------------------------------------------------
# IndexedSource
# ---------------------------------------------------------------------------

class TestIndexedSource(unittest.TestCase):

    def setUp(self):
        self.idx = _make_index()
        self.src = self.idx.as_source()

    def tearDown(self):
        self.idx.close()

    def test_iterate_all(self):
        books = list(self.src.iterate_all())
        self.assertEqual(len(books), len(ALL_BOOKS))

    def test_search_by_title(self):
        results = list(self.src.search_by_title("Shining"))
        self.assertTrue(any(b.title == "The Shining" for b in results))

    def test_search_by_author(self):
        results = list(self.src.search_by_author("Dickens"))
        self.assertTrue(any(b.title == "A Tale of Two Cities" for b in results))

    def test_search_by_tag(self):
        results = list(self.src.search_by_tag("Fantasy"))
        self.assertTrue(any(b.title == "The Fellowship of the Ring"
                            for b in results))

    def test_search_by_narrator(self):
        results = list(self.src.search_by_narrator("Campbell Scott"))
        self.assertTrue(any(b.title == "The Shining" for b in results))

    def test_source_filter(self):
        filtered = IndexedSource(self.idx, source_filter="StephenKingAudioBooks")
        books = list(filtered.iterate_all())
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "The Shining")

    def test_language_filter(self):
        de_src = IndexedSource(self.idx, language_filter="de")
        books = list(de_src.iterate_all())
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, "Faust")

    def test_iterate_by_author(self):
        results = list(self.src.iterate_by_author("Doyle"))
        self.assertTrue(any(b.title == "The Hound of the Baskervilles"
                            for b in results))

    def test_iterate_by_tag(self):
        results = list(self.src.iterate_by_tag("Mystery"))
        self.assertTrue(any(b.title == "The Hound of the Baskervilles"
                            for b in results))

    def test_repr(self):
        self.assertIn("IndexedSource", repr(self.src))
        self.assertIn("BookIndex", repr(self.src))


if __name__ == "__main__":
    unittest.main()
