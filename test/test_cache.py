"""Tests for audiobooker.cache and BookIndex duration filters."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.cache import (
    is_cached, cached_paths, download, clear_cache, list_cached,
    _book_dir, _stream_filename, _book_to_meta, _meta_to_book,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _book(title="Test Book", streams=None, runtime=3600):
    return AudioBook(
        title=title,
        authors=[BookAuthor(first_name="Test", last_name="Author")],
        streams=streams or ["http://example.com/test.mp3"],
        runtime=runtime,
        source="TestSource",
    )


BOOK = _book()


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

class TestPathHelpers(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def test_book_dir_uses_hash(self):
        d = _book_dir(BOOK, self.root)
        self.assertEqual(d.parent, self.root)
        self.assertEqual(d.name, str(hash(BOOK)))

    def test_stream_filename_from_url(self):
        name = _stream_filename("http://example.com/audio.mp3", 0)
        self.assertEqual(name, "audio.mp3")

    def test_stream_filename_fallback(self):
        name = _stream_filename("http://example.com/stream", 2)
        self.assertEqual(name, "stream_2.mp3")


# ---------------------------------------------------------------------------
# Serialisation round-trip
# ---------------------------------------------------------------------------

class TestSerialisation(unittest.TestCase):

    def test_meta_roundtrip(self):
        meta = _book_to_meta(BOOK)
        book2 = _meta_to_book(meta)
        self.assertEqual(book2.title, BOOK.title)
        self.assertEqual(book2.streams, BOOK.streams)
        self.assertEqual(book2.authors[0].last_name, "Author")

    def test_meta_roundtrip_with_narrator(self):
        from audiobooker.base import AudiobookNarrator
        book = _book()
        book.narrator = AudiobookNarrator(first_name="Wayne", last_name="June")
        meta = _book_to_meta(book)
        book2 = _meta_to_book(meta)
        self.assertEqual(book2.narrator.last_name, "June")


# ---------------------------------------------------------------------------
# is_cached / cached_paths
# ---------------------------------------------------------------------------

class TestCacheStatus(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def test_not_cached_initially(self):
        self.assertFalse(is_cached(BOOK, self.root))

    def test_cached_after_file_created(self):
        d = _book_dir(BOOK, self.root)
        d.mkdir(parents=True)
        (d / "test.mp3").write_bytes(b"fake")
        self.assertTrue(is_cached(BOOK, self.root))

    def test_cached_paths_returns_existing(self):
        d = _book_dir(BOOK, self.root)
        d.mkdir(parents=True)
        (d / "test.mp3").write_bytes(b"fake")
        paths = cached_paths(BOOK, self.root)
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].exists())

    def test_cached_paths_empty_when_nothing_downloaded(self):
        paths = cached_paths(BOOK, self.root)
        self.assertEqual(paths, [])


# ---------------------------------------------------------------------------
# download() — mocked HTTP
# ---------------------------------------------------------------------------

class TestDownload(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    def _mock_response(self, content=b"audio data"):
        resp = MagicMock()
        resp.headers = {"content-length": str(len(content))}
        resp.iter_content.return_value = [content]
        resp.raise_for_status = MagicMock()
        return resp

    @patch("requests.get")
    def test_download_creates_file(self, mock_get):
        mock_get.return_value = self._mock_response()
        paths = download(BOOK, cache_root=self.root, progress=False)
        self.assertEqual(len(paths), 1)
        self.assertTrue(paths[0].exists())
        self.assertEqual(paths[0].read_bytes(), b"audio data")

    @patch("requests.get")
    def test_download_writes_meta(self, mock_get):
        mock_get.return_value = self._mock_response()
        download(BOOK, cache_root=self.root, progress=False)
        meta_file = _book_dir(BOOK, self.root) / "meta.json"
        self.assertTrue(meta_file.exists())

    @patch("requests.get")
    def test_download_skips_existing(self, mock_get):
        mock_get.return_value = self._mock_response()
        download(BOOK, cache_root=self.root, progress=False)
        download(BOOK, cache_root=self.root, progress=False)
        # Should only have been called once
        self.assertEqual(mock_get.call_count, 1)

    @patch("requests.get")
    def test_download_stream_index(self, mock_get):
        book = _book(streams=[
            "http://example.com/part1.mp3",
            "http://example.com/part2.mp3",
        ])
        mock_get.return_value = self._mock_response()
        paths = download(book, stream=1, cache_root=self.root, progress=False)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].name, "part2.mp3")

    @patch("requests.get")
    def test_download_http_error_returns_empty(self, mock_get):
        import requests as req
        mock_get.return_value.raise_for_status.side_effect = req.HTTPError("404")
        mock_get.return_value.iter_content.return_value = []
        # Should not raise — returns empty list
        paths = download(BOOK, cache_root=self.root, progress=False)
        self.assertEqual(paths, [])


# ---------------------------------------------------------------------------
# clear_cache / list_cached
# ---------------------------------------------------------------------------

class TestClearList(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

    @patch("requests.get")
    def test_clear_single_book(self, mock_get):
        resp = MagicMock()
        resp.headers = {}
        resp.iter_content.return_value = [b"x"]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp
        download(BOOK, cache_root=self.root, progress=False)
        self.assertTrue(is_cached(BOOK, self.root))
        clear_cache(BOOK, self.root)
        self.assertFalse(is_cached(BOOK, self.root))

    @patch("requests.get")
    def test_list_cached(self, mock_get):
        resp = MagicMock()
        resp.headers = {}
        resp.iter_content.return_value = [b"x"]
        resp.raise_for_status = MagicMock()
        mock_get.return_value = resp
        download(BOOK, cache_root=self.root, progress=False)
        books = list(list_cached(self.root))
        self.assertEqual(len(books), 1)
        self.assertEqual(books[0].title, BOOK.title)


# ---------------------------------------------------------------------------
# BookIndex duration filters
# ---------------------------------------------------------------------------

class TestDurationFilter(unittest.TestCase):

    def setUp(self):
        import tempfile
        from audiobooker.index import BookIndex

        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.idx = BookIndex(tmp.name)

        from audiobooker.base import BookAuthor

        def make(title, runtime):
            return AudioBook(
                title=title,
                authors=[BookAuthor(first_name="A", last_name="B")],
                runtime=runtime,
                streams=["http://example.com/x.mp3"],
                source="Test",
            )

        books = [
            make("Short Story", 600),       # 10 min
            make("Medium Novel", 7200),     # 2 h
            make("Epic Saga", 36000),       # 10 h
        ]
        for b in books:
            self.idx._upsert(b)
        self.idx._con.commit()
        self.idx._fts_rebuild()

    def tearDown(self):
        self.idx.close()

    def test_min_duration_filters_short(self):
        results = self.idx.search_by_title("story", min_score=0.0,
                                           max_results=0, min_duration=3600)
        self.assertFalse(any(b.title == "Short Story" for b in results))

    def test_max_duration_filters_long(self):
        results = self.idx.search_by_title("saga", min_score=0.0,
                                           max_results=0, max_duration=10000)
        self.assertFalse(any(b.title == "Epic Saga" for b in results))

    def test_duration_range(self):
        results = self.idx.search("novel", min_score=0.0, max_results=0,
                                  min_duration=3600, max_duration=10000)
        titles = {b.title for b in results}
        self.assertIn("Medium Novel", titles)
        self.assertNotIn("Short Story", titles)
        self.assertNotIn("Epic Saga", titles)

    def test_no_duration_filter_returns_all(self):
        results = self.idx.search_by_author("B", min_score=0.0, max_results=0)
        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main()
