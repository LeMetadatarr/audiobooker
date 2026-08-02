# HTTP Transport

`default_session()`, defined in `audiobooker/transport.py`, builds a session
you can inject into any scraper. It is not applied automatically — without
explicit injection, every scraper uses the shared class-level
`AudioBookSource.session`, a plain `requests.Session`.

`default_session()` picks a backend in this order:

| Backend | Chosen when | Package |
|---|---|---|
| `curl_cffi.requests.Session` | `AUDIOBOOKER_TRANSPORT=curl_cffi` + package importable | `pip install audiobooker[stealth]` |
| `unblock_requests.CloudflareSession` | `unblock_requests` importable | `pip install audiobooker[stealth]` |
| `requests.Session` | fallback | `requests` (always installed) |

`curl_cffi` impersonates a real browser TLS fingerprint. `unblock_requests`
routes through anti-bot bypass with a Wayback Machine fallback. Both are
optional; `default_session()` falls back to plain `requests` when neither is
installed.

## Environment variable

```bash
# Install the extra first
pip install audiobooker[stealth]

# Enable for the process
AUDIOBOOKER_TRANSPORT=curl_cffi python myscript.py
```

Setting `AUDIOBOOKER_TRANSPORT` only affects what `default_session()`
returns; it has no effect until you call `default_session()` and inject the
result into a scraper (see below). If `AUDIOBOOKER_TRANSPORT=curl_cffi` is
set but `curl_cffi` is not installed, `default_session()` silently falls
back to the next backend.

```python
import os
os.environ["AUDIOBOOKER_TRANSPORT"] = "curl_cffi"

from audiobooker.transport import default_session
from audiobooker.scrappers.librivox import Librivox

lv = Librivox(session=default_session())
```

## Per-instance injection

Every `AudioBookSource.__init__` accepts an optional `session` parameter, in
`audiobooker/scrappers/__init__.py:22`.

```python
from curl_cffi import requests as cffi_requests
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks

session = cffi_requests.Session(impersonate="chrome")
lv = Librivox(session=session)
ga = GoldenAudioBooks(session=session)
```

When `session=None` (the default), the class-level `AudioBookSource.session`
is used: a module-level `requests.Session` initialised with a random
`User-Agent`.

## Pluggable session, `audiobooker/scrappers/__init__.py:14`

Any object that satisfies the `requests.Session` interface works:
`get()`, `post()`, `Session.headers`. The `curl_cffi.requests.Session` is
API-compatible.

## User-Agent rotation

`random_user_agent()`, in `audiobooker/utils.py`, picks a random modern
browser UA string on every call. Both `default_session()` and the
module-level `_default_session` apply it at construction time.

---
[← mediavocab Converters](converters.md) · [Home](README.md) · [API Reference →](api.md)
