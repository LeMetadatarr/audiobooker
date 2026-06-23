# Getting Started

## Install

```bash
pip install audiobooker
```

Optional extras:

| Extra | Installs | Enables |
|---|---|---|
| `[youtube]` | tutubo | `TheCybrarian`, `HorrorBabble`, `YoutubeChannelSource` |
| `[stealth]` | curl-cffi | TLS-fingerprint transport to bypass bot protection |
| `[test]` | pytest, vcrpy, pytest-vcr | running the test suite |

## First search

```python
from audiobooker import search

for book in search("Dracula", max_per_source=3, timeout=30):
    print(f"[{book.score:.2f}] [{book.source}] {book.title}")
    print(f"  streams: {book.streams[:1]}")
```

`search()` queries all 7 web sources in parallel threads. Results arrive sorted
by relevance score and deduplicated by title + authors.

## Key objects

| Object | Module | Purpose |
|---|---|---|
| `AudioBook` | `audiobooker.base` | Unified book dataclass — title, authors, chapters, streams |
| `BookAuthor` | `audiobooker.base` | Author name (first + last) |
| `AudiobookNarrator` | `audiobooker.base` | Reader name |
| `AudioBookChapter` | `audiobooker.base` | Chapter with offset, runtime, stream URL |
| `AudioBookSource` | `audiobooker.scrappers` | Base class for all scrapers |
| `BookIndex` | `audiobooker.index` | SQLite offline index |

## Search methods

```python
from audiobooker import search, search_by_title, search_by_author, search_by_tag, search_by_narrator

search("Poe")                          # title + author + tag, weighted
search_by_title("The Raven")
search_by_author("Edgar Allan Poe")
search_by_tag("horror")
search_by_narrator("Frank Muller")
```

All accept `sources`, `max_per_source`, `timeout`, `deduplicate`. See
[search.md](search.md) for details.

## Single-source

```python
from audiobooker.scrappers.librivox import Librivox

lv = Librivox()
for book in lv.search_by_author("Lovecraft", max_per_source=5):
    print(book.title, book.runtime, "s")
```

## mediavocab conversion

```python
from audiobooker import search, audiobook_to_release

book = next(search("Dracula", max_per_source=1))
release = audiobook_to_release(book)
print(release.work.title, release.license)
```

See [converters.md](converters.md) for the full field mapping.

## CLI

```bash
audiobooker search "Sherlock Holmes" -n 5 -v
audiobooker index build
audiobooker index search "Lovecraft" --method search_by_author
audiobooker cache download "Dracula" --source Librivox
audiobooker cache play "Dracula"
```
