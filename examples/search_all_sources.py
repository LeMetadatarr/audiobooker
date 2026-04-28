"""Unified parallel search across all sources using audiobooker.search.

Sources with native search (Librivox, LoyalBooks, StephenKingAudioBooks)
return results quickly. Linear-scan sources (GoldenAudioBooks, AudioAnarchy,
DarkerProjects, HPTalesAudioBooks) will be cut off by the timeout if the
query doesn't appear in their early catalogue pages.
"""
import time
from audiobooker import search, search_by_author
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

# --- fast sources only (native API/site search) ---
FAST_SOURCES = [Librivox(), LoyalBooks(), StephenKingAudioBooks()]

print("=== search('Lovecraft') — all sources, 15s timeout ===\n")
t0 = time.time()
for book in search("Lovecraft", max_per_source=3, timeout=15):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  {book.title!r}")
    print(f"    author={authors or '?'}  streams={len(book.streams)}  runtime={book.runtime}s")
print(f"\nDone in {time.time() - t0:.1f}s\n")

# --- targeted search across fast sources ---
print("=== search_by_author('Lovecraft') — fast sources only ===\n")
t0 = time.time()
for book in search_by_author("Lovecraft", sources=FAST_SOURCES, max_per_source=3, timeout=15):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors)
    print(f"  {book.title!r}  author={authors or '?'}")
print(f"\nDone in {time.time() - t0:.1f}s")
