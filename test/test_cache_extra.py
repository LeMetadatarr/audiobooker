"""Extra coverage for audiobooker.cache — download, play, main()."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.cache import (
    download, play, clear_cache, list_cached, _open_file,
    _book_dir, _stream_filename, _book_to_meta, main, _find_book,
)


def _book(title="Test Book", streams=None):
    return AudioBook(
        title=title,
        authors=[BookAuthor(first_name="Test", last_name="Author")],
        streams=streams or ["http://example.com/test.mp3"],
        runtime=3600,
        source="TestSource",
    )


class TestDownload(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_download_skips_existing(self):
        b = _book(streams=["http://x/a.mp3"])
        bdir = _book_dir(b, self.tmp)
        bdir.mkdir(parents=True)
        existing = bdir / _stream_filename("http://x/a.mp3", 0)
        existing.write_bytes(b"old")
        paths = download(b, cache_root=self.tmp)
        self.assertEqual(paths, [existing])

    def test_download_with_progress_and_content_length(self):
        b = _book(streams=["http://x/a.mp3"])
        resp = MagicMock()
        resp.headers = {"content-length": "10"}
        resp.iter_content.return_value = [b"hello", b"world"]
        resp.raise_for_status.return_value = None
        with patch("audiobooker.cache.requests.get", return_value=resp):
            paths = download(b, cache_root=self.tmp, progress=True)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0].read_bytes(), b"helloworld")

    def test_download_without_progress(self):
        b = _book(streams=["http://x/a.mp3"])
        resp = MagicMock()
        resp.headers = {}
        resp.iter_content.return_value = [b"data"]
        resp.raise_for_status.return_value = None
        with patch("audiobooker.cache.requests.get", return_value=resp):
            paths = download(b, cache_root=self.tmp, progress=False)
        self.assertEqual(len(paths), 1)

    def test_download_handles_failure(self):
        b = _book(streams=["http://x/a.mp3"])
        with patch("audiobooker.cache.requests.get",
                   side_effect=Exception("boom")):
            paths = download(b, cache_root=self.tmp, progress=True)
        self.assertEqual(paths, [])

    def test_download_cleans_partial_on_failure(self):
        b = _book(streams=["http://x/a.mp3"])
        bdir = _book_dir(b, self.tmp)
        bdir.mkdir(parents=True)
        # Pre-create a .part file so the cleanup branch executes
        dest = bdir / _stream_filename("http://x/a.mp3", 0)
        tmp_file = dest.with_suffix(".part")
        tmp_file.write_bytes(b"oops")
        with patch("audiobooker.cache.requests.get",
                   side_effect=Exception("boom")):
            download(b, cache_root=self.tmp)
        self.assertFalse(tmp_file.exists())

    def test_download_specific_stream_index(self):
        b = _book(streams=["http://x/a.mp3", "http://x/b.mp3"])
        resp = MagicMock()
        resp.headers = {}
        resp.iter_content.return_value = [b"x"]
        resp.raise_for_status.return_value = None
        with patch("audiobooker.cache.requests.get", return_value=resp):
            paths = download(b, stream=1, cache_root=self.tmp, progress=False)
        self.assertEqual(len(paths), 1)
        self.assertIn("01_b.mp3", paths[0].name)


class TestPlay(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def test_play_existing_file(self):
        b = _book(streams=["http://x/a.mp3"])
        bdir = _book_dir(b, self.tmp)
        bdir.mkdir(parents=True)
        dest = bdir / _stream_filename("http://x/a.mp3", 0)
        dest.write_bytes(b"audio")
        with patch("audiobooker.cache._open_file") as op:
            play(b, cache_root=self.tmp, progress=False)
        op.assert_called_once_with(dest)

    def test_play_downloads_first(self):
        b = _book(streams=["http://x/a.mp3"])
        with patch("audiobooker.cache.download",
                   return_value=[Path(self.tmp) / "fake.mp3"]) as d, \
             patch("audiobooker.cache._open_file"):
            play(b, cache_root=self.tmp, progress=False)
        d.assert_called_once()

    def test_play_raises_when_download_fails(self):
        b = _book(streams=["http://x/a.mp3"])
        with patch("audiobooker.cache.download", return_value=[]):
            with self.assertRaises(RuntimeError):
                play(b, cache_root=self.tmp, progress=False)


class TestOpenFile(unittest.TestCase):
    def test_open_file_linux(self):
        with patch("audiobooker.cache.sys.platform", "linux"), \
             patch("audiobooker.cache.subprocess.Popen") as p:
            _open_file(Path("/tmp/x"))
        p.assert_called_once()
        self.assertEqual(p.call_args[0][0][0], "xdg-open")

    def test_open_file_darwin(self):
        with patch("audiobooker.cache.sys.platform", "darwin"), \
             patch("audiobooker.cache.subprocess.Popen") as p:
            _open_file(Path("/tmp/x"))
        self.assertEqual(p.call_args[0][0][0], "open")

    def test_open_file_windows(self):
        # os.startfile is Windows-only; patch attribute presence
        with patch("audiobooker.cache.sys.platform", "win32"), \
             patch("audiobooker.cache.os") as os_mod:
            _open_file(Path("/tmp/x"))
        os_mod.startfile.assert_called_once()


class TestClearList(unittest.TestCase):
    def test_clear_book_not_present(self):
        tmp = Path(tempfile.mkdtemp())
        b = _book("Gone")
        # Book dir doesn't exist
        self.assertEqual(clear_cache(b, tmp), 0)

    def test_clear_no_root(self):
        # Nonexistent root
        tmp = Path(tempfile.mkdtemp())
        # Remove the dir
        import shutil
        shutil.rmtree(tmp)
        self.assertEqual(clear_cache(cache_root=tmp), 0)

    def test_list_cached_skips_corrupt_meta(self):
        tmp = Path(tempfile.mkdtemp())
        b = _book("Bad")
        bdir = _book_dir(b, tmp)
        bdir.mkdir(parents=True)
        (bdir / "meta.json").write_text("{not valid json")
        self.assertEqual(list(list_cached(tmp)), [])

    def test_list_cached_no_root(self):
        tmp = Path(tempfile.mkdtemp())
        import shutil
        shutil.rmtree(tmp)
        self.assertEqual(list(list_cached(tmp)), [])


class TestFindBookCacheModule(unittest.TestCase):
    def test_returns_index_hit(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        from audiobooker.index import BookIndex
        with patch("audiobooker.cache.BookIndex",
                   side_effect=lambda *a, **k: BookIndex(tmp.name)):
            idx = BookIndex(tmp.name)
            idx._upsert(_book("Found"))
            idx._con.commit()
            idx._fts_rebuild()
            idx.close()
            book = _find_book("found", "search_by_title")
            self.assertIsNotNone(book)
        Path(tmp.name).unlink(missing_ok=True)

    def test_falls_back_to_librivox(self):
        with patch("audiobooker.cache.BookIndex", side_effect=Exception("nope")), \
             patch("audiobooker.cache.Librivox") as Lv:
            inst = Lv.return_value
            inst.search_by_title.return_value = iter([_book("Live", streams=[])])
            book = _find_book("live", "search_by_title")
            self.assertIsNotNone(book)

    def test_source_filter_skips_mismatch(self):
        b1 = _book("L"); b1.source = "Other"
        b2 = _book("L"); b2.source = "Librivox"
        with patch("audiobooker.cache.BookIndex", side_effect=Exception()), \
             patch("audiobooker.cache.Librivox") as Lv:
            Lv.return_value.search_by_title.return_value = iter([b1, b2])
            book = _find_book("l", "search_by_title", "Librivox")
            self.assertEqual(book.source, "Librivox")

    def test_returns_none(self):
        with patch("audiobooker.cache.BookIndex", side_effect=Exception()), \
             patch("audiobooker.cache.Librivox") as Lv:
            Lv.return_value.search_by_title.return_value = iter([])
            self.assertIsNone(_find_book("nothing", "search_by_title"))


class TestCacheMain(unittest.TestCase):
    """Coverage for the argparse main() of audiobooker.cache."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _run(self, *argv):
        with patch.object(sys, "argv", ["audiobooker.cache", *argv]):
            try:
                main()
            except SystemExit as e:
                return e.code
        return 0

    def test_list_empty(self):
        self._run("--cache", self.tmp, "list")

    def test_list_with_book(self):
        b = _book("Cached")
        bdir = _book_dir(b, Path(self.tmp))
        bdir.mkdir(parents=True)
        (bdir / "meta.json").write_text(json.dumps(_book_to_meta(b)))
        (bdir / "00_test.mp3").write_bytes(b"x" * 2048)
        self._run("--cache", self.tmp, "list")

    def test_clear(self):
        Path(self.tmp, "x").mkdir()
        self._run("--cache", self.tmp, "clear")

    def test_download_no_book(self):
        with patch("audiobooker.cache._find_book", return_value=None):
            code = self._run("--cache", self.tmp, "download", "x")
        self.assertEqual(code, 1)

    def test_download_with_book(self):
        b = _book()
        with patch("audiobooker.cache._find_book", return_value=b), \
             patch("audiobooker.cache.download",
                   return_value=[Path(self.tmp) / "f.mp3"]):
            self._run("--cache", self.tmp, "download", "x")

    def test_play_with_book(self):
        b = _book()
        with patch("audiobooker.cache._find_book", return_value=b), \
             patch("audiobooker.cache.play"):
            self._run("--cache", self.tmp, "play", "x")

    def test_info_with_book(self):
        b = _book()
        bdir = _book_dir(b, Path(self.tmp))
        bdir.mkdir(parents=True)
        (bdir / _stream_filename(b.streams[0], 0)).write_bytes(b"x" * 1024)
        with patch("audiobooker.cache._find_book", return_value=b):
            self._run("--cache", self.tmp, "info", "x")


if __name__ == "__main__":
    unittest.main()
