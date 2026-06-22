# audiobooker

Search and stream free audiobooks from multiple web sources. Parallel search,
fuzzy scoring, a unified `AudioBook` dataclass, local cache, SQLite index, and
a mediavocab `Release` converter — one API regardless of where the book comes from.

## Install

```bash
pip install audiobooker

# Optional extras
pip install audiobooker[youtube]   # YouTube channel/playlist sources (tutubo)
pip install audiobooker[stealth]   # curl_cffi TLS-fingerprint transport
pip install audiobooker[test]      # pytest + vcrpy (dev only)
```

## Quick start

```python
from audiobooker import search

for book in search("Lovecraft", max_per_source=5, timeout=30):
    print(f"[{book.score:.2f}] [{book.source}] {book.title}")
    print(f"  authors={[f'{a.first_name} {a.last_name}'.strip() for a in book.authors]}")
    print(f"  streams={len(book.streams)}")
```

## Supported sources

| Source | Site | Catalogue | Native search |
|---|---|---|---|
| `Librivox` | librivox.org | ~18 000 books | REST API (title, author, narrator, tag) |
| `LoyalBooks` | loyalbooks.com | ~3 500 books | sitemap + genre pages |
| `GoldenAudioBooks` | goldenaudiobook.co | ~6 500 books | linear scan |
| `StephenKingAudioBooks` | stephenkingaudiobooks.com | ~113 books | native site search |
| `AudioAnarchy` | audioanarchy.org | ~11 books | linear scan |
| `DarkerProjects` | darkerprojects.com | ~244 episodes | linear scan |
| `HPTalesAudioBooks` | hpaudiotales.com | ~20 books | linear scan |

**YouTube** (`pip install audiobooker[youtube]`):

| Source | Channel | Content |
|---|---|---|
| `TheCybrarian` | @TheCybrarian | Robert E. Howard fiction |
| `HorrorBabble` | @HorrorBabble | Horror short fiction |

## Python API

```python
from audiobooker import (
    search, search_by_title, search_by_author, search_by_tag, search_by_narrator,
    audiobook_to_release,
    BookIndex, IndexedSource,
    AudioBook, BookAuthor, AudiobookNarrator, AudioBookChapter,
)

# Targeted searches — all run in parallel across all sources
for book in search_by_author("Dickens", max_per_source=5):
    print(book.title)

for book in search_by_tag("horror", max_per_source=5):
    print(book.title)
```

### Per-source

```python
from audiobooker.scrappers.librivox import Librivox

lv = Librivox()
for book in lv.search_by_title("Dracula"):
    print(book.title, book.runtime)

for book in lv.iterate_all():   # full catalogue
    print(book.title)
```

All scrapers share the same interface: `search()`, `search_by_title()`,
`search_by_author()`, `search_by_tag()`, `search_by_narrator()`,
`iterate_all()`, `iterate_popular()`, `iterate_by_author()`, `iterate_by_tag()`.

## mediavocab integration

`mediavocab` is a required dependency. `audiobook_to_release()` projects an
`AudioBook` into the typed `mediavocab.Release` schema — `Work`, credits,
chapters, external IDs, codec, license.

```python
from audiobooker import search, audiobook_to_release

for book in search("Lovecraft", max_per_source=3):
    release = audiobook_to_release(book)
    lic = release.parsed_license
    if lic and lic.is_open():
        print(release.work.title, lic.identifier)
```

See [docs/converters.md](docs/converters.md) for the full field mapping.

## HTTP transport

By default every scraper uses a `requests.Session` with a randomised
`User-Agent`. Two ways to override:

**Environment variable** — set before any import:
```bash
AUDIOBOOKER_TRANSPORT=curl_cffi python myscript.py
```
Falls back to plain `requests` if `curl_cffi` is not installed. Install with
`pip install audiobooker[stealth]`.

**Per-instance injection** — pass any `requests`-compatible session:
```python
from curl_cffi import requests as cffi_requests
from audiobooker.scrappers.librivox import Librivox

session = cffi_requests.Session(impersonate="chrome")
lv = Librivox(session=session)
```

`default_session()` from `audiobooker.transport` respects `AUDIOBOOKER_TRANSPORT`
and returns the appropriate session type. — `audiobooker/transport.py:1`

## Local index

Build once, search without network access:

```python
from audiobooker.index import BookIndex

idx = BookIndex()   # ~/.audiobooker/index.db
idx.build()         # iterate_all() on all 7 web sources

for book in idx.search_by_title("Sherlock Holmes", max_results=5):
    print(f"[{book.score:.2f}] {book.title}")
```

## CLI reference

```
audiobooker search <query>
    --method  search|search_by_title|search_by_author|search_by_tag|search_by_narrator
    -n        max results (default 10)
    --source  limit to one source
    --timeout seconds (default 30)
    -v        verbose (tags, narrator, stream URLs)

audiobooker index build [--sources librivox loyalbooks ...]
audiobooker index update
audiobooker index search <query> [--method ...] [-n N]
audiobooker index stats
audiobooker index follow <url> [--kind channel|playlist] [--tags ...] [--blacklist ...]
audiobooker index unfollow <url>
audiobooker index list

audiobooker cache download <query> [--stream INDEX]
audiobooker cache play     <query> [--stream INDEX]
audiobooker cache list
audiobooker cache clear    [<query>]
audiobooker cache info     <query>
```

All `index` and `cache` commands accept `--db PATH` and `--cache-dir PATH`
to override default locations (`~/.audiobooker/index.db` and
`~/.cache/audiobooker`).

## Docs

Full documentation is in [`/docs/`](docs/README.md):

- [Getting started](docs/getting-started.md)
- [Sources](docs/sources.md) — per-scraper details and quirks
- [Search orchestrator](docs/search.md)
- [Scoring](docs/scoring.md)
- [Index](docs/index.md) — SQLite index, offline search, YouTube follow
- [Cache](docs/cache.md) — download + play
- [Converters](docs/converters.md) — mediavocab Release shape
- [Transport](docs/transport.md) — HTTP session, stealth backend
- [API reference](docs/api.md)

Runnable examples are in [`/examples/`](examples/) — numbered 01 → 10 from
quickstart to advanced index usage.

## Error handling

Network failures and malformed pages are swallowed per-item — a bad page never
aborts an `iterate_all()` run. If a source site is down or has restructured its
HTML, that scraper silently yields nothing.

## License

MIT
