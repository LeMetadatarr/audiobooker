"""04 — Download streams to local cache.

Cache layout: ~/.cache/audiobooker/<book_hash>/<index>_<filename>

Requires: pip install audiobooker
Run:      python examples/04_download_and_cache.py
"""
from audiobooker.scrappers.librivox import Librivox
from audiobooker.cache import download, is_cached, cached_paths

# Find a short book to keep download time reasonable
book = None
for candidate in Librivox().search_by_tag("short works"):
    if candidate.streams and 0 < candidate.runtime < 3600:
        book = candidate
        break

if book is None:
    print("No suitable short book found.")
else:
    print(f"Book: {book.title!r}  runtime={book.runtime // 60}min  streams={len(book.streams)}")

    if is_cached(book):
        print("Already cached:")
        for p in cached_paths(book):
            print(f"  {p}")
    else:
        print("Downloading stream 0 only...")
        paths = download(book, stream=0)
        print(f"Downloaded to: {paths[0] if paths else '(failed)'}")
