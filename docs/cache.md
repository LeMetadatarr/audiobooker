# Cache & Download

`audiobooker.cache` downloads audiobook streams to a local directory so
subsequent plays are instant without any network access.

```bash
pip install audiobooker requests   # requests is required for downloads
```

## Cache layout

```
~/.cache/audiobooker/
    <book_hash>/
        meta.json          ← serialised book metadata
        audio.mp3          ← downloaded stream file(s)
```

## Download

```python
from audiobooker.cache import download, is_cached, cached_paths

book = next(iter(Librivox().search_by_title("Dracula")))

download(book)              # fetch all streams → cache
download(book, stream=0)    # first stream only

if is_cached(book):
    paths = cached_paths(book)   # list of local Path objects
```

`download()` skips files that are already in the cache. It is safe to call
repeatedly. A `.part` temporary file is used during download. It is renamed on
completion and deleted on error, so partial downloads never pollute the cache.

## Play

```python
from audiobooker.cache import play

play(book)           # download if needed, then open with system player
play(book, stream=0) # specific stream index
```

`play()` uses `xdg-open` (Linux), `open` (macOS), or `os.startfile` (Windows)
to hand the file off to the system's default audio player.

## List and clear

```python
from audiobooker.cache import list_cached, clear_cache

for book in list_cached():
    print(book.title)

clear_cache(book)     # remove one book
clear_cache()         # wipe entire cache
```

## Custom cache directory

```python
from pathlib import Path
from audiobooker.cache import download, play

download(book, cache_root=Path("/data/audiobooks"))
play(book, cache_root=Path("/data/audiobooks"))
```

## Bulk download: example with TheCybrarian

Download every audiobook from a YouTube channel in one pass.
Already-cached files are skipped automatically.

```python
from audiobooker.cache import download, is_cached
from audiobooker.scrappers.youtube import TheCybrarian

for book in TheCybrarian().iterate_all():
    if is_cached(book):
        print(f"[cached] {book.title}")
        continue
    print(f"[downloading] {book.title}")
    paths = download(book, stream=0, progress=True)
    if paths:
        print(f"  → {paths[0]}")
```

`TheCybrarian` ships with `title_blacklist=["update"]` so channel-update
announcement videos are filtered out before download.

See `examples/download_cybrarian.py` for the full runnable version with
`--dry-run` and `--indexed` (index channel first, then download from index).

## CLI

```bash
# Download by title (searches local index first, falls back to Librivox)
python -m audiobooker.cache download "Dracula"
python -m audiobooker.cache download "Dracula" --stream 0

# Play (downloads if not cached)
python -m audiobooker.cache play "Dracula"

# Show cache info for a book
python -m audiobooker.cache info "Dracula"

# List all cached books
python -m audiobooker.cache list

# Clear entire cache
python -m audiobooker.cache clear

# Custom cache path
python -m audiobooker.cache --cache /data/audiobooks download "Dracula"
```

## Duration filters (BookIndex)

All `BookIndex.search_*` methods accept `min_duration` and `max_duration`
parameters (in seconds) to filter by runtime:

```python
from audiobooker.index import BookIndex

idx = BookIndex()

# Short stories only (under 30 minutes)
idx.search_by_tag("Horror", max_duration=1800)

# Full novels (over 2 hours)
idx.search_by_author("Dickens", min_duration=7200)

# Specific range: 1 to 4 hours
idx.search("Lovecraft", min_duration=3600, max_duration=14400)
```

CLI:

```bash
python -m audiobooker.index search "horror" --method search_by_tag \
    --min-duration 3600 --max-duration 14400
```

---
[← Local Index](index.md) · [Home](README.md) · [mediavocab Converters →](converters.md)
