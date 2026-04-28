# Local Index

`BookIndex` stores audiobook records in a local SQLite database so search
runs instantly without hitting any network after the initial build.

```bash
pip install audiobooker   # no extra dependencies — uses stdlib sqlite3
```

## When to use it

| Approach | Speed | Network | Freshness |
|---|---|---|---|
| `search()` (live) | slow for linear-scan sources | yes | always fresh |
| `BookIndex` (indexed) | instant | only during `build()` | stale until refreshed |

Use the index when:
- You query repeatedly (voice assistant, batch processing)
- You need offline operation
- You care about latency (first result in <1ms vs 10–30s)

Don't bother indexing Librivox for interactive use — its REST API is fast enough.

## Build

```python
from audiobooker.index import BookIndex

idx = BookIndex()                  # stored at ~/.audiobooker/index.db
idx.build()                        # iterate_all() on all 7 web sources
idx.build(sources=[Librivox()])    # specific sources only
```

Build times (single-threaded, cold HTTP cache):

| Source | Books | Time |
|---|---|---|
| AudioAnarchy | ~11 | ~1 s |
| DarkerProjects | ~244 | ~2 min |
| LoyalBooks | ~3 500 | ~2 min |
| GoldenAudioBooks | ~6 500 | ~30 min |
| StephenKingAudioBooks | ~113 | ~1 min |
| HPTalesAudioBooks | ~20 | ~30 s |
| Librivox | ~18 000 | ~60 min |

`build()` clears and repopulates records for the given sources. Use `update()`
to only add new books without clearing existing records.

## Update

```python
idx.update()                        # add new books from all sources
idx.update(sources=[Librivox()])    # specific sources only
```

`update()` uses `AudioBook.__hash__` (title + authors) as the uniqueness key —
existing books are skipped, new ones are inserted.

## Search

All search methods mirror the live `search*()` API and return results sorted
by `score` descending, filtered at `min_score=0.45`:

```python
idx.search("Lovecraft")
idx.search_by_title("Sherlock Holmes", max_results=5)
idx.search_by_author("Dickens")
idx.search_by_tag("horror")
idx.search_by_narrator("Frank Muller")
```

Optional filters on any search method:

```python
# Only books from Librivox
idx.search_by_tag("horror", source="Librivox")

# Only English books
idx.search_by_author("Lovecraft", language="en")
```

## IndexedSource — drop-in for unified search()

`idx.as_source()` returns an `IndexedSource` that implements the full
`AudioBookSource` interface and can be passed anywhere a source is accepted:

```python
from audiobooker import search
from audiobooker.index import BookIndex

idx = BookIndex()
for book in search("Lovecraft", sources=[idx.as_source()], timeout=5):
    print(f"[{book.score:.2f}] {book.title}")
```

Filter by source or language at the `IndexedSource` level:

```python
from audiobooker.index import IndexedSource

librivox_only = IndexedSource(idx, source_filter="Librivox")
english_only  = IndexedSource(idx, language_filter="en")
```

## Stats

```python
s = idx.stats()
# {'total': 28388, 'by_source': {'Librivox': 18012, ...}, 'by_language': {'en': 26400, ...}}
print(len(idx))   # total book count
```

## CLI

```bash
# Build full index (all sources)
python -m audiobooker.index build

# Build selected sources
python -m audiobooker.index build --sources librivox loyalbooks

# Add new books without clearing existing records
python -m audiobooker.index update

# Show stats
python -m audiobooker.index stats

# Search
python -m audiobooker.index search "Lovecraft"
python -m audiobooker.index search "Conan" --method search_by_title --n 5
python -m audiobooker.index search "horror" --method search_by_tag --source Librivox

# Custom database path
python -m audiobooker.index --db /data/books.db build
```

## Custom database path

```python
idx = BookIndex("/data/my_books.db")
```

Or as a context manager:

```python
with BookIndex() as idx:
    idx.build(sources=[AudioAnarchy()])
    for book in idx.search("anarchy"):
        print(book.title)
```

## YouTube sources and the index

YouTube channels change frequently (new uploads). They are excluded from the
default `build()` source list. You can index them explicitly, but `update()`
is better suited — run it periodically to pick up new videos:

```python
from audiobooker.scrappers.youtube import HorrorBabble, TheCybrarian

idx.update(sources=[HorrorBabble(), TheCybrarian()])
```
