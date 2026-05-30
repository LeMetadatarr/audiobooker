# audiobooker — agent guide

Python client that searches and streams free / public-domain audiobooks from multiple web sources behind one API, scores results with fuzzy matching, caches and indexes them locally, and projects each book into a typed `mediavocab.Release`.

## Setup

```bash
pip install -e .
pip install -e .[test]      # pytest + vcrpy + pytest-vcr
pip install -e .[youtube]   # tutubo — enables YouTube channel/playlist sources
pip install -e .[stealth]   # curl_cffi — TLS-fingerprint HTTP transport
```

Requires Python >= 3.8. Console script entry point: `audiobooker` -> `audiobooker.cli:cli`.

## Test

```bash
pytest                      # testpaths = ["test"]
```

Parser tests are cassette-backed (vcrpy/pytest-vcr); they replay recorded HTTP and need no network. To re-record against live upstreams, run vcrpy in record mode locally — the `nightly-live.yml` workflow does this in detect-only mode (cassettes are not committed back). `test/license_tests.py` is a separate `lichecker`-based dependency-license check (not pytest).

## Lint/Typecheck

Ruff via `.github/workflows/lint.yml` (`ruff: true`). No type checker configured; the data models in `base.py` are plain `@dataclass`, the `converters.py` boundary is fully typed against mediavocab.

## Layout

- `audiobooker/base.py` — core dataclasses `AudioBook`, `BookAuthor`, `AudiobookNarrator`, `AudioBookChapter`; `normalize_language()` (ISO 639-1); `AudioBook.stable_id()` is a deterministic sha256-based key used for caching/dedup/index.
- `audiobooker/scrappers/` — one module per source, all subclass `AudioBookSource` (in `scrappers/__init__.py`). Sources: `librivox` (REST API), `loyalbooks` (sitemap+genre), `goldenaudiobooks`, `stephenkingaudiobooks`, `audioanarchy`, `darkerprojects`, `hpaudiotales` (linear scans), and `youtube` (`TheCybrarian`, `HorrorBabble`, optional, needs tutubo). Base class provides default `search*`/`iterate_*` built on the abstract `iterate_all()`.
- `audiobooker/search.py` — `ALL_SOURCES` list + `_parallel_search()`: one daemon thread per source feeding a queue, with timeout, dedup by `hash(book)`, fuzzy `score_book()` re-ranking, `min_score=0.45` filter. Public: `search`, `search_by_title/_author/_narrator/_tag`.
- `audiobooker/index.py` — `BookIndex` SQLite store at `~/.audiobooker/index.db`; FTS5 pre-filter then rapidfuzz WRatio re-rank, full-scan fallback on zero hits; supports YouTube follow/unfollow; `as_source()` makes it usable as a `search()` source.
- `audiobooker/cache.py` — download/play/list/clear/info of streams under `~/.cache/audiobooker`.
- `audiobooker/converters.py` — `audiobook_to_release()`: the only mediavocab boundary. Builds `Work` (credits as author=CREATOR / narrator=PERFORMER, content_genres, external_ids incl. `audiobooker_id` from `stable_id()`) and wraps it in `Release` (license `public_domain` for librivox/loyalbooks, codec/bitrate, chapters).
- `audiobooker/transport.py` — `default_session()`; `AUDIOBOOKER_TRANSPORT=curl_cffi` switches to a TLS-impersonating session, silently falling back to `requests` if curl_cffi is absent.
- `audiobooker/cli.py` — Click CLI: `search`, `index` (build/update/search/stats/follow/unfollow/list), `cache` (download/play/list/clear/info).
- `audiobooker/utils.py` — `fuzzy_match`, `score_book`, `random_user_agent`, `check_url_availability`, `iter_sitemap_urls`.
- `test/` — 23 test modules, ~375 test functions, VCR cassettes per scraper.

## Conventions

- Branches: work on `dev`, stable on `master`. Never `main`.
- Never edit `audiobooker/version.py` — gh-automations bumps semver from conventional-commit prefixes (`feat:`, `fix:`, `feat!:`).
- New repos private by default.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`. CI (build-tests, coverage, license-check, lint, publish-alpha/stable) is provided by gh-automations.
- No Neon / `neon-*` references. No meta-commentary (no history, dates, "before times").

## Gotchas

- The `scrappers` subpackage does not appear in `__init__.py`'s `__all__`; import scrapers directly (`from audiobooker.scrappers.librivox import Librivox`). YouTube sources import-guard on tutubo and are appended to `ALL_SOURCES` only when installed.
- `AudioBook` keeps singular `narrator` and plural `narrators` in sync via `__post_init__`; the converter dedups narrators case-insensitively.
- `_worker` swallows all source exceptions (a failing scraper silently yields nothing); slow sources are cancelled at `timeout` via a per-source `stop` Event.
- `min_score=0.45` in `_parallel_search` filters low-confidence matches — a query that returns nothing may simply be below threshold.
- `pyproject.toml` `Homepage`/`Repository` URLs still point at `OpenJarbas/audiobooker`; the canonical remote is `TigreGotico/audiobooker`.
- License `public_domain` is assigned only for librivox/loyalbooks (`_PUBLIC_DOMAIN_SOURCES`); other sources get an empty license string.
