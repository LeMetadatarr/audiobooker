# AudioBooker

Audiobook scraper — search and iterate audiobooks from multiple free sources.

## Supported Sources

| Class | Site | Native Search | Iterate All |
|---|---|---|---|
| `Librivox` | librivox.org | title, author, narrator, tag (via API) | yes (paginated) |
| `LoyalBooks` | loyalbooks.com | title, author (via sitemap) | yes |
| `StephenKingAudioBooks` | stephenkingaudiobooks.com | full-text (via site search) | yes |
| `GoldenAudioBooks` | goldenaudiobook.co | title, author, tag (linear scan) | yes |
| `AudioAnarchy` | audioanarchy.org | title, author, tag (linear scan) | yes |
| `DarkerProjects` | darkerprojects.com | title, author, tag (linear scan) | yes |
| `HPTalesAudioBooks` | hpaudiotales.com | title, author, tag (linear scan) | yes |

## Install

```bash
pip install audiobooker
```

## Usage

All scrapers share the same interface via `AudioBookSource`. Methods return generators of `AudioBook` dataclass instances.

### Common interface

```python
scraper.search(query)               # search by title, author, and tag
scraper.search_by_title(query)
scraper.search_by_author(query)
scraper.search_by_tag(query)
scraper.search_by_narrator(query)
scraper.iterate_all()               # yield every book from the source
scraper.iterate_popular()           # defaults to iterate_all()
scraper.iterate_by_author(author)
scraper.iterate_by_tag(tag)
```

### AudioBook fields

```python
@dataclass
class AudioBook:
    title: str
    description: str
    image: str          # cover art URL
    language: str
    authors: List[BookAuthor]
    tags: List[str]
    streams: List[str]  # direct audio URLs (mp3 / rss feed entries)
    narrator: AudiobookNarrator
    year: int
    runtime: int        # seconds (where available)
```

### Librivox

Librivox has a public API — searches are fast and targeted.

```python
from audiobooker.scrappers.librivox import Librivox

lv = Librivox()

for book in lv.search_by_title("Art of War"):
    print(book.title, book.streams)

for book in lv.search_by_author("Lovecraft"):
    print(book.title, book.authors)

for book in lv.search_by_narrator("LibriVox"):
    print(book.title, book.narrator)
```

### LoyalBooks

```python
from audiobooker.scrappers.loyalbooks import LoyalBooks

lb = LoyalBooks()

for book in lb.search_by_author("lovecraft"):
    print(book.title, book.streams)

for book in lb.iterate_all():
    print(book.title)
```

### Other scrapers

All other scrapers support `iterate_all()` to walk their full catalogue:

```python
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker.scrappers.darkerprojects import DarkerProjects
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

for book in AudioAnarchy().iterate_all():
    print(book.title, book.authors, book.streams)
```

## Caching

HTTP responses are cached in memory for 1 hour by default (via `requests-cache`).
The shared session lives on `AudioBookSource.session` and can be replaced if needed.

## Error handling

Network failures and malformed pages are swallowed per-item — a single bad page
won't abort a full `iterate_all()` run. If a source site is down or has changed
its HTML structure, that scraper will silently yield nothing.

## License

MIT
