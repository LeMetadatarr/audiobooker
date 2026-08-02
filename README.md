# audiobooker

Search and stream free audiobooks from multiple web sources. It gives one API
regardless of where the book comes from, with parallel search, fuzzy scoring,
a unified `AudioBook` dataclass, a local cache, a SQLite index, and a mediavocab
`Release` converter.

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
| `TheDustyTome` | @TheDustyTome | Classic literature, horror, and weird fiction |

`TheCybrarian` and `HorrorBabble` are added to `ALL_SOURCES` automatically.
`TheDustyTome` must be passed explicitly via `sources=`. See
[docs/youtube.md](docs/youtube.md).

## Python API

```python
from audiobooker import (
    search, search_by_title, search_by_author, search_by_tag, search_by_narrator,
    audiobook_to_release,
    BookIndex, IndexedSource,
    AudioBook, BookAuthor, AudiobookNarrator, AudioBookChapter,
)

# Targeted searches, all run in parallel across all sources
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
`AudioBook` into the typed `mediavocab.Release` schema: `Work`, credits,
chapters, external IDs, codec, license.

```python
from audiobooker import search, audiobook_to_release

for book in search("Lovecraft", max_per_source=3):
    release = audiobook_to_release(book)
    lic = release.license
    if lic and lic.is_open():
        print(release.work.title, lic.identifier)
```

See [docs/converters.md](docs/converters.md) for the full field mapping.

## HTTP transport

By default every scraper uses a shared `requests.Session` with a randomised
`User-Agent`. To use a different backend, build a session and inject it into
the scraper instance — this is not automatic, you must pass it explicitly.

**Stealth backend**, for sites that fingerprint the TLS handshake:
```bash
pip install audiobooker[stealth]
```
```python
import os
os.environ["AUDIOBOOKER_TRANSPORT"] = "curl_cffi"

from audiobooker.transport import default_session
from audiobooker.scrappers.librivox import Librivox

lv = Librivox(session=default_session())
```
`default_session()` returns a `curl_cffi`-backed session when
`AUDIOBOOKER_TRANSPORT=curl_cffi` is set and `curl_cffi` is importable, and
falls back to plain `requests` otherwise.

**Per-instance injection**, pass any `requests`-compatible session directly:
```python
from curl_cffi import requests as cffi_requests
from audiobooker.scrappers.librivox import Librivox

session = cffi_requests.Session(impersonate="chrome")
lv = Librivox(session=session)
```

See [docs/transport.md](docs/transport.md) for the full backend list.

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

audiobooker index build [--sources librivox --sources loyalbooks ...]
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
- [Sources](docs/sources.md): per-scraper details and quirks
- [Search orchestrator](docs/search.md)
- [Scoring](docs/scoring.md)
- [Index](docs/index.md): SQLite index, offline search, YouTube follow
- [Cache](docs/cache.md): download and play
- [Converters](docs/converters.md): mediavocab Release shape
- [Transport](docs/transport.md): HTTP session, stealth backend
- [API reference](docs/api.md)

Runnable examples are in [`/examples/`](examples/), numbered 01 to 10 from
quickstart to advanced index usage.

## Related projects

- [tutubo](https://github.com/LeMetadatarr/tutubo): YouTube channel/playlist
  scraping, used by the `[youtube]` extra.
- [unblock_requests](https://github.com/LeMetadatarr/unblock_requests): IP
  rotation and Cloudflare bypass, used by the `[stealth]` extra.

## Error handling

Network failures and malformed pages are swallowed per-item. A bad page never
aborts an `iterate_all()` run. If a source site is down or has restructured its
HTML, that scraper yields nothing without raising an error.

## License

MIT
