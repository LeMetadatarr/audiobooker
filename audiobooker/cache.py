"""Local file cache and download utilities for AudioBook streams.

Cache layout
------------
~/.cache/audiobooker/<book_hash>/
    meta.json          — serialised book metadata
    <filename>.mp3     — downloaded audio (one file per stream)

Usage
-----
    from audiobooker.cache import download, play, is_cached, cached_paths

    book = next(iter(Librivox().search_by_title("Dracula")))

    download(book)               # fetch all streams → cache
    download(book, stream=0)     # first stream only

    play(book)                   # download if needed, then open with system player
    play(book, stream=0)

    if is_cached(book):
        paths = cached_paths(book)

CLI
---
    python -m audiobooker.cache download "Dracula" --source librivox
    python -m audiobooker.cache play "Dracula"
    python -m audiobooker.cache info "Dracula"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path
from typing import List, Optional

import requests

from audiobooker.base import AudioBook, AudiobookNarrator, BookAuthor
from audiobooker.index import BookIndex
from audiobooker.scrappers.librivox import Librivox

_DEFAULT_CACHE = Path("~/.cache/audiobooker").expanduser()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _book_dir(book, cache_root: Path) -> Path:
    return cache_root / book.stable_id()


def _stream_filename(url: str, index: int) -> str:
    parsed = urllib.parse.urlparse(url)
    name = Path(parsed.path).name
    if not name or "." not in name:
        name = "stream.mp3"
    return f"{index:02d}_{name}"


def _meta_path(book_dir: Path) -> Path:
    return book_dir / "meta.json"


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def _book_to_meta(book) -> dict:
    return {
        "title":       book.title,
        "description": book.description,
        "image":       book.image,
        "language":    book.language,
        "year":        book.year,
        "runtime":     book.runtime,
        "source":      book.source,
        "streams":     book.streams,
        "tags":        book.tags,
        "authors":     [{"first_name": a.first_name, "last_name": a.last_name}
                        for a in book.authors],
        "narrator":    ({"first_name": book.narrator.first_name,
                         "last_name":  book.narrator.last_name}
                        if book.narrator else None),
    }


def _meta_to_book(meta: dict):
    narrator = None
    if meta.get("narrator"):
        narrator = AudiobookNarrator(**meta["narrator"])
    return AudioBook(
        title=meta["title"],
        description=meta.get("description", ""),
        image=meta.get("image", ""),
        language=meta.get("language", ""),
        year=meta.get("year", 0),
        runtime=meta.get("runtime", 0),
        source=meta.get("source", ""),
        streams=meta.get("streams", []),
        tags=meta.get("tags", []),
        authors=[BookAuthor(**a) for a in meta.get("authors", [])],
        narrator=narrator,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_cached(book, cache_root: Optional[Path] = None) -> bool:
    """Return True if at least one stream file exists in the cache."""
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    book_dir = _book_dir(book, root)
    if not book_dir.exists():
        return False
    return any(
        (book_dir / _stream_filename(url, i)).exists()
        for i, url in enumerate(book.streams)
    )


def cached_paths(book, cache_root: Optional[Path] = None) -> List[Path]:
    """Return paths to all cached stream files (only those that exist)."""
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    book_dir = _book_dir(book, root)
    return [
        p for p in (
            book_dir / _stream_filename(url, i)
            for i, url in enumerate(book.streams)
        )
        if p.exists()
    ]


def download(book, stream: Optional[int] = None,
             cache_root: Optional[Path] = None,
             progress: bool = True) -> List[Path]:
    """Download stream(s) to cache and return local file paths.

    Parameters
    ----------
    book:
        AudioBook to download.
    stream:
        Index into ``book.streams``. When ``None`` all streams are downloaded.
    cache_root:
        Override the default ``~/.cache/audiobooker`` directory.
    progress:
        Print download progress to stdout.

    Returns
    -------
    List of paths to the downloaded files.
    """
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    book_dir = _book_dir(book, root)
    book_dir.mkdir(parents=True, exist_ok=True)

    # Write metadata so the cache dir is self-describing
    meta_file = _meta_path(book_dir)
    if not meta_file.exists():
        meta_file.write_text(json.dumps(_book_to_meta(book), indent=2,
                                        ensure_ascii=False))

    urls = book.streams if stream is None else [book.streams[stream]]
    base_index = 0 if stream is None else stream

    downloaded = []
    for i, url in enumerate(urls):
        idx = base_index + i
        dest = book_dir / _stream_filename(url, idx)
        if dest.exists():
            if progress:
                print(f"  [cache] {dest.name}")
            downloaded.append(dest)
            continue

        if progress:
            print(f"  [download] {url}")

        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            tmp = dest.with_suffix(".part")
            written = 0
            with tmp.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    written += len(chunk)
                    if progress and total:
                        pct = written * 100 // total
                        print(f"\r    {pct:3d}%  {written // 1024}KB / {total // 1024}KB",
                              end="", flush=True)
            if progress and total:
                print()
            tmp.rename(dest)
            downloaded.append(dest)
        except Exception as exc:
            if progress:
                print(f"  [error] {exc}")
            tmp = dest.with_suffix(".part")
            if tmp.exists():
                tmp.unlink()

    return downloaded


def play(book, stream: int = 0,
         cache_root: Optional[Path] = None,
         progress: bool = True) -> None:
    """Play a book stream, downloading to cache first if needed.

    Uses the system's default audio player (``xdg-open`` on Linux,
    ``open`` on macOS, ``start`` on Windows).

    Parameters
    ----------
    book:
        AudioBook to play.
    stream:
        Index of the stream to play (default 0).
    cache_root:
        Override cache directory.
    progress:
        Show download progress.
    """
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    book_dir = _book_dir(book, root)
    dest = book_dir / _stream_filename(book.streams[stream], stream)

    if not dest.exists():
        paths = download(book, stream=stream, cache_root=root, progress=progress)
        if not paths:
            raise RuntimeError(f"Download failed for {book.title!r}")
        dest = paths[0]

    _open_file(dest)


def clear_cache(book=None, cache_root: Optional[Path] = None) -> int:
    """Remove cached files.

    Parameters
    ----------
    book:
        Remove only this book's cache. When ``None``, clears the entire cache.

    Returns
    -------
    Number of directories removed.
    """
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    if book is not None:
        d = _book_dir(book, root)
        if d.exists():
            shutil.rmtree(d)
            return 1
        return 0
    if root.exists():
        count = sum(1 for _ in root.iterdir())
        shutil.rmtree(root)
        return count
    return 0


def list_cached(cache_root: Optional[Path] = None):
    """Yield AudioBook objects for every book in the cache."""
    root = Path(cache_root) if cache_root else _DEFAULT_CACHE
    if not root.exists():
        return
    for book_dir in sorted(root.iterdir()):
        meta_file = _meta_path(book_dir)
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
                yield _meta_to_book(meta)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_file(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform == "win32":
        os.startfile(str(path))
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ---------------------------------------------------------------------------
# CLI  (python -m audiobooker.cache)
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="python -m audiobooker.cache",
        description="Download and play audiobooks with local caching.",
    )
    parser.add_argument("--cache", default=None, help="Cache directory")
    sub = parser.add_subparsers(dest="cmd")

    p_dl = sub.add_parser("download", help="Download book streams to cache")
    p_dl.add_argument("query")
    p_dl.add_argument("--source", default=None,
                      help="Limit search to this source name")
    p_dl.add_argument("--stream", type=int, default=None,
                      help="Stream index (default: all)")
    p_dl.add_argument("--method", default="search_by_title",
                      choices=["search_by_title", "search_by_author",
                               "search", "search_by_tag"])

    p_play = sub.add_parser("play", help="Play a book (download if not cached)")
    p_play.add_argument("query")
    p_play.add_argument("--source", default=None)
    p_play.add_argument("--stream", type=int, default=0)
    p_play.add_argument("--method", default="search_by_title",
                        choices=["search_by_title", "search_by_author",
                                 "search", "search_by_tag"])

    p_info = sub.add_parser("info", help="Show cache info for a book")
    p_info.add_argument("query")
    p_info.add_argument("--source", default=None)
    p_info.add_argument("--method", default="search_by_title",
                        choices=["search_by_title", "search_by_author",
                                 "search", "search_by_tag"])

    sub.add_parser("list", help="List all cached books")
    sub.add_parser("clear", help="Clear the entire cache")

    args = parser.parse_args()
    cache_root = Path(args.cache) if args.cache else None

    if args.cmd == "list":
        books = list(list_cached(cache_root))
        if not books:
            print("Cache is empty.")
        for b in books:
            paths = cached_paths(b, cache_root)
            size = sum(p.stat().st_size for p in paths if p.exists())
            print(f"  {b.title!r}  [{b.source}]  {size // 1024}KB  {len(paths)} file(s)")
        return

    if args.cmd == "clear":
        n = clear_cache(cache_root=cache_root)
        print(f"Cleared {n} cached book(s).")
        return

    # Commands that need a book lookup
    book = _find_book(args.query, args.method, getattr(args, "source", None))
    if book is None:
        print(f"No results for {args.query!r}")
        sys.exit(1)

    if args.cmd == "download":
        paths = download(book, stream=args.stream, cache_root=cache_root)
        print(f"\nDownloaded {len(paths)} file(s):")
        for p in paths:
            print(f"  {p}")

    elif args.cmd == "play":
        play(book, stream=args.stream, cache_root=cache_root)
        print(f"Playing: {book.title!r}")

    elif args.cmd == "info":
        paths = cached_paths(book, cache_root)
        print(f"Title:   {book.title}")
        print(f"Source:  {book.source}")
        print(f"Cached:  {is_cached(book, cache_root)}")
        print(f"Streams: {len(book.streams)}")
        root = cache_root or _DEFAULT_CACHE
        book_dir = _book_dir(book, root)
        for i, url in enumerate(book.streams):
            local = book_dir / _stream_filename(url, i)
            status = f"{local.stat().st_size // 1024}KB" if local.exists() else "not cached"
            print(f"  [{i}] {url}  →  {status}")
    else:
        parser.print_help()


def _find_book(query: str, method: str, source_filter: Optional[str] = None):
    """Search the local index first, fall back to live Librivox search."""
    try:
        idx = BookIndex()
        fn = getattr(idx, method)
        kw = {"max_results": 1}
        if source_filter:
            kw["source"] = source_filter
        results = fn(query, **kw)
        idx.close()
        if results:
            return results[0]
    except Exception:
        pass

    src = Librivox()
    fn = getattr(src, method, src.search_by_title)
    for book in fn(query):
        if source_filter and book.source != source_filter:
            continue
        return book
    return None


if __name__ == "__main__":
    main()
