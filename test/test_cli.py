"""Tests for audiobooker.cli (Click command surface)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from audiobooker.base import AudioBook, AudiobookNarrator, BookAuthor
from audiobooker.cli import cli, _print_book, _find_book


def _book(title="Test Book", **kwargs):
    defaults = dict(
        title=title,
        authors=[BookAuthor(first_name="Test", last_name="Author")],
        streams=["http://example.com/test.mp3"],
        runtime=3600,
        source="TestSource",
    )
    defaults.update(kwargs)
    return AudioBook(**defaults)


class TestPrintBook(unittest.TestCase):
    def test_basic(self):
        from click.testing import CliRunner

        @ __import__("click").command()
        def show():
            _print_book(_book(), verbose=False)

        result = CliRunner().invoke(show)
        self.assertIn("Test Book", result.output)
        self.assertIn("TestSource", result.output)

    def test_verbose(self):
        import click

        @click.command()
        def show():
            b = _book(
                tags=["horror", "classic"],
                narrator=AudiobookNarrator(first_name="Wayne", last_name="June"),
                streams=["http://x/a.mp3", "http://x/b.mp3", "http://x/c.mp3"],
            )
            b.score = 0.85
            _print_book(b, verbose=True)

        result = CliRunner().invoke(show)
        self.assertIn("tags:", result.output)
        self.assertIn("narrator:", result.output)
        self.assertIn("streams:", result.output)
        self.assertIn("0.85", result.output)


class TestRoot(unittest.TestCase):
    def test_help(self):
        result = CliRunner().invoke(cli, ["--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("audiobooker", result.output)

    def test_version(self):
        result = CliRunner().invoke(cli, ["--version"])
        self.assertEqual(result.exit_code, 0)


class TestSearchCmd(unittest.TestCase):
    def test_no_results(self):
        with patch("audiobooker.search", return_value=iter([])):
            result = CliRunner().invoke(cli, ["search", "xyzzy"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No results", result.output)

    def test_with_results(self):
        b = _book("Dracula")
        b.score = 0.9
        with patch("audiobooker.search", return_value=iter([b])):
            result = CliRunner().invoke(cli, ["search", "dracula", "-v"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Dracula", result.output)

    def test_filters_drop_results(self):
        b1 = _book("X", language="en", runtime=600)
        b2 = _book("Y", language="de", runtime=10)
        b1.score = b2.score = 0.9
        with patch("audiobooker.search", return_value=iter([b1, b2])):
            result = CliRunner().invoke(cli, [
                "search", "any",
                "--language", "en",
                "--min-duration", "100",
                "--max-duration", "1000",
                "--source", "TestSource",
            ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("X", result.output)
        self.assertNotIn("Y", result.output)


class TestIndexCmds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db = self.tmp.name

    def tearDown(self):
        Path(self.db).unlink(missing_ok=True)

    def test_stats_empty(self):
        result = CliRunner().invoke(cli, ["index", "--db", self.db, "stats"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Total books: 0", result.output)

    def test_build(self):
        src = MagicMock()
        src.iterate_all.return_value = iter([_book("Built")])
        src.__class__.__name__ = "FakeSrc"
        with patch("audiobooker.index._default_sources", return_value=[src]):
            result = CliRunner().invoke(cli, ["index", "--db", self.db, "build"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("books indexed", result.output)

    def test_update(self):
        src = MagicMock()
        src.iterate_all.return_value = iter([_book("Up")])
        src.__class__.__name__ = "FakeSrc"
        with patch("audiobooker.index._default_sources", return_value=[src]), \
             patch("audiobooker.index.BookIndex._followed_as_sources", return_value=[]):
            result = CliRunner().invoke(cli, ["index", "--db", self.db, "update"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("new books added", result.output)

    def test_build_with_named_sources(self):
        # Resolve real source class but mock its iterate_all
        with patch("audiobooker.scrappers.librivox.Librivox.iterate_all",
                   return_value=iter([])):
            result = CliRunner().invoke(cli, [
                "index", "--db", self.db, "build", "-s", "librivox",
            ])
        self.assertEqual(result.exit_code, 0)

    def test_search_no_results(self):
        result = CliRunner().invoke(cli, [
            "index", "--db", self.db, "search", "anything",
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No results", result.output)

    def test_search_with_results(self):
        from audiobooker.index import BookIndex
        idx = BookIndex(self.db)
        idx._upsert(_book("Dracula", authors=[BookAuthor(last_name="Stoker")]))
        idx._con.commit()
        idx._fts_rebuild()
        idx.close()
        result = CliRunner().invoke(cli, [
            "index", "--db", self.db, "search", "dracula",
            "-v",
        ])
        self.assertEqual(result.exit_code, 0, msg=result.output)
        self.assertIn("Dracula", result.output)
        # Now test with all filters
        result = CliRunner().invoke(cli, [
            "index", "--db", self.db, "search", "dracula",
            "--source", "TestSource", "--language", "en",
            "--min-duration", "1", "--max-duration", "100000",
        ])
        self.assertEqual(result.exit_code, 0, msg=result.output)

    def test_follow_unfollow_list(self):
        url = "https://www.youtube.com/@Test/videos"
        result = CliRunner().invoke(cli, [
            "index", "--db", self.db, "follow", url,
            "--name", "TestCh", "--tags", "horror",
            "--blacklist", "trailer",
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Following", result.output)

        result = CliRunner().invoke(cli, ["index", "--db", self.db, "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("TestCh", result.output)

        result = CliRunner().invoke(cli, ["index", "--db", self.db, "unfollow", url])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Unfollowed", result.output)

        # Unfollow nonexistent
        result = CliRunner().invoke(cli, ["index", "--db", self.db, "unfollow", url])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Not found", result.output)

        # Empty list
        result = CliRunner().invoke(cli, ["index", "--db", self.db, "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("No followed sources", result.output)


class TestFindBook(unittest.TestCase):
    def test_returns_index_hit(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as t:
            db = t.name
        from audiobooker.index import BookIndex
        idx = BookIndex(db)
        idx._upsert(_book("Findme", authors=[BookAuthor(last_name="Smith")]))
        idx._con.commit()
        idx._fts_rebuild()
        idx.close()
        try:
            book = _find_book("findme", "search_by_title", db, None)
            self.assertIsNotNone(book)
        finally:
            Path(db).unlink(missing_ok=True)

    def test_falls_back_to_librivox(self):
        with patch("audiobooker.cli._open_index", side_effect=Exception("nope")), \
             patch("audiobooker.scrappers.librivox.Librivox.search_by_title",
                   return_value=iter([_book("Live", source="Librivox")])):
            book = _find_book("live", "search_by_title", None, None)
            self.assertEqual(book.title, "Live")

    def test_source_filter_skips_mismatch(self):
        with patch("audiobooker.cli._open_index", side_effect=Exception("nope")), \
             patch("audiobooker.scrappers.librivox.Librivox.search_by_title",
                   return_value=iter([_book("L", source="Other"),
                                      _book("L2", source="Librivox")])):
            book = _find_book("l", "search_by_title", None, "Librivox")
            self.assertEqual(book.source, "Librivox")

    def test_returns_none_when_no_results(self):
        with patch("audiobooker.cli._open_index", side_effect=Exception("nope")), \
             patch("audiobooker.scrappers.librivox.Librivox.search_by_title",
                   return_value=iter([])):
            book = _find_book("nothing", "search_by_title", None, None)
            self.assertIsNone(book)


class TestCacheCmds(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_list_empty(self):
        result = CliRunner().invoke(cli, ["cache", "--cache-dir", self.tmp, "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cache is empty", result.output)

    def test_list_with_books(self):
        # Pre-populate cache with a meta + dummy file
        from audiobooker.cache import _book_dir, _book_to_meta
        b = _book("Cached")
        bdir = _book_dir(b, Path(self.tmp))
        bdir.mkdir(parents=True)
        (bdir / "meta.json").write_text(json.dumps(_book_to_meta(b)))
        (bdir / "00_test.mp3").write_bytes(b"\x00" * 2048)
        result = CliRunner().invoke(cli, ["cache", "--cache-dir", self.tmp, "list"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cached", result.output)

    def test_clear_all(self):
        Path(self.tmp, "x").mkdir()
        result = CliRunner().invoke(cli, [
            "cache", "--cache-dir", self.tmp, "clear", "--yes",
        ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cleared", result.output)

    def test_download_no_book(self):
        with patch("audiobooker.cli._find_book", return_value=None):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "download", "missing",
            ])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("No results", result.output)

    def test_download_success(self):
        b = _book("DLed")
        with patch("audiobooker.cli._find_book", return_value=b), \
             patch("audiobooker.cli.download",
                   return_value=[Path(self.tmp) / "f.mp3"]):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "download", "x",
            ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Downloaded", result.output)

    def test_download_fail(self):
        b = _book("DLfail")
        with patch("audiobooker.cli._find_book", return_value=b), \
             patch("audiobooker.cli.download", return_value=[]):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "download", "x",
            ])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("failed", result.output)

    def test_play_no_book(self):
        with patch("audiobooker.cli._find_book", return_value=None):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "play", "missing",
            ])
        self.assertEqual(result.exit_code, 1)

    def test_play_success(self):
        b = _book("Play")
        with patch("audiobooker.cli._find_book", return_value=b), \
             patch("audiobooker.cli.play"):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "play", "x",
            ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Playing", result.output)

    def test_info_no_book(self):
        with patch("audiobooker.cli._find_book", return_value=None):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "info", "missing",
            ])
        self.assertEqual(result.exit_code, 1)

    def test_info_success(self):
        b = _book("Info")
        with patch("audiobooker.cli._find_book", return_value=b):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "info", "x",
            ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Title:", result.output)
        self.assertIn("not cached", result.output)

    def test_clear_one_book(self):
        b = _book("Single")
        # Pre-cache it
        from audiobooker.cache import _book_dir
        bdir = _book_dir(b, Path(self.tmp))
        bdir.mkdir(parents=True)
        (bdir / "00_test.mp3").write_bytes(b"x")
        with patch("audiobooker.cli._find_book", return_value=b):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "clear", "x", "--yes",
            ])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Cleared", result.output)

    def test_clear_one_book_not_found(self):
        with patch("audiobooker.cli._find_book", return_value=None):
            result = CliRunner().invoke(cli, [
                "cache", "--cache-dir", self.tmp, "clear", "x", "--yes",
            ])
        self.assertEqual(result.exit_code, 1)


if __name__ == "__main__":
    unittest.main()
