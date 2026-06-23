"""01 — Quickstart: search LibriVox for one book.

Requires: pip install audiobooker
Run:      python examples/01_quickstart.py
"""
from audiobooker.scrappers.librivox import Librivox

lv = Librivox()
book = next(lv.search_by_title("Dracula"), None)
if book is None:
    print("No results.")
else:
    print(f"Title:   {book.title}")
    print(f"Authors: {[f'{a.first_name} {a.last_name}'.strip() for a in book.authors]}")
    print(f"Runtime: {book.runtime // 60} min")
    print(f"Streams: {len(book.streams)}")
    if book.streams:
        print(f"  first: {book.streams[0]}")
    print(f"Chapters: {len(book.chapters)}")
