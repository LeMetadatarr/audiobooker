# API Reference

## AudioBook

```python
from audiobooker.base import AudioBook
```

```python
@dataclass
class AudioBook:
    title: str = ""
    description: str = ""
    image: str = ""            # cover art URL
    language: str = ""         # ISO 639-1 (normalised on init via normalize_language)
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    streams: List[str] = field(default_factory=list)   # direct audio URLs
    narrator: Optional[AudiobookNarrator] = None
    year: int = 0
    runtime: int = 0           # seconds (where available)
    source: str = ""           # set automatically by the scraper, e.g. "Librivox"
    score: float = 0.0         # relevance score from last search (0..1)
```

### Equality and hashing

`AudioBook.__hash__` and `__eq__` are keyed on `(title.lower(), sorted authors)`.
Use a `set` to deduplicate across sources:

```python
seen = set()
for book in results:
    if book not in seen:
        seen.add(book)
        process(book)
```

### has_live_streams()

```python
book.has_live_streams() -> bool
```

Issues a HEAD request to each stream URL and returns `True` if at least one
responds with HTTP < 400. Uses the shared cached session.

## BookAuthor

```python
from audiobooker.base import BookAuthor

a = BookAuthor(first_name="H. P.", last_name="Lovecraft")
```

Equality and hashing are case-insensitive.

## AudiobookNarrator

```python
from audiobooker.base import AudiobookNarrator

n = AudiobookNarrator(first_name="Frank", last_name="Muller")
```

## AudioBookSource

Base class for all scrapers.

```python
from audiobooker.scrappers import AudioBookSource
```

### Class-level shared session

```python
AudioBookSource.session   # plain requests.Session shared across all scrapers
```

Replace with your own session if you need caching, retries, or a custom adapter:

```python
import requests
AudioBookSource.session = requests.Session()
```

### source_name property

Returns `self.__class__.__name__`. Stamped into `book.source` via `_tag()`.

### Abstract / override

| Method | Required | Description |
|---|---|---|
| `iterate_all()` | yes | Yield every book in the catalogue |
| `iterate_popular()` | no | Defaults to `iterate_all()` |

All `search_by_*` methods have working default implementations in the base
class (fuzzy linear scan over `iterate_all()`). Override for native search.

## Utilities

```python
from audiobooker import score_book, iter_sitemap_urls, check_url_availability, normalize_language
```

### score_book

```python
score_book(query: str, book: AudioBook, method: str = "search") -> float
```

Returns 0.0–1.0. `method` controls field weights — use the same name as the
search function (`"search"`, `"search_by_title"`, etc.). See [scoring.md](scoring.md).

### iter_sitemap_urls

```python
iter_sitemap_urls(url: str) -> Iterable[str]
```

Recursively walks a sitemap or sitemap index and yields every leaf URL.
Handles both `<urlset>` and `<sitemapindex>` transparently. Silently skips
URLs that fail to fetch or parse.

### check_url_availability

```python
check_url_availability(url: str, timeout: int = 5) -> bool
```

Returns `True` if a HEAD request to `url` returns HTTP < 400.

### normalize_language

```python
normalize_language(lang: str) -> str
```

Maps any language string to an ISO 639-1 two-letter code:

```python
normalize_language("English")   # → "en"
normalize_language("en-US")     # → "en"
normalize_language("français")  # → "fr"
normalize_language("de")        # → "de"
```

Called automatically by `AudioBook.__post_init__` on the `language` field.
