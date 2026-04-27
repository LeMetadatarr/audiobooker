"""Iterate GoldenAudioBooks catalogue."""
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks

scraper = GoldenAudioBooks()

print("=== GoldenAudioBooks catalogue (first 5) ===")
for i, book in enumerate(scraper.iterate_all()):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  [{i+1}] {book.title!r}  author={authors or '?'}  streams={len(book.streams)}")
    if i >= 4:
        break
