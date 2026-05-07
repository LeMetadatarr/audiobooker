"""08 — YouTube audiobook sources (TheCybrarian, HorrorBabble, custom channel).

Requires: pip install audiobooker[youtube]
Run:      python examples/08_youtube_audiobooks.py
"""
try:
    from audiobooker.scrappers.youtube import (
        TheCybrarian, HorrorBabble, YoutubeChannelSource, YoutubePlaylistSource,
    )
    from audiobooker.base import BookAuthor
except ImportError:
    print("tutubo not installed. Run: pip install audiobooker[youtube]")
    raise SystemExit(1)

# Pre-configured channels
print("=== TheCybrarian — search by title ===")
for book in TheCybrarian().search_by_title("Conan"):
    print(f"  {book.title!r}  runtime={book.runtime}s  streams={book.streams[:1]}")
    break

print("\n=== HorrorBabble — first 3 from iterate_all ===")
count = 0
for book in HorrorBabble().iterate_all():
    print(f"  {book.title!r}  tags={book.tags}")
    count += 1
    if count >= 3:
        break

# Custom channel
print("\n=== Custom YoutubeChannelSource ===")
channel = YoutubeChannelSource(
    channel_url="https://www.youtube.com/@TheCybrarian/videos",
    authors=[BookAuthor(last_name="Howard")],
    tags=["Sword and Sorcery"],
    language="en",
    min_runtime=300,
)
for book in channel.search_by_title("Solomon Kane"):
    print(f"  {book.title!r}  {book.streams[:1]}")
    break

# Unified search includes YouTube sources when tutubo is installed
print("\n=== Unified search (ALL_SOURCES includes YouTube) ===")
from audiobooker import search, ALL_SOURCES
yt_names = [cls.__name__ for cls in ALL_SOURCES if "youtube" in cls.__module__]
print(f"YouTube sources in ALL_SOURCES: {yt_names}")
