# Unified Search

`audiobooker.search` runs all sources in parallel threads and yields results
sorted by relevance score.

## Functions

```python
from audiobooker import search, search_by_title, search_by_author, search_by_tag, search_by_narrator
```

All five functions share the same signature:

```python
def search(
    query: str,
    sources: Optional[List[AudioBookSource]] = None,  # default: all sources
    max_per_source: int = 10,   # 0 = unlimited
    timeout: Optional[float] = 30.0,   # seconds; None = wait forever
    deduplicate: bool = True,
) -> Iterable[AudioBook]: ...
```

Results arrive after the timeout (or when all sources finish) and are sorted
by `score` descending. Books scoring below **0.45** are filtered out.

## Parameters

| Parameter | Default | Description |
|---|---|---|
| `query` | n/a | Search string |
| `sources` | all sources | List of instantiated `AudioBookSource` objects |
| `max_per_source` | 10 | Max results collected per source before that thread stops |
| `timeout` | 30.0 | Seconds before slow sources are cancelled |
| `deduplicate` | True | Skip books with identical title+author already seen from another source |

## Choosing the right function

| Function | Scores on | Use when |
|---|---|---|
| `search` | title 55% + author 30% + tag 10% + narrator 5% | General keyword search |
| `search_by_title` | title 100% | You know the title |
| `search_by_author` | author 100% | You know the author's name |
| `search_by_tag` | tag 100% | You want a genre or category |
| `search_by_narrator` | narrator 100% | You want a specific reader |

Using the wrong function causes cross-field contamination.
`search_by_title("Harry Potter")` will not boost Beatrix Potter because author
is not scored.

## Restricting to specific sources

Pass a `sources=` list of instantiated source objects:

```python
from audiobooker import search_by_author
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks

for book in search_by_author("Lovecraft", sources=[Librivox(), LoyalBooks()], timeout=15):
    print(book.title)
```

## Using YouTube sources in search

YouTube sources are regular `AudioBookSource` objects and work with `sources=`:

```python
from audiobooker import search
from audiobooker.scrappers.youtube import TheCybrarian, HorrorBabble

for book in search("Conan", sources=[TheCybrarian()], timeout=20):
    print(f"[{book.score:.2f}] {book.title}")
```

When `tutubo` is installed, `TheCybrarian` and `HorrorBabble` are automatically
included in `ALL_SOURCES` and participate in every `search*()` call.

## ALL_SOURCES

`audiobooker.search.ALL_SOURCES` is the list of source *classes* used when
`sources=None`:

```python
from audiobooker.search import ALL_SOURCES
print([cls.__name__ for cls in ALL_SOURCES])
# ['Librivox', 'LoyalBooks', 'StephenKingAudioBooks', 'GoldenAudioBooks',
#  'AudioAnarchy', 'DarkerProjects', 'HPTalesAudioBooks',
#  'TheCybrarian', 'HorrorBabble']   # last two only when tutubo installed
```

## Scoring details

See [scoring.md](scoring.md).

---
[← Getting Started](getting-started.md) · [Home](README.md) · [Scoring →](scoring.md)
