# audiobooker — Developer Docs

| Document | Contents |
|---|---|
| [search.md](search.md) | Unified parallel search API, parameters, `ALL_SOURCES` |
| [scoring.md](scoring.md) | How scores are computed, field weights, fuzzy matching details |
| [sources.md](sources.md) | Each web scraper — catalogue size, native search, quirks |
| [youtube.md](youtube.md) | YouTube channel and playlist sources (`YoutubeChannelSource`, `YoutubePlaylistSource`, `TheCybrarian`, `HorrorBabble`) |
| [api.md](api.md) | Full API reference: `AudioBook`, `BookAuthor`, `AudioBookSource`, utilities |

See also the `examples/` directory for runnable code:

| Example | Shows |
|---|---|
| `search_all_sources.py` | Unified search across all web sources |
| `search_librivox.py` | Librivox REST API search |
| `search_loyalbooks.py` | LoyalBooks genre and title search |
| `search_stephenkingaudiobooks.py` | StephenKingAudioBooks native search |
| `iterate_goldenaudiobooks.py` | GoldenAudioBooks full catalogue iteration |
| `iterate_audioanarchy.py` | AudioAnarchy catalogue |
| `iterate_darkerprojects.py` | DarkerProjects audio dramas |
| `iterate_hpaudiotales.py` | HPTalesAudioBooks |
| `youtube_sources.py` | YouTube channel + playlist sources, unified search |
| `low_level_usage.py` | Direct scraper usage without the search layer |
