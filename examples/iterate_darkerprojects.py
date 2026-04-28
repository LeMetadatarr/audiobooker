"""Iterate Darker Projects audio dramas."""
from audiobooker.scrappers.darkerprojects import DarkerProjects

scraper = DarkerProjects()

print("=== Darker Projects catalogue (first 5) ===")
for i, book in enumerate(scraper.iterate_all()):
    print(f"  [{i+1}] {book.title!r}")
    print(f"       streams={len(book.streams)}  desc={book.description[:60]!r}")
    if i >= 4:
        break
