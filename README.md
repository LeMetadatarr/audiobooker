# AudioBooker

Python library for searching and streaming free audiobooks from multiple sources.
Parallel search across all sources, fuzzy matching, relevance scoring, and a unified
`AudioBook` dataclass — one API regardless of where the book comes from.

## Supported Sources

| Source | Site | Catalogue | Native Search | Genres / Tags |
|---|---|---|---|---|
| `Librivox` | librivox.org | ~18 000 books | title, author, narrator, tag (REST API) | 30+ |
| `LoyalBooks` | loyalbooks.com | ~3 500 books | title, author (sitemap), tag (genre pages) | 41 |
| `StephenKingAudioBooks` | stephenkingaudiobooks.com | ~113 books | full-text site search | — |
| `GoldenAudioBooks` | goldenaudiobook.co | ~6 500 books | title, author, tag (linear scan) | — |
| `AudioAnarchy` | audioanarchy.org | ~11 books | title, author, tag (linear scan) | Anarchy, Radio Drama |
| `DarkerProjects` | darkerprojects.com | ~244 episodes | title, author, tag (linear scan) | Audio Drama |
| `HPTalesAudioBooks` | hpaudiotales.com | ~20 books | title, author, tag (linear scan) | Harry Potter |

**YouTube sources** (optional, requires `pip install audiobooker[youtube]`):

| Source | Channel | Content | Tags |
|---|---|---|---|
| `TheCybrarian` | [@TheCybrarian](https://www.youtube.com/@TheCybrarian) | Robert E. Howard fiction (Conan, Solomon Kane, Kull…) | Fantasy, Sword and Sorcery, Robert E. Howard |
| `HorrorBabble` | [@HorrorBabble](https://www.youtube.com/@HorrorBabble) | Horror short fiction narrated by Ian Gordon | Horror, Lovecraft, Weird Fiction |

**Total indexed:** ~28 000+ titles across 7 web sources + 2 YouTube channels.

**LoyalBooks genres** (41): Action and Adventure, Ancient Texts, Animals, Art Design and Architecture,
Biography and Memoir, Children in Fiction, Children Non-fiction, Classics (Antiquity),
Comedy and Humour, Drama, Early Modern, Fantasy, General Fiction, Historical Fiction,
History, Horror and Supernatural Fiction, Humor, Instruction and How-To, Language,
Literary Fiction, Love Romance and Marriage, Modern (19th C), Music and Theatre,
Myths Legends and Fairy Tales, Nature and Wildlife, Non-fiction, Philosophy, Poetry,
Politics and Economics, Psychology, Religion, Science, Science Fiction, Short Stories,
Short Works, Spiritual and Inspirational, Sport and Recreation, Tragedy,
Travel and Geography, War and Military, Westerns.

## YouTube support

Install the optional YouTube extra:

```bash
pip install audiobooker[youtube]
# or
pip install tutubo
```

Use the pre-configured channel sources or define your own:

```python
from audiobooker.scrappers.youtube import HorrorBabble, TheCybrarian, YoutubeChannelSource
from audiobooker.base import BookAuthor

# Pre-configured channels
for book in HorrorBabble().iterate_all():
    print(book.title, book.streams)  # streams = YouTube watch URLs

for book in TheCybrarian().search_by_title("Conan"):
    print(book.title, book.runtime)

# Custom channel
my_channel = YoutubeChannelSource(
    channel_url="https://www.youtube.com/@SomeChannel/videos",
    authors=[BookAuthor(last_name="Unknown")],
    tags=["Audiobook"],
    language="en",
    min_runtime=300,  # skip anything under 5 minutes
)
for book in my_channel.iterate_all():
    print(book.title)

# Custom playlist
from audiobooker.scrappers.youtube import YoutubePlaylistSource
playlist = YoutubePlaylistSource(
    playlist_url="https://www.youtube.com/playlist?list=PLxxxxxx",
    authors=[BookAuthor(last_name="Various")],
    tags=["Horror"],
)
for book in playlist.iterate_all():
    print(book.title, book.runtime)
```

When tutubo is installed, `TheCybrarian` and `HorrorBabble` are automatically included
in `ALL_SOURCES` and participate in all unified `search*()` calls.

## Install

```bash
pip install audiobooker
```

## Unified search

Search all sources in parallel — results arrive sorted by relevance score.

```python
from audiobooker import search, search_by_author, search_by_title, search_by_tag, search_by_narrator

# Search all sources, deduplicated, scored, timeout 30s
for book in search("Lovecraft", max_per_source=5, timeout=30):
    print(f"[{book.score:.2f}] [{book.source}] {book.title}")
    print(f"  author={book.authors}  streams={len(book.streams)}")

# Targeted searches
for book in search_by_author("Dickens", max_per_source=5):
    print(book.title)

for book in search_by_title("Sherlock Holmes", max_per_source=5):
    print(book.title, book.language)

for book in search_by_tag("horror", max_per_source=5):
    print(book.title)

for book in search_by_narrator("Frank Muller", max_per_source=5):
    print(book.title, book.narrator)
```

### Search parameters

| Parameter | Default | Description |
|---|---|---|
| `sources` | all 7 | list of instantiated `AudioBookSource` objects to restrict search |
| `max_per_source` | 10 | max results collected per source before stopping that thread |
| `timeout` | 30.0 | seconds before slow sources are cancelled |
| `deduplicate` | True | skip books with identical title+author from a second source |

### Scoring

Each result carries a `score` field (0.0–1.0) computed by `score_book()`.
Weights depend on the search method so cross-field contamination is avoided:

| Method | Title | Author | Tag | Narrator |
|---|---|---|---|---|
| `search_by_title` | 100% | — | — | — |
| `search_by_author` | — | 100% | — | — |
| `search_by_tag` | — | — | 100% | — |
| `search_by_narrator` | — | — | — | 100% |
| `search` | 55% | 30% | 10% | 5% |

Uses [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) WRatio — handles token
reordering, typos, and partial matches. Title scoring adds a containment bonus when
all query words appear verbatim in the title.

Results scoring below **0.45** are filtered out automatically.

## Per-source usage

All scrapers share the same interface via `AudioBookSource`.

```python
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker.scrappers.darkerprojects import DarkerProjects
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

# Common interface
source = Librivox()
source.search(query)               # title + author + tag
source.search_by_title(query)
source.search_by_author(query)
source.search_by_tag(query)
source.search_by_narrator(query)
source.iterate_all()               # every book in the catalogue
source.iterate_popular()           # front-page / curated selection
source.iterate_by_author(author)
source.iterate_by_tag(tag)
```

### Librivox — REST API, fastest source

```python
lv = Librivox()
for book in lv.search_by_author("Lovecraft", max_per_source=5):
    print(book.title, book.runtime, "s")
for book in lv.search_by_narrator("LibriVox"):
    print(book.title, book.narrator)
```

### LoyalBooks — sitemap + genre pages

```python
lb = LoyalBooks()
for book in lb.search_by_tag("Horror and Supernatural Fiction"):
    print(book.title)             # uses genre page, not linear scan
for book in lb.iterate_popular():
    print(book.title)             # front-page featured books
```

### Linear-scan sources

GoldenAudioBooks, AudioAnarchy, DarkerProjects, HPTalesAudioBooks, and
StephenKingAudioBooks all support `iterate_all()`. StephenKingAudioBooks also
has a native site search for title/author queries.

```python
for book in AudioAnarchy().iterate_all():
    print(book.title, book.tags)   # tags: ["Anarchy"] or ["Anarchy", "Radio Drama"]

for book in DarkerProjects().iterate_popular():
    print(book.title)              # front-page shows
```

## AudioBook dataclass

```python
@dataclass
class AudioBookChapter:
    title: str   = ""
    offset: float = 0.0   # seconds from start of book
    runtime: float = 0.0  # seconds
    stream: str  = ""     # per-chapter audio URL
    image: str   = ""

@dataclass
class AudioBook:
    title: str          = ""
    description: str    = ""
    image: str          = ""   # cover art URL
    language: str       = ""   # ISO 639-1 code (normalised from source)
    authors: List[BookAuthor]              = field(default_factory=list)
    tags: List[str]                        = field(default_factory=list)
    streams: List[str]                     = field(default_factory=list)  # direct audio URLs
    narrator: Optional[AudiobookNarrator]  = None  # primary reader
    narrators: List[AudiobookNarrator]     = field(default_factory=list)  # full reader cast
    chapters: List[AudioBookChapter]       = field(default_factory=list)
    genres: List[str]                      = field(default_factory=list)  # taxonomy genres
    year: int           = 0
    runtime: int        = 0    # seconds (where available)
    source: str         = ""   # e.g. "Librivox", "LoyalBooks"
    score: float        = 0.0  # relevance score from last search (0..1)
    codec: str          = ""   # e.g. "mp3"
    bitrate: str        = ""   # e.g. "128"
    external_ids: dict  = field(default_factory=dict)  # e.g. {"librivox_id": "47"}

    def has_live_streams(self) -> bool: ...  # HEAD-checks stream URLs
```

`AudioBook` supports `==` and `hash()` based on `(title, sorted authors)` — use a
`set` to deduplicate across sources.

## Utilities

```python
from audiobooker import score_book, iter_sitemap_urls, check_url_availability, normalize_language

# Score a book against a query manually
score = score_book("Lovecraft", book, method="search_by_author")

# Walk any sitemap or sitemap index recursively
for url in iter_sitemap_urls("https://example.com/sitemap.xml"):
    print(url)

# Check if a stream URL is reachable
if check_url_availability("https://example.com/book.mp3"):
    print("live")

# Normalise language strings to ISO 639-1
normalize_language("English")   # → "en"
normalize_language("en-US")     # → "en"
```

## mediavocab integration

`mediavocab` is a hard runtime dependency. Every `AudioBook` can be projected
into the typed `mediavocab.Release` schema via `audiobook_to_release()`:

```python
from audiobooker import search, audiobook_to_release

# Search → typed mediavocab Release with parsed_license filtering
for book in search("Lovecraft", max_per_source=3):
    release = audiobook_to_release(book)
    if release.parsed_license and release.parsed_license.is_open():
        # public domain / CC-licensed: free to redistribute
        print(release.work.title, release.parsed_license.identifier)
```

The converter populates a wide swath of the `Release` / `Work` schema:

| mediavocab field            | Source data                                  |
|---|---|
| `Work.title`, `Work.year`, `Work.runtime`, `Work.language` | direct |
| `Work.content_genres`       | `AudioBook.genres` (e.g. LibriVox `genres`)  |
| `Work.credits`              | authors → `RelationRole.CREATOR`, every reader → `RelationRole.PERFORMER` |
| `Work.external_ids`         | `librivox_id` and any other typed ID the source supplied |
| `Release.chapters`          | `AudioBook.chapters` → `Chapter(offset, end, title)` |
| `Release.codec`, `Release.bitrate` | LibriVox publishes 128 kbps MP3 by policy |
| `Release.audio_language`    | mirrors `Work.language` |
| `Release.license`           | `public_domain` for LibriVox / LoyalBooks |
| `Release.release_date`      | `IsoDate`-compatible `YYYY` from `AudioBook.year` |

LibriVox emits one `Release` per book with full per-section `chapters` and a
deduplicated reader cast. Other sources populate whatever subset their public
data exposes — fields are only set when the source actually carries the data.

## Error handling

Network failures and malformed pages are swallowed per-item — a bad page never
aborts an `iterate_all()` run. If a source site is down or has restructured its
HTML, that scraper silently yields nothing.

## License

MIT
