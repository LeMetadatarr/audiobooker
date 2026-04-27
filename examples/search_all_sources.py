"""Search a query across sources that have native search support.

Sources backed by a real API or site search (Librivox, LoyalBooks,
StephenKingAudioBooks) return targeted results quickly.

Other sources (GoldenAudioBooks, AudioAnarchy, DarkerProjects,
HPTalesAudioBooks) only support linear iteration — use their
iterate_all() directly rather than search() for those.
"""
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

QUERY = "Lovecraft"

SOURCES = [
    ("Librivox",              Librivox()),
    ("LoyalBooks",            LoyalBooks()),
    ("StephenKingAudioBooks", StephenKingAudioBooks()),
]

for name, source in SOURCES:
    results = []
    try:
        for book in source.search(QUERY):
            results.append(book)
            if len(results) >= 3:
                break
    except Exception as e:
        print(f"[{name}] ERROR: {e}")
        continue

    if results:
        print(f"\n[{name}] {len(results)} result(s) for '{QUERY}':")
        for book in results:
            authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
            print(f"  - {book.title!r}  author={authors or '?'}  streams={len(book.streams)}")
    else:
        print(f"\n[{name}] no results for '{QUERY}'")
