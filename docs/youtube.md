# YouTube Sources

YouTube channel and playlist sources are optional and require `tutubo`:

```bash
pip install audiobooker[youtube]
# or
pip install tutubo
```

When installed, `TheCybrarian`, `HorrorBabble`, and `TheDustyTome` are
automatically added to `ALL_SOURCES` and participate in every `search*()` call.

## Pre-configured channels

### TheCybrarian

Robert E. Howard fiction (Conan, Solomon Kane, Kull, El Borak…).

```python
from audiobooker.scrappers.youtube import TheCybrarian

for book in TheCybrarian().iterate_all():
    print(book.title, book.runtime, "s")
    print(book.streams[0])   # YouTube watch URL
```

- Channel: [@TheCybrarian](https://www.youtube.com/@TheCybrarian)
- Authors: `BookAuthor(first_name="Robert E.", last_name="Howard")`
- Tags: Fantasy, Sword and Sorcery, Robert E. Howard, Conan
- `min_runtime`: 120 s (keeps short pieces, filters out channel trailers)

### HorrorBabble

Horror short fiction narrated by Ian Gordon.

```python
from audiobooker.scrappers.youtube import HorrorBabble

for book in HorrorBabble().search_by_title("Lovecraft"):
    print(book.title, book.tags)
```

- Channel: [@HorrorBabble](https://www.youtube.com/@HorrorBabble)
- Authors: `BookAuthor(last_name="Various")`
- Tags: Horror, Lovecraft, Weird Fiction, Short Stories
- `min_runtime`: 300 s (5 minutes, filters out shorts and trailers)

### TheDustyTome

Classic literature and fantasy audiobooks. Authors and narrators are extracted
per-video from the title/description using `extract_metadata=True`.

```python
from audiobooker.scrappers.youtube import TheDustyTome

for book in TheDustyTome().iterate_all():
    print(book.title, book.authors)
```

- Channel: [@TheDustyTome](https://www.youtube.com/@TheDustyTome)
- Authors: extracted per-video (falls back to empty)
- Tags: Classic Literature, Fantasy, Audiobook
- `min_runtime`: 300 s

## YoutubeChannelSource

Generic source for any YouTube channel.

```python
from audiobooker.scrappers.youtube import YoutubeChannelSource
from audiobooker.base import BookAuthor

source = YoutubeChannelSource(
    channel_url="https://www.youtube.com/@SomeChannel/videos",
    authors=[BookAuthor(last_name="Unknown")],
    tags=["Audiobook"],
    language="en",
    min_runtime=300,   # skip anything under 5 minutes
)

for book in source.iterate_all():
    print(book.title, book.runtime)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `channel_url` | str | `""` | Full channel `/videos` URL |
| `authors` | List[BookAuthor] | `[]` | Stamped on every book |
| `tags` | List[str] | `[]` | Stamped on every book |
| `language` | str | `"en"` | ISO 639-1 code |
| `min_runtime` | int | 300 | Skip videos shorter than this many seconds |

### Methods

All standard `AudioBookSource` methods are supported:

| Method | Behaviour |
|---|---|
| `iterate_all()` | Yields all videos from the channel's first page |
| `iterate_popular()` | Same as `iterate_all()` (first page = most recent) |
| `search_by_title(query)` | Fuzzy match against video titles |
| `search_by_author(query)` | Fuzzy match against the configured authors list |
| `search_by_tag(query)` | Fuzzy match against the configured tags list |

### Implementation note

`iterate_all()` fetches only the **first page** of videos as returned by
`tutubo.models.Channel.initial_data`. YouTube does not expose a simple
pagination API without authentication, so deep channels are only partially
covered. This is the same limitation that applies to all unauthenticated
YouTube scraping.

## YoutubePlaylistSource

Source for a specific YouTube playlist URL.

```python
from audiobooker.scrappers.youtube import YoutubePlaylistSource
from audiobooker.base import BookAuthor

playlist = YoutubePlaylistSource(
    playlist_url="https://www.youtube.com/playlist?list=PLxxxxxx",
    authors=[BookAuthor(last_name="Various")],
    tags=["Horror"],
    language="en",
    min_runtime=60,
)

for book in playlist.iterate_all():
    print(book.title, book.runtime)
```

### Parameters

Same as `YoutubeChannelSource` but with `playlist_url` instead of `channel_url`:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `playlist_url` | str | `""` | Full `youtube.com/playlist?list=` URL |
| `authors` | List[BookAuthor] | `[]` | Stamped on every book |
| `tags` | List[str] | `[]` | Stamped on every book |
| `language` | str | `"en"` | ISO 639-1 code |
| `min_runtime` | int | 300 | Skip videos shorter than this many seconds |

### Methods

Same interface as `YoutubeChannelSource`. `iterate_all()` yields all videos
in the playlist in playlist order via `tutubo.models.Playlist.initial_data`.

### Pagination

YouTube's initial page for a playlist contains up to ~100 videos. Playlists
beyond that limit are not paginated. Only the first page is fetched.
Most audiobook playlists are well under this limit.

## Using YouTube sources in unified search

Pass any YouTube source instance in `sources=`:

```python
from audiobooker import search
from audiobooker.scrappers.youtube import TheCybrarian, YoutubePlaylistSource
from audiobooker.base import BookAuthor

my_playlist = YoutubePlaylistSource(
    playlist_url="https://www.youtube.com/playlist?list=PLxxxxxx",
    authors=[BookAuthor(last_name="Lovecraft")],
    tags=["Horror"],
)

for book in search("Dunwich", sources=[TheCybrarian(), my_playlist], timeout=20):
    print(f"[{book.score:.2f}] [{book.source}] {book.title}")
```

## Streams

YouTube sources produce `streams` containing YouTube watch URLs
(`https://www.youtube.com/watch?v=VIDEO_ID`). These are not direct audio
streams. A downstream player must resolve them, for example with `yt-dlp`.
`has_live_streams()` returns `True` for any reachable watch URL.

---
[← Sources](sources.md) · [Home](README.md) · [Local Index →](index.md)
