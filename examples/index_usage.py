"""Local index — build once, search instantly without network.

The index is stored in ~/.audiobooker/index.db by default.

Build time estimates (single-threaded, cold HTTP cache):
  AudioAnarchy         ~1 s      (~11 books)
  DarkerProjects       ~2 min    (~244 books)
  LoyalBooks           ~2 min    (~3 500 books)
  StephenKingAudioBooks ~1 min   (~113 books)
  HPTalesAudioBooks    ~30 s     (~20 books)
  GoldenAudioBooks     ~30 min   (~6 500 books)
  Librivox             ~60 min   (~18 000 books, REST-paged)

Run:
  python examples/index_usage.py
  python -m audiobooker.index build --sources librivox loyalbooks
  python -m audiobooker.index search "Lovecraft" --method search_by_author
"""
import time
from audiobooker.index import BookIndex, IndexedSource
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker import search

# ---------------------------------------------------------------------------
# 1. Build index — small source so this demo runs fast
# ---------------------------------------------------------------------------
idx = BookIndex()   # ~/.audiobooker/index.db

print("=== Building index (AudioAnarchy) ===\n")
idx.build(sources=[AudioAnarchy()])
print()

# ---------------------------------------------------------------------------
# 2. Stats
# ---------------------------------------------------------------------------
s = idx.stats()
print(f"Total books: {s['total']}")
for src, n in s["by_source"].items():
    print(f"  {src}: {n}")
print()

# ---------------------------------------------------------------------------
# 3. Search methods — all run offline after build
# ---------------------------------------------------------------------------
def show(label, results, limit=3):
    print(f"{label}  ({len(results)} hit(s))")
    for b in results[:limit]:
        authors = ", ".join(f"{a.first_name} {a.last_name}".strip()
                            for a in b.authors)
        print(f"  [{b.score:.2f}] {b.title!r}  tags={b.tags}")
    print()

t0 = time.monotonic()
show('search_by_tag("radio")',    idx.search_by_tag("radio"))
show('search_by_tag("anarchy")', idx.search_by_tag("anarchy"))
show('search_by_title("introduction")', idx.search_by_title("introduction"))
show('search("democracy")',       idx.search("democracy"))
print(f"All searches completed in {(time.monotonic() - t0)*1000:.1f}ms\n")

# ---------------------------------------------------------------------------
# 4. Typo tolerance — FTS misses, rapidfuzz full-scan fallback kicks in
# ---------------------------------------------------------------------------
print("=== Typo tolerance ===\n")
t0 = time.monotonic()
results = idx.search_by_title("anarchi")   # typo
ms = (time.monotonic() - t0) * 1000
show(f'search_by_title("anarchi") [typo, {ms:.1f}ms]', results)

# ---------------------------------------------------------------------------
# 5. IndexedSource — drop-in for unified search()
# ---------------------------------------------------------------------------
print("=== IndexedSource in unified search() ===\n")
t0 = time.monotonic()
for book in search("anarchy", sources=[idx.as_source()], timeout=5):
    print(f"  [{book.score:.2f}] [{book.source}] {book.title!r}")
print(f"\nDone in {(time.monotonic() - t0)*1000:.1f}ms\n")

# ---------------------------------------------------------------------------
# 6. Source and language filters
# ---------------------------------------------------------------------------
print("=== Filtered IndexedSource ===\n")
audio_only = IndexedSource(idx, source_filter="AudioAnarchy")
en_only    = IndexedSource(idx, language_filter="en")
print(f"AudioAnarchy only: {sum(1 for _ in audio_only.iterate_all())} books")
print(f"English only:      {sum(1 for _ in en_only.iterate_all())} books\n")

# ---------------------------------------------------------------------------
# 7. Update — adds only new books, skips existing
# ---------------------------------------------------------------------------
print("=== update() — incremental, skips duplicates ===\n")
added = idx.update(sources=[AudioAnarchy()], progress=True)
print(f"\n{added} new books added (0 expected — already indexed)\n")

idx.close()

# ---------------------------------------------------------------------------
# 8. CLI quick-reference
# ---------------------------------------------------------------------------
print("CLI:")
print("  python -m audiobooker.index build")
print("  python -m audiobooker.index build --sources librivox loyalbooks")
print("  python -m audiobooker.index update --sources librivox")
print("  python -m audiobooker.index stats")
print('  python -m audiobooker.index search "Lovecraft" --method search_by_author')
print('  python -m audiobooker.index search "horror" --method search_by_tag --n 5')
print("  python -m audiobooker.index --db /data/books.db stats")
