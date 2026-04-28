# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 0.6.0

### Added

- **Unified parallel search** (`audiobooker.search`): `search()`, `search_by_title()`,
  `search_by_author()`, `search_by_tag()`, `search_by_narrator()` — all sources queried
  concurrently via daemon threads, results deduplicated and sorted by relevance score.
- **Relevance scoring** via [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) WRatio:
  `score_book(query, book, method)` with per-method field weights so `search_by_title`
  never boosts results via author score and vice versa. Title scoring adds a containment
  bonus. Results below 0.45 are filtered.
- **`AudioBook.source`** — stamped with the scraper class name on every yielded book.
- **`AudioBook.score`** — relevance score 0..1 from the last search.
- **`AudioBook.__hash__` / `__eq__`** keyed on `(title, sorted authors)` — books are now
  usable in sets and as dict keys for cross-source deduplication.
- **`AudioBook.has_live_streams()`** — HEAD-checks at least one stream URL.
- **`normalize_language()`** — maps full language names and regional tags to ISO 639-1
  codes (`"English"` → `"en"`, `"en-US"` → `"en"`). Applied automatically in
  `AudioBook.__post_init__`.
- **`iter_sitemap_urls(url)`** — recursively yields every leaf URL from a sitemap or
  sitemap index. Replaces all raw `SiteMapParser.get_urls()` calls; silences the
  `sitemapparser` CRITICAL log noise.
- **`check_url_availability(url)`** — HEAD request returning bool.
- **`fuzzy_match(query, text)`** — rapidfuzz-based helper with single-word sliding window
  and multi-word direct ratio. Used in all base-class `search_by_*` fallback methods.
- **`LoyalBooks.search_by_tag()`** — hits 41 genre pages directly instead of linear scan.
- **`LoyalBooks.iterate_popular()`** — scrapes the front-page featured selection.
- **`AudioAnarchy` radio section** — `/radio/` page now scraped; books tagged
  `["Anarchy", "Radio Drama"]`. Adds ~4 audio dramas previously missing.
- **`GoldenAudioBooks` full sitemap coverage** — root sitemap index auto-discovered;
  all `post-sitemap*.xml` pages included (~6 500 titles, up from ~450 previously).
- **`GoldenAudioBooks.iterate_popular()`** and **`DarkerProjects.iterate_popular()`** —
  front-page scrapes for fast curated results.
- **`StephenKingAudioBooks.search_by_title()` / `search_by_author()`** — native site
  search (`?s=` param) replaces 66-second linear sitemap scan.
- **`AudioBookSource._tag()`** — stamps `source` on every yielded book.
- **`AudioBookSource.source_name`** property.
- `score_book`, `iter_sitemap_urls`, `check_url_availability`, `normalize_language`
  exported from `audiobooker.__init__`.
- 21 new unit tests (37 total) covering fuzzy match, language normalisation,
  `AudioBook` hash/eq/source/score, and `score_book` per-method weight isolation.
- 10 standard GitHub Actions workflows via `OpenVoiceOS/gh-automations@dev`.
- `audiobooker/version.py` with standard version block.

### Fixed

- **`LoyalBooks`**: hours-to-seconds multiplier was `120`, now correctly `3600`.
- **`LoyalBooks`**: sitemap uses `http://` URLs; filter was checking `https://` prefix.
- **`LoyalBooks`** RSS parsing: all feed fields guarded against `None` / missing keys.
- **`Librivox`**: `_parse_res` IndexError when RSS entry count < section count.
- **`Librivox`**: `search_by_title` used `title=` param (returns 404); now uses `search=`.
- **`Librivox`**: feedparser `timeout` kwarg removed (unsupported, raised `TypeError`).
- **`Librivox`**: playtime parsed to `int` seconds via `_parse_playtime()` instead of
  leaving as string.
- **`StephenKingAudioBooks`**: sitemap domain was `stephenkingaudiobook.net` (wrong);
  fixed to `stephenkingaudiobooks.com`.
- **`StephenKingAudioBooks`**: site search post-filtered with fuzzy check to remove
  irrelevant results the site returns for any query.
- **`AudioAnarchy`**: radio section relative hrefs resolved against section base URL
  (were resolving against root, causing 404s).
- **`GoldenAudioBooks`**: all HTML element accesses guarded against `None`.
- **`sitemapparser`** CRITICAL log noise suppressed via logger level.
- All scrapers: bare `except:` → `except Exception:`, `None` guards on all soup lookups.

### Changed

- Packaging migrated from `setup.py` to `pyproject.toml`; `setuptools.build_meta` backend.
- `requests-cache` in-memory session with 1-hour TTL; User-Agent randomised at class level.
- All base-class `search_by_*` methods use `fuzzy_match` (rapidfuzz) instead of exact substring.
- `search_by_author` anchors on the last query token matching the candidate's last name before
  full-name fuzzy check — prevents `"Stephen King"` matching `"Stephen Crane"`.
- README fully rewritten with catalogue stats, scoring table, and utility docs.

### Removed

- `StoryNory` scraper — site migrated to SvelteKit SPA, scraping no longer works.
- `ThoughtAudio` scraper — site blocks automated access (403 / SSL failure).
- `SharedAudioBooks` scraper — site returns HTTP 500.
- `setup.py`, `requirements.txt` — replaced by `pyproject.toml`.
- Dead `base_url` / `authors_url` class variables from multiple scrapers.
- Unused exception imports from `scrappers/__init__.py`.

## [0.2.6] — 2019-12-12

### Changed

- Transferred ownership to [OpenJarbas](https://github.com/OpenJarbas)
- Added deprecation warning for broken HPPodcraft scraper

[unreleased]: https://github.com/TigreGotico/audiobooker/compare/master...feat/modernize-and-audit
