"""YouTube channel and playlist sources via audiobooker.

Requires: pip install audiobooker[youtube]

Demonstrates:
  - YoutubeChannelSource  — iterate and search a YouTube channel
  - YoutubePlaylistSource — iterate and search a specific playlist
  - Pre-configured channels: TheCybrarian, HorrorBabble
  - Using a YouTube source inside unified search()
"""
import time
from audiobooker.base import BookAuthor
from audiobooker.scrappers.youtube import (
    TheCybrarian,
    HorrorBabble,
    YoutubeChannelSource,
    YoutubePlaylistSource,
)
from audiobooker import search

# ---------------------------------------------------------------------------
# 1. Pre-configured channel — TheCybrarian (Robert E. Howard)
# ---------------------------------------------------------------------------
print("=== TheCybrarian — first 5 videos ===\n")
count = 0
for book in TheCybrarian().iterate_all():
    print(f"  {book.title!r}  runtime={book.runtime}s  streams={book.streams[0]}")
    count += 1
    if count >= 5:
        break
print()

# ---------------------------------------------------------------------------
# 2. Pre-configured channel — HorrorBabble (Horror fiction)
# ---------------------------------------------------------------------------
print("=== HorrorBabble.search_by_title('Lovecraft') ===\n")
for book in HorrorBabble().search_by_title("Lovecraft"):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  {book.title!r}  tags={book.tags}")
    break  # just show the first hit
print()

# ---------------------------------------------------------------------------
# 3. Custom channel source
# ---------------------------------------------------------------------------
print("=== Custom YoutubeChannelSource — first 3 videos ===\n")
my_channel = YoutubeChannelSource(
    channel_url="https://www.youtube.com/@TheCybrarian/videos",
    authors=[BookAuthor(first_name="Robert E.", last_name="Howard")],
    tags=["Fantasy"],
    language="en",
    min_runtime=60,
)
count = 0
for book in my_channel.iterate_all():
    print(f"  {book.title!r}  source={book.source}")
    count += 1
    if count >= 3:
        break
print()

# ---------------------------------------------------------------------------
# 4. Playlist source
# ---------------------------------------------------------------------------
PLAYLIST_URL = "https://www.youtube.com/playlist?list=PL_I08nip76cJMME746302lPoB37d8RnRU"

print(f"=== YoutubePlaylistSource — {PLAYLIST_URL!r} ===\n")
playlist = YoutubePlaylistSource(
    playlist_url=PLAYLIST_URL,
    authors=[BookAuthor(last_name="Lovecraft")],
    tags=["Horror", "Lovecraft"],
    language="en",
    min_runtime=60,
)
count = 0
for book in playlist.iterate_all():
    print(f"  {book.title!r}  runtime={book.runtime}s")
    count += 1
print(f"  ({count} videos total)")
print()

# ---------------------------------------------------------------------------
# 5. YouTube channel as a sources= argument to unified search()
# ---------------------------------------------------------------------------
print("=== search('Conan', sources=[TheCybrarian()], timeout=20) ===\n")
t0 = time.time()
for book in search("Conan", sources=[TheCybrarian()], max_per_source=5, timeout=20):
    print(f"  [{book.score:.2f}] {book.title!r}")
print(f"\nDone in {time.time() - t0:.1f}s")
