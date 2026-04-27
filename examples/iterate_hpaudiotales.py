"""Iterate Harry Potter audio tales."""
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks

scraper = HPTalesAudioBooks()

print("=== HP Audio Tales catalogue (first 3) ===")
for i, book in enumerate(scraper.iterate_all()):
    print(f"  [{i+1}] {book.title!r}")
    print(f"       tags={book.tags[:3]}  streams={len(book.streams)}")
    if i >= 2:
        break
