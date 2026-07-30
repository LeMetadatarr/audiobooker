"""07 — Inject a custom HTTP session; opt into curl_cffi stealth backend.

Two patterns:
  A. Inject any requests-compatible session per scraper instance.
  B. Use AUDIOBOOKER_TRANSPORT=curl_cffi + default_session() to get the
     stealth backend automatically (requires pip install audiobooker[stealth]).

Requires: pip install audiobooker
          pip install audiobooker[stealth]  # for pattern B
Run:      python examples/07_custom_session.py
"""
import os
import requests

from audiobooker.scrappers.librivox import Librivox

# Pattern A — custom requests.Session with a proxy or extra headers
session_a = requests.Session()
session_a.headers["X-Custom-Header"] = "demo"
lv_a = Librivox(session=session_a)
book = next(lv_a.search_by_title("Frankenstein"), None)
print(f"Pattern A: {book.title if book else 'no result'}")

# Pattern B — curl_cffi stealth session via transport helper
os.environ["AUDIOBOOKER_TRANSPORT"] = "curl_cffi"
try:
    from audiobooker.transport import default_session
    session_b = default_session()
    backend = type(session_b).__module__.split(".")[0]
    print(f"Pattern B: session backend = {backend}")
    lv_b = Librivox(session=session_b)
    book2 = next(lv_b.search_by_title("Frankenstein"), None)
    print(f"  result: {book2.title if book2 else 'no result'}")
except ImportError:
    print("Pattern B: curl_cffi not installed — fell back to requests (expected without [stealth])")
