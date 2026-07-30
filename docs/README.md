# audiobooker Docs

| Document | Contents |
|---|---|
| [getting-started.md](getting-started.md) | Install, first search, key concepts |
| [search.md](search.md) | Unified parallel search API, parameters, `ALL_SOURCES` |
| [scoring.md](scoring.md) | Score computation, field weights, fuzzy matching details |
| [sources.md](sources.md) | Each web scraper: catalogue size, native search, quirks |
| [youtube.md](youtube.md) | `YoutubeChannelSource`, `YoutubePlaylistSource`, `TheCybrarian`, `HorrorBabble` |
| [index.md](index.md) | `BookIndex`: SQLite index, offline search, YouTube follow, CLI |
| [cache.md](cache.md) | Download streams to disk, play, cache management |
| [converters.md](converters.md) | `audiobook_to_release()`: mediavocab `Release` field mapping |
| [transport.md](transport.md) | HTTP session, `AUDIOBOOKER_TRANSPORT`, stealth backend |
| [api.md](api.md) | Full API reference: `AudioBook`, `BookAuthor`, `AudioBookSource`, utilities |

Examples are in `../examples/`, numbered 01 to 10 from quickstart to advanced:

| File | Shows |
|---|---|
| `01_quickstart.py` | Search LibriVox for one book |
| `02_search_all_sources.py` | Unified parallel search orchestrator |
| `03_filter_by_author.py` | Author search with score display |
| `04_download_and_cache.py` | Download streams to local cache |
| `05_play_with_cache.py` | Play from cache (download if missing) |
| `06_convert_to_mediavocab.py` | Convert to mediavocab `Release` |
| `07_custom_session.py` | Inject a custom HTTP session. curl_cffi is opt-in |
| `08_youtube_audiobooks.py` | YouTube sources (requires `[youtube]` extra) |
| `09_advanced_index.py` | `IndexedSource` + SQLite index + follow |
| `10_cli_pipeline.py` | Shell-callable search → download pipeline |
