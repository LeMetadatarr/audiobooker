"""09 — Advanced index usage: build, search, IndexedSource, follow YouTube.

Builds a small index from AudioAnarchy (fast, ~11 books) then demonstrates
all search methods, IndexedSource drop-in, and YouTube follow.

Requires: pip install audiobooker
Run:      python examples/09_advanced_index.py
"""
from audiobooker.index import BookIndex, IndexedSource
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker import search

DB_PATH = "/tmp/audiobooker_demo.db"

# Build index from one small source
print("Building index from AudioAnarchy...")
with BookIndex(DB_PATH) as idx:
    total = idx.build(sources=[AudioAnarchy()])
    print(f"Indexed {total} books.\n")

    stats = idx.stats()
    print(f"Stats: {stats}\n")

    # Search
    print("=== search_by_tag('Anarchy') ===")
    for book in idx.search_by_tag("Anarchy", max_results=5):
        print(f"  [{book.score:.2f}] {book.title!r}")

    # Typo tolerance (FTS misses → rapidfuzz fallback)
    print("\n=== search_by_title with typo ===")
    for book in idx.search_by_title("anrchy", max_results=3):
        print(f"  [{book.score:.2f}] {book.title!r}")

    # IndexedSource — drop-in for unified search()
    print("\n=== IndexedSource in unified search() ===")
    source = idx.as_source()
    for book in search("radio drama", sources=[source], timeout=5):
        print(f"  [{book.score:.2f}] {book.title!r} [{book.source}]")

    # Follow a YouTube channel (no actual indexing — just registering)
    print("\n=== follow / list_followed ===")
    idx.follow(
        "https://www.youtube.com/@HorrorBabble/videos",
        kind="channel",
        name="HorrorBabble",
        tags=["Horror"],
        language="en",
        min_runtime=300,
        title_blacklist=["compilation"],
    )
    for f in idx.list_followed():
        print(f"  {f['kind']} — {f['name']} ({f['language']})")

    idx.unfollow("https://www.youtube.com/@HorrorBabble/videos")
    print("Unfollowed.")

print(f"\nDatabase at: {DB_PATH}")
