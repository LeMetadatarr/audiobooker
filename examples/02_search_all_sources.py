"""02 — Unified parallel search across all sources.

Requires: pip install audiobooker
Run:      python examples/02_search_all_sources.py
"""
from audiobooker import search

query = "Sherlock Holmes"
print(f"Searching all sources for {query!r} (timeout=30s)...\n")

for book in search(query, max_per_source=3, timeout=30):
    authors = ", ".join(f"{a.first_name} {a.last_name}".strip() for a in book.authors) or "?"
    runtime = f"{book.runtime // 60}min" if book.runtime else "?"
    print(f"[{book.score:.2f}] [{book.source}] {book.title!r}")
    print(f"         {authors}  runtime={runtime}  streams={len(book.streams)}")
