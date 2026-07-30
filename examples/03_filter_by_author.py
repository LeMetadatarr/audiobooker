"""03 — Author search with score display and language filter.

Requires: pip install audiobooker
Run:      python examples/03_filter_by_author.py
"""
from audiobooker import search_by_author

author = "H.P. Lovecraft"
print(f"Searching for author {author!r}...\n")

results = list(search_by_author(author, max_per_source=5, timeout=30))
results.sort(key=lambda b: b.score, reverse=True)

for book in results:
    lang = f"[{book.language}]" if book.language else ""
    print(f"[{book.score:.2f}] {lang} [{book.source}] {book.title!r}")

print(f"\n{len(results)} total results")

# Filter to English only
en = [b for b in results if b.language == "en"]
print(f"{len(en)} English results")
