"""Search and iterate Stephen King audiobooks."""
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

sk = StephenKingAudioBooks()

print("=== search: Dark Tower ===")
for book in sk.search("Dark Tower"):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  {book.title!r}  narrator={book.narrator}  streams={len(book.streams)}")
    break

print("\n=== search: Shining ===")
for book in sk.search("Shining"):
    print(f"  {book.title!r}  year={book.year}  streams={book.streams[:1]}")
    break
