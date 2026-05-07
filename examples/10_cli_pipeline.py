"""10 — Shell-callable search → download pipeline.

Demonstrates how to drive audiobooker from Python as a scripted pipeline:
  1. Search all sources for a query.
  2. Pick the top result.
  3. Download to cache.
  4. Print the local path.

Can be run directly or called from a shell script.

Requires: pip install audiobooker
Run:      python examples/10_cli_pipeline.py "The Time Machine"
          python examples/10_cli_pipeline.py "Lovecraft" --author --stream 0
"""
import argparse
import sys

from audiobooker import search, search_by_author, search_by_tag
from audiobooker.cache import download, is_cached, cached_paths


def main():
    parser = argparse.ArgumentParser(description="Search → download pipeline")
    parser.add_argument("query")
    parser.add_argument("--author", action="store_true", help="Search by author")
    parser.add_argument("--tag", action="store_true", help="Search by tag")
    parser.add_argument("--stream", type=int, default=None,
                        help="Stream index to download (default: all)")
    parser.add_argument("--source", default=None, help="Limit to one source name")
    parser.add_argument("-n", type=int, default=5, help="Max results to consider")
    args = parser.parse_args()

    if args.author:
        results = list(search_by_author(args.query, max_per_source=args.n, timeout=30))
    elif args.tag:
        results = list(search_by_tag(args.query, max_per_source=args.n, timeout=30))
    else:
        results = list(search(args.query, max_per_source=args.n, timeout=30))

    if args.source:
        results = [b for b in results if b.source == args.source]

    if not results:
        print(f"No results for {args.query!r}", file=sys.stderr)
        sys.exit(1)

    book = results[0]
    print(f"Selected: [{book.score:.2f}] [{book.source}] {book.title!r}")

    if not book.streams:
        print("No streams available.", file=sys.stderr)
        sys.exit(1)

    if is_cached(book):
        paths = cached_paths(book)
        print(f"Already cached ({len(paths)} file(s)):")
    else:
        print(f"Downloading {len(book.streams) if args.stream is None else 1} stream(s)...")
        paths = download(book, stream=args.stream)
        print(f"Downloaded {len(paths)} file(s):")

    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
