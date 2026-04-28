"""Cache and download — download once, play instantly thereafter.

Run:
  python examples/cache_usage.py
  python -m audiobooker.cache download "Dracula"
  python -m audiobooker.cache play "Dracula"
  python -m audiobooker.cache list
"""
import tempfile
from pathlib import Path

from audiobooker.base import AudioBook, BookAuthor
from audiobooker.cache import (
    download, is_cached, cached_paths, list_cached, clear_cache,
)
from audiobooker.index import BookIndex

# ---------------------------------------------------------------------------
# 1. Set up a temporary cache so this demo doesn't touch ~/.cache
# ---------------------------------------------------------------------------
tmp_cache = Path(tempfile.mkdtemp())
print(f"Using temporary cache: {tmp_cache}\n")

# ---------------------------------------------------------------------------
# 2. Build a small in-memory index with one book
# ---------------------------------------------------------------------------
book = AudioBook(
    title="The Call of Cthulhu",
    authors=[BookAuthor(first_name="H. P.", last_name="Lovecraft")],
    streams=["https://www.archive.org/download/call_of_cthulhu_0809_librivox/callofcthulhu_01_lovecraft.mp3"],
    runtime=2640,
    source="Librivox",
    language="en",
    tags=["Horror", "Weird Fiction"],
)

# ---------------------------------------------------------------------------
# 3. Cache status before download
# ---------------------------------------------------------------------------
print(f"Cached before download: {is_cached(book, tmp_cache)}")

# ---------------------------------------------------------------------------
# 4. Download (uncomment to actually fetch — requires network)
# ---------------------------------------------------------------------------
# paths = download(book, cache_root=tmp_cache)
# print(f"\nDownloaded to: {paths}")

# ---------------------------------------------------------------------------
# 5. Duration filters in BookIndex
# ---------------------------------------------------------------------------
print("\n=== Duration filters ===\n")

with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
    db_path = f.name

idx = BookIndex(db_path)

books = [
    AudioBook(title="Short Story", authors=[BookAuthor(last_name="A")],
              runtime=600, streams=["http://x.com/a.mp3"], source="S"),
    AudioBook(title="Medium Novel", authors=[BookAuthor(last_name="B")],
              runtime=7200, streams=["http://x.com/b.mp3"], source="S"),
    AudioBook(title="Epic Saga", authors=[BookAuthor(last_name="C")],
              runtime=36000, streams=["http://x.com/c.mp3"], source="S"),
]
for b in books:
    idx._upsert(b)
idx._con.commit()
idx._fts_rebuild()

print("All books:")
for b in idx.iterate_all():
    print(f"  {b.title:20s}  {b.runtime // 60} min")

print("\nOver 1 hour (min_duration=3600):")
for b in idx.search_by_author("", min_score=0.0, max_results=0, min_duration=3600):
    print(f"  {b.title}")

print("\nUnder 2 hours (max_duration=7200):")
for b in idx.search_by_author("", min_score=0.0, max_results=0, max_duration=7200):
    print(f"  {b.title}")

idx.close()

# ---------------------------------------------------------------------------
# 6. CLI quick-reference
# ---------------------------------------------------------------------------
print("\nCLI:")
print('  python -m audiobooker.cache download "Dracula"')
print('  python -m audiobooker.cache play "Dracula"')
print("  python -m audiobooker.cache list")
print("  python -m audiobooker.cache clear")
print('  python -m audiobooker.index search "Horror" --method search_by_tag --min-duration 3600')
