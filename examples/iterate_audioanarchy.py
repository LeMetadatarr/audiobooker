"""Iterate all AudioAnarchy books (political/anarchist audiobooks)."""
from audiobooker.scrappers.audioanarchy import AudioAnarchy

scraper = AudioAnarchy()

print("=== AudioAnarchy catalogue (first 5) ===")
for i, book in enumerate(scraper.iterate_all()):
    print(f"  [{i+1}] {book.title!r}")
    print(f"       streams={book.streams[:1]}")
    if i >= 4:
        break
