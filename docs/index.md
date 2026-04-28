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
- You care about latency (first result in <20ms vs 10–30s)

## Search strategy

Two-phase: **FTS5 pre-filter → rapidfuzz re-rank**.

1. SQLite FTS5 tokenises the query into prefix terms (`"love"*`) and
   applies an OR across tokens. This runs in C against an inverted index
   and returns up to 500 candidates in microseconds.
2. rapidfuzz WRatio re-ranks the candidate shortlist with full fuzzy
   scoring including typo handling, token reordering, and containment bonuses.
3. If FTS returns fewer than 5 hits (e.g. a misspelled query), the search
   automatically falls back to a full rapidfuzz scan of all rows — so typos
   never produce zero results, they just take a bit longer (~50–100ms at 18k books).

Typical query latency: **~15ms** (FTS path) vs O(N·WRatio) without an index.

## Build

```python
from audiobooker.index import BookIndex

idx = BookIndex()                  # stored at ~/.audiobooker/index.db
idx.build()                        # iterate_all() on all 7 web sources
idx.build(sources=[Librivox()])    # specific sources only
```

`build()` clears and repopulates records for the given sources, then
rebuilds the FTS index. Use `update()` to only add new books.

Build times (single-threaded, cold HTTP cache):

| Source | Books | Time |
|---|---|---|
| AudioAnarchy | ~11 | ~1 s |
| HPTalesAudioBooks | ~20 | ~30 s |
| StephenKingAudioBooks | ~113 | ~1 min |
| DarkerProjects | ~244 | ~2 min |
| LoyalBooks | ~3 500 | ~2 min |
| GoldenAudioBooks | ~6 500 | ~30 min |
| Librivox | ~18 000 | ~60 min |

## Update

```python
idx.update()                        # add new books from all sources
idx.update(sources=[Librivox()])    # specific sources only
```

`update()` uses `AudioBook.__hash__` (title + authors) as the uniqueness key.
Existing books are skipped; new ones are inserted and the FTS index is
updated incrementally (no full rebuild needed).

## Search

All methods return results sorted by `score` descending, filtered at
`min_score=0.45`. Books without a narrator are automatically excluded from
`search_by_narrator`.

```python
idx.search("Lovecraft")                         # all fields, weighted
idx.search_by_title("Sherlock Holmes", max_results=5)
idx.search_by_author("Dickens")
idx.search_by_tag("Horror")
idx.search_by_narrator("Frank Muller")
```

### Scoring note

`search()` weights: title 55%, author 30%, tag 10%, narrator 5%. A single
genre word like "Horror" scores ~0.35 in a general search — below the 0.45
threshold. Use `search_by_tag("Horror")` when you want genre results.

### Optional filters

```python
idx.search_by_tag("Horror", source="Librivox")     # source filter
idx.search_by_author("Lovecraft", language="en")   # language filter
idx.search_by_title("Faust", max_results=3, min_score=0.6)
```

### Typo tolerance

FTS5 handles prefix matching but not typos. When FTS returns < 5 hits,
the search automatically falls back to a full rapidfuzz scan:

```python
idx.search_by_title("Sherlok Holms")  # FTS misses, rapidfuzz finds it
```

## IndexedSource — drop-in for unified search()

```python
from audiobooker import search
from audiobooker.index import BookIndex, IndexedSource

idx = BookIndex()
for book in search("Lovecraft", sources=[idx.as_source()], timeout=5):
    print(f"[{book.score:.2f}] {book.title}")
```

Filter by source or language at the `IndexedSource` level:

```python
librivox_only = IndexedSource(idx, source_filter="Librivox")
english_only  = IndexedSource(idx, language_filter="en")

for book in search("horror", sources=[english_only], timeout=5):
    print(book.title)
```

## Stats

```python
s = idx.stats()
# {'total': 28388, 'by_source': {'Librivox': 18012, ...}, 'by_language': {'en': 26400, ...}}
print(len(idx))   # total book count
```

## CLI

```bash
# Build full index
python -m audiobooker.index build

# Build selected sources
python -m audiobooker.index build --sources librivox loyalbooks

# Incremental update
python -m audiobooker.index update
python -m audiobooker.index update --sources librivox

# Stats
python -m audiobooker.index stats

# Search
python -m audiobooker.index search "Lovecraft"
python -m audiobooker.index search "Conan" --method search_by_title --n 5
python -m audiobooker.index search "horror" --method search_by_tag --source Librivox
python -m audiobooker.index search "Wayne June" --method search_by_narrator

# Custom database path
python -m audiobooker.index --db /data/books.db build
python -m audiobooker.index --db /data/books.db search "Poe"
```

## Custom database path

```python
idx = BookIndex("/data/my_books.db")
```

## Context manager

```python
with BookIndex() as idx:
    idx.build(sources=[AudioAnarchy()])
    for book in idx.search("anarchy"):
        print(book.title)
```

## YouTube sources

YouTube channels are excluded from the default `build()` source list since
they update frequently. Use `update()` to add new videos periodically:

```python
from audiobooker.scrappers.youtube import HorrorBabble, TheCybrarian

idx.update(sources=[HorrorBabble(), TheCybrarian()])
```

## Schema

The SQLite database has two tables:

- **`books`** — one row per book; primary key is an auto-increment `id`;
  `hash` (title + authors) is a unique constraint used for deduplication;
  `authors_text`, `tags_text`, `narrator_text` are flattened plaintext copies
  of the JSON fields used for FTS indexing.
- **`books_fts`** — FTS5 virtual table (unicode61 tokeniser, diacritic removal)
  linked to `books.id`. Kept in sync via explicit insert/delete calls during
  `build()` and `update()`.
