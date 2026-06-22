# mediavocab Converters

`audiobook_to_release()` — see `audiobooker/converters.py`

Converts an `AudioBook` into a `mediavocab.Release`. `mediavocab` is a required
runtime dependency.

```python
from audiobooker import audiobook_to_release
from audiobooker.scrappers.librivox import Librivox

book = next(Librivox().search_by_author("Lovecraft"))
release = audiobook_to_release(book)

work = release.work
print(work.title, work.year, work.language)
print(release.license, release.codec, release.bitrate)
```

## Field mapping

| `MvRelease` / `Work` field | Source in `AudioBook` |
|---|---|
| `work.title` | `AudioBook.title` |
| `work.year` | `AudioBook.year` (int → `int \| None`) |
| `work.runtime` | `AudioBook.runtime` (int seconds → `float \| None`) |
| `work.language` | `AudioBook.language` (already ISO 639-1) |
| `work.media_type` | hard-coded `MediaType.AUDIOBOOK` |
| `work.content_genres` | `AudioBook.genres`; falls back to `[]` (not `tags`) |
| `work.credits` | authors → `RelationRole.CREATOR`; narrators → `RelationRole.PERFORMER` |
| `work.external_ids` | `AudioBook.external_ids` pass-through + `audiobooker_id` (SHA-256 stable ID) |
| `work.extra` | source name, score, tags, stream URLs, description |
| `release.uri` | `AudioBook.streams[0]` (empty string when no streams) |
| `release.image` | `AudioBook.image` |
| `release.stream_mode` | hard-coded `StreamMode.ON_DEMAND` |
| `release.release_date` | `str(AudioBook.year)` — ISO-compatible YYYY |
| `release.license` | `"public_domain"` for LibriVox and LoyalBooks; `""` otherwise |
| `release.codec` | `AudioBook.codec` |
| `release.bitrate` | `AudioBook.bitrate` |
| `release.audio_language` | mirrors `work.language` |
| `release.chapters` | `AudioBook.chapters` → `MvChapter(offset, end, title, image)` |
| `release.external_ids` | same as `work.external_ids` |

## Credits

Authors use `RelationRole.CREATOR`, `CreditSection.PRINCIPAL`.
Narrators use `RelationRole.PERFORMER`, `CreditSection.PRINCIPAL`.

`AudioBook.narrators` (plural) is the authoritative list. When only
`AudioBook.narrator` (singular) is set, `base.AudioBook.__post_init__`
promotes it to `narrators`; the converter deduplicates by `(first, last)`.

## License detection

Sources whose names contain `"librivox"` or `"loyalbooks"` (case-insensitive)
get `license="public_domain"`. All other sources get an empty string — the
converter never guesses.

## Chapter conversion

```python
MvChapter(
    offset=float(c.offset),
    title=c.title,
    image=c.image,
    end=(float(c.offset) + float(c.runtime)) if c.runtime else None,
)
```

## Checking openness

```python
lic = release.license   # None when no license is detected
if lic and lic.is_open():
    print("free to redistribute")
```
