"""05 — Play a book from cache (downloads first if not cached).

Uses the system default audio player: xdg-open (Linux), open (macOS),
start (Windows).

Requires: pip install audiobooker
Run:      python examples/05_play_with_cache.py
"""
from audiobooker.scrappers.librivox import Librivox
from audiobooker.cache import play, is_cached

book = next(Librivox().search_by_title("The Yellow Wallpaper"), None)
if book is None:
    print("Book not found.")
else:
    print(f"Title:   {book.title!r}")
    print(f"Cached:  {is_cached(book)}")
    print("Playing stream 0 (downloads if needed)...")
    play(book, stream=0)
    print("Player launched.")
