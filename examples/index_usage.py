"""Local index — build once, search instantly without network.

Run this script once to build the index, then use it for offline search.
The index is stored in ~/.audiobooker/index.db by default.

Build time estimates (single-threaded, cold cache):
  AudioAnarchy    ~1s      (~11 books)
  LoyalBooks      ~2 min   (~3 500 books)
  DarkerProjects  ~2 min   (~244 books)
  GoldenAudioBooks ~30 min  (~6 500 books)
  Librivox        ~60 min  (~18 000 books, REST-paged)
"""
import time
from audiobooker.index import BookIndex
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker.scrappers.darkerprojects import DarkerProjects
from audiobooker import search

# ---------------------------------------------------------------------------
# 1. Build index from fast/small sources for this demo
# ---------------------------------------------------------------------------
idx = BookIndex()  # ~/.audiobooker/index.db

print("=== Building index (AudioAnarchy + DarkerProjects) ===\n")
idx.build(sources=[AudioAnarchy(), DarkerProjects()])
print()

# ---------------------------------------------------------------------------
# 2. Stats
# ---------------------------------------------------------------------------
s = idx.stats()
print(f"=== Index stats: {s['total']} books ===")
for src, n in s["by_source"].items():
    print(f"  {src}: {n}")
print()

# ---------------------------------------------------------------------------
# 3. Offline search — no network after build
# ---------------------------------------------------------------------------
print('=== search("drama") — offline, instant ===\n')
t0 = time.monotonic()
for book in idx.search("drama", max_results=5):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  [{book.score:.2f}] {book.title!r}")
    print(f"         source={book.source}  tags={book.tags}")
print(f"\nDone in {time.monotonic() - t0:.3f}s\n")

# ---------------------------------------------------------------------------
# 4. IndexedSource as drop-in for unified search()
# ---------------------------------------------------------------------------
print('=== search("anarchy", sources=[idx.as_source()]) ===\n')
t0 = time.monotonic()
for book in search("anarchy", sources=[idx.as_source()], timeout=5):
    print(f"  [{book.score:.2f}] {book.title!r}  tags={book.tags}")
print(f"\nDone in {time.monotonic() - t0:.3f}s\n")

# ---------------------------------------------------------------------------
# 5. Update — only add new books (skips existing by title+author hash)
# ---------------------------------------------------------------------------
print("=== update() — adds only new books ===\n")
added = idx.update(sources=[AudioAnarchy()])
print(f"  {added} new books added\n")

idx.close()

# ---------------------------------------------------------------------------
# 6. CLI reminder
# ---------------------------------------------------------------------------
print("CLI usage:")
print("  python -m audiobooker.index build")
print("  python -m audiobooker.index build --sources librivox loyalbooks")
print("  python -m audiobooker.index update")
print("  python -m audiobooker.index stats")
print('  python -m audiobooker.index search "Lovecraft"')
print('  python -m audiobooker.index search "Conan" --method search_by_title --n 5')
