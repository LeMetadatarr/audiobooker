"""Download all audiobooks from TheCybrarian to local cache.

TheCybrarian publishes Robert E. Howard audiobooks (Conan, Solomon Kane, Kull…)
on YouTube. This script iterates the channel, skips "update" announcement videos
(handled by title_blacklist on the source), downloads each stream to
~/.cache/audiobooker/, and skips files already present.

It also shows how to index the channel first and run the download from the index
so book metadata is preserved across runs.

Run:
  python examples/download_cybrarian.py
  python examples/download_cybrarian.py --dry-run    # list books without downloading
  python examples/download_cybrarian.py --indexed     # build index first, then download

Requirements:
  pip install audiobooker[youtube]
"""

import argparse
import sys
from pathlib import Path

from audiobooker.cache import download, is_cached, cached_paths, list_cached
from audiobooker.scrappers.youtube import TheCybrarian


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true",
                        help="List books without downloading")
    parser.add_argument("--indexed", action="store_true",
                        help="Index the channel first, then download from the index")
    parser.add_argument("--cache", default=None, metavar="DIR",
                        help="Cache directory (default ~/.cache/audiobooker)")
    parser.add_argument("--stream", type=int, default=0,
                        help="Stream index to download per book (default 0)")
    args = parser.parse_args()

    cache_root = Path(args.cache) if args.cache else None

    if args.indexed:
        books = _from_index()
    else:
        books = _from_channel()

    total = skipped = downloaded = errors = 0

    for book in books:
        total += 1
        if is_cached(book, cache_root):
            paths = cached_paths(book, cache_root)
            size_kb = sum(p.stat().st_size for p in paths) // 1024
            print(f"  [cached {size_kb}KB] {book.title!r}")
            skipped += 1
            continue

        if args.dry_run:
            runtime_min = book.runtime // 60
            print(f"  [would download] {book.title!r}  {runtime_min}min  {book.streams[0]}")
            continue

        print(f"  [downloading] {book.title!r}")
        paths = download(book, stream=args.stream, cache_root=cache_root, progress=True)
        if paths:
            size_kb = sum(p.stat().st_size for p in paths) // 1024
            print(f"    → {paths[0].name}  ({size_kb}KB)")
            downloaded += 1
        else:
            print(f"    → ERROR: download failed")
            errors += 1

    print()
    print(f"Total: {total}  |  Downloaded: {downloaded}  |  Already cached: {skipped}  |  Errors: {errors}")


def _from_channel():
    """Stream books directly from the YouTube channel."""
    print("=== Fetching TheCybrarian channel ===\n")
    return TheCybrarian().iterate_all()


def _from_index():
    """Build/update a local index, then iterate from it."""
    from audiobooker.index import BookIndex

    print("=== Indexing TheCybrarian channel ===\n")
    idx = BookIndex()
    added = idx.update(sources=[TheCybrarian()], progress=True)
    print(f"  {added} new books added to index\n")

    print("=== Downloading from index ===\n")
    books = list(idx.iterate_all(source="YoutubeChannelSource"))
    idx.close()
    return books


if __name__ == "__main__":
    main()
