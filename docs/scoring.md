# Scoring

Every `AudioBook` returned by a `search*()` call carries a `score` field (0.0–1.0)
computed by `score_book()`.

## score_book()

```python
from audiobooker import score_book

score = score_book(query, book, method="search")
```

`method` must match the search function name: `"search"`, `"search_by_title"`,
`"search_by_author"`, `"search_by_tag"`, or `"search_by_narrator"`.

## Field weights per method

| Method | Title | Author | Tag | Narrator |
|---|---|---|---|---|
| `search` | 55% | 30% | 10% | 5% |
| `search_by_title` | 100% | — | — | — |
| `search_by_author` | — | 100% | — | — |
| `search_by_tag` | — | — | 100% | — |
| `search_by_narrator` | — | — | — | 100% |

Isolating weights prevents cross-field contamination: `search_by_title("Harry Potter")`
will not rank *Beatrix Potter* higher just because "Potter" matches the author.

## Similarity metric

All field scores use [rapidfuzz](https://github.com/rapidfuzz/RapidFuzz) `WRatio`
(case-insensitive), normalized to 0.0–1.0.

`WRatio` is a meta-scorer that tries several strategies (full string, partial,
token sort, token set) and returns the best. It handles:
- Token reordering: `"Sherlock Holmes"` ≈ `"Holmes Sherlock"`
- Partial matches: `"Lovecraft"` matches `"H. P. Lovecraft"`
- Typos and minor OCR errors

### Title bonus

For title scoring, a +0.15 bonus is added when **all** query words appear
verbatim (case-insensitive) in the title. This ensures `"Harry Potter"` scores
higher for titles that actually contain both words, versus titles that just
happen to share a token like "Potter".

The bonus is capped at 1.0.

## Score threshold

Results scoring below **0.45** are filtered out by `_parallel_search` before
they are yielded. This is not configurable via the public API; it exists to
suppress near-random low-quality matches from linear-scan sources.

## fuzzy_match()

The base-level `fuzzy_match(query, text, threshold=0.80)` is used in per-source
`search_by_*` methods to decide whether to yield a book at all, before unified
scoring takes over.

Single-word queries use WRatio directly (it handles partial matching internally).
Multi-word queries also use WRatio on the full string; the `search_by_author`
base class adds a **last-token anchor** — the final word of the query (typically
a surname) must independently match the candidate's last name before the full
comparison runs. This prevents `"Stephen King"` from matching `"Stephen Vincent Benét"`
(WRatio token-set would score that ≥ 0.80 because of shared "Stephen").
