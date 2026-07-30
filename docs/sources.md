# Sources

All scrapers share the `AudioBookSource` interface. This page documents each
source's catalogue, native capabilities, and quirks.

## Interface

```python
source.search(query)               # title + author + tag (union, deduplicated)
source.search_by_title(query)
source.search_by_author(query)
source.search_by_tag(query)
source.search_by_narrator(query)
source.iterate_all()               # every book in the catalogue
source.iterate_popular()           # front-page / curated selection
source.iterate_by_author(author)
source.iterate_by_tag(tag)
```

All methods return lazy iterables of `AudioBook`. Network errors and parse
failures are swallowed per-item so a single bad page never aborts a run.

## Librivox

```python
from audiobooker.scrappers.librivox import Librivox
```

- **Site:** librivox.org
- **Catalogue:** ~18 000 books
- **API:** REST JSON, the fastest source. No HTML scraping needed
- **Native search:** title, author, narrator, tag (genre)
- **Genres:** 30+
- **Language:** many; normalised to ISO 639-1
- **Streams:** direct MP3 archive URLs

`search_by_narrator` and genre-based `search_by_tag` use API parameters.
`iterate_all()` pages through the full catalogue via the REST API.

## LoyalBooks

```python
from audiobooker.scrappers.loyalbooks import LoyalBooks
```

- **Site:** loyalbooks.com
- **Catalogue:** ~3 500 books
- **Native search:** title/author via sitemap scan, tag via genre pages
- **Genres:** 41 (see README for full list)
- **Streams:** MP3 URLs from RSS feed per book

`search_by_tag` fetches the genre page directly instead of scanning the full
catalogue, which is fast for genre queries. `iterate_popular()` scrapes the front page.

## StephenKingAudioBooks

```python
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks
```

- **Site:** stephenkingaudiobooks.com
- **Catalogue:** ~113 books (Stephen King titles only)
- **Native search:** full-text site search for title/author queries
- **Streams:** direct audio links or external embeds

Results from native search are post-filtered with `fuzzy_match` to avoid false
positives from the site's loose search engine.

## GoldenAudioBooks

```python
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
```

- **Site:** goldenaudiobook.co
- **Catalogue:** ~6 500 books (discovered via sitemap)
- **Native search:** linear scan via sitemap
- **Streams:** audio links scraped per book page

Uses the full sitemap index (`post-sitemap` entries) to enumerate all books,
giving ~6 500 titles vs the ~450 from hand-picked sitemap URLs.
`iterate_popular()` scrapes the front page.

## AudioAnarchy

```python
from audiobooker.scrappers.audioanarchy import AudioAnarchy
```

- **Site:** audioanarchy.org
- **Catalogue:** ~11 books
- **Genres/Tags:** Anarchy, Radio Drama
- **Native search:** linear scan

Small catalogue. `iterate_all()` walks the /audio/ and /radio/ sections.
`iterate_popular()` delegates to `iterate_all()`.

## DarkerProjects

```python
from audiobooker.scrappers.darkerprojects import DarkerProjects
```

- **Site:** darkerprojects.com
- **Catalogue:** ~244 episodes
- **Genre:** Audio Drama (original productions)
- **Native search:** linear scan via sitemap

`iterate_popular()` scrapes the front page featured shows.

## HPTalesAudioBooks

```python
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
```

- **Site:** hpaudiotales.com
- **Catalogue:** ~20 books
- **Genre:** Harry Potter fan recordings
- **Native search:** linear scan via sitemap

## Shared HTTP session

All sources share a single `requests.Session`. Override it on the class if you
need caching, retries, or a custom adapter:

```python
import requests
from audiobooker.scrappers import AudioBookSource

AudioBookSource.session = requests.Session()
```

See [youtube.md](youtube.md) for YouTube channel and playlist sources.

---
[← Scoring](scoring.md) · [Home](README.md) · [YouTube Sources →](youtube.md)
