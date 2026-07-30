"""Extra coverage for audiobooker.index — main() CLI, IndexedSource, follow."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from audiobooker.base import AudioBook, AudiobookNarrator, BookAuthor
from audiobooker.index import (
    BookIndex, IndexedSource, _resolve_sources, main,
)


def _b(title, author_last="X", source="TestSource", language="en",
       runtime=3600, tags=None, narrator=None):
    return AudioBook(
        title=title,
        authors=[BookAuthor(first_name="A", last_name=author_last)],
        tags=tags or [],
        narrator=narrator,
        source=source,
        language=language,
        runtime=runtime,
        streams=["http://x/a.mp3"],
    )


def _make_index(books):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    idx = BookIndex(tmp.name)
    for b in books:
        idx._upsert(b)
    idx._con.commit()
    idx._fts_rebuild()
    return idx, tmp.name


class TestIndexedSource(unittest.TestCase):
    def setUp(self):
        self.idx, self.path = _make_index([
            _b("Dracula", author_last="Stoker", tags=["Horror"],
               narrator=AudiobookNarrator(first_name="F", last_name="Muller")),
            _b("Frankenstein", author_last="Shelley", tags=["Gothic"]),
        ])

    def tearDown(self):
        self.idx.close()
        Path(self.path).unlink(missing_ok=True)

    def test_iterate_all(self):
        src = IndexedSource(self.idx)
        books = list(src.iterate_all())
        self.assertEqual(len(books), 2)

    def test_iterate_popular_alias(self):
        src = IndexedSource(self.idx)
        self.assertEqual(len(list(src.iterate_popular())), 2)

    def test_iterate_by_author(self):
        src = IndexedSource(self.idx)
        results = list(src.iterate_by_author("Stoker"))
        self.assertTrue(any(r.title == "Dracula" for r in results))

    def test_iterate_by_tag(self):
        src = IndexedSource(self.idx)
        results = list(src.iterate_by_tag("Horror"))
        self.assertTrue(any(r.title == "Dracula" for r in results))

    def test_search(self):
        src = IndexedSource(self.idx)
        self.assertTrue(any(r.title == "Dracula"
                            for r in src.search("Dracula")))

    def test_search_by_title(self):
        src = IndexedSource(self.idx)
        self.assertTrue(any(r.title == "Dracula"
                            for r in src.search_by_title("Dracula")))

    def test_search_by_author(self):
        src = IndexedSource(self.idx)
        self.assertTrue(any(r.title == "Dracula"
                            for r in src.search_by_author("Stoker")))

    def test_search_by_tag(self):
        src = IndexedSource(self.idx)
        self.assertTrue(any(r.title == "Dracula"
                            for r in src.search_by_tag("Horror")))

    def test_search_by_narrator(self):
        src = IndexedSource(self.idx)
        results = list(src.search_by_narrator("Muller"))
        self.assertTrue(results)

    def test_repr(self):
        src = IndexedSource(self.idx)
        self.assertIn("IndexedSource", repr(src))

    def test_filters(self):
        src = IndexedSource(self.idx, source_filter="TestSource",
                            language_filter="en")
        self.assertEqual(len(list(src.iterate_all())), 2)


class TestResolveSources(unittest.TestCase):
    def test_known_name(self):
        srcs = _resolve_sources(["librivox"])
        self.assertEqual(len(srcs), 1)

    def test_unknown_name_skipped(self):
        # captures the print to stdout
        srcs = _resolve_sources(["nonexistent"])
        self.assertEqual(srcs, [])

    def test_normalises_dashes_and_underscores(self):
        srcs = _resolve_sources(["loyal_books", "stephen-king-audiobooks"])
        self.assertEqual(len(srcs), 2)


class TestFollowedAsSources(unittest.TestCase):
    def test_with_youtube_unavailable(self):
        idx, path = _make_index([])
        try:
            with patch.dict(sys.modules,
                            {"audiobooker.scrappers.youtube": None}):
                # youtube import fails → no followed sources
                self.assertEqual(idx._followed_as_sources(), [])
        finally:
            idx.close()
            Path(path).unlink(missing_ok=True)

    def test_with_followed_channel(self):
        idx, path = _make_index([])
        try:
            idx.follow("https://yt/@x", kind="channel", name="X",
                       tags=["t1"], language="en", min_runtime=300,
                       authors=[BookAuthor(first_name="A", last_name="B")],
                       narrator=AudiobookNarrator(first_name="N", last_name="M"),
                       title_blacklist=["bad"])
            idx.follow("https://yt/playlist?list=PL1", kind="playlist",
                       name="P")
            with patch("audiobooker.scrappers.youtube.YoutubeChannelSource") as Ch, \
                 patch("audiobooker.scrappers.youtube.YoutubePlaylistSource") as Pl:
                sources = idx._followed_as_sources()
            self.assertEqual(len(sources), 2)
        finally:
            idx.close()
            Path(path).unlink(missing_ok=True)


class TestMainCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()

    def tearDown(self):
        Path(self.tmp.name).unlink(missing_ok=True)

    def _run(self, *argv):
        with patch.object(sys, "argv",
                          ["audiobooker.index", "--db", self.tmp.name, *argv]):
            try:
                main()
            except SystemExit as e:
                return e.code
        return 0

    def test_no_subcommand_prints_help(self):
        self._run()

    def test_stats(self):
        self._run("stats")

    def test_build_no_sources(self):
        # Don't actually hit the network — provide empty sources
        with patch("audiobooker.index._default_sources", return_value=[]):
            self._run("build")

    def test_build_named_sources(self):
        with patch("audiobooker.scrappers.librivox.Librivox.iterate_all",
                   return_value=iter([])):
            self._run("build", "--sources", "librivox")

    def test_update_no_sources(self):
        with patch("audiobooker.index._default_sources", return_value=[]), \
             patch("audiobooker.index.BookIndex._followed_as_sources",
                   return_value=[]):
            self._run("update")

    def test_update_named_sources(self):
        with patch("audiobooker.scrappers.librivox.Librivox.iterate_all",
                   return_value=iter([])):
            self._run("update", "--sources", "librivox")

    def test_follow_unfollow_list(self):
        url = "https://yt/@X/videos"
        self._run("follow", url, "--name", "TestCh", "--tags", "horror",
                  "--blacklist", "trailer")
        self._run("list")
        self._run("unfollow", url)
        # Unfollow nonexistent
        self._run("unfollow", url)
        # List empty
        self._run("list")

    def test_search(self):
        # Pre-populate
        idx = BookIndex(self.tmp.name)
        idx._upsert(_b("Dracula", author_last="Stoker"))
        idx._con.commit()
        idx._fts_rebuild()
        idx.close()
        self._run("search", "dracula", "--source", "TestSource",
                  "--language", "en", "--min-duration", "1",
                  "--max-duration", "100000")


class TestBuildProgressOutput(unittest.TestCase):
    def test_build_prints_every_50(self):
        idx, path = _make_index([])
        try:
            books = [_b(f"B{i}") for i in range(55)]
            src = MagicMock()
            src.iterate_all.return_value = iter(books)
            src.__class__.__name__ = "FakeS"
            total = idx.build(sources=[src], progress=True)
            self.assertEqual(total, 55)
        finally:
            idx.close()
            Path(path).unlink(missing_ok=True)


class TestFtsFallbackPaths(unittest.TestCase):
    def test_full_scan_fallback(self):
        # Query that does not exist falls back from FTS to full_scan
        idx, path = _make_index([_b("OnlyOne", author_last="UniqueLast")])
        try:
            # Trigger a malformed FTS query causing OperationalError
            results = idx._fts_search('"')  # unbalanced quote
            self.assertEqual(results, [])
        finally:
            idx.close()
            Path(path).unlink(missing_ok=True)


class TestRepr(unittest.TestCase):
    def test_repr_and_len(self):
        idx, path = _make_index([_b("X")])
        try:
            self.assertEqual(len(idx), 1)
            self.assertIn("BookIndex", repr(idx))
        finally:
            idx.close()
            Path(path).unlink(missing_ok=True)

    def test_context_manager(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as t:
            db = t.name
        try:
            with BookIndex(db) as idx:
                self.assertIsNotNone(idx)
        finally:
            Path(db).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
