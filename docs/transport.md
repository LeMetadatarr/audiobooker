# HTTP Transport

`default_session()` — `audiobooker/transport.py:22`

Returns the HTTP session used by all scrapers. Two backends are supported:

| Backend | When used | Package |
|---|---|---|
| `requests.Session` | default | `requests` (always installed) |
| `curl_cffi.requests.Session` | `AUDIOBOOKER_TRANSPORT=curl_cffi` + package importable | `pip install audiobooker[stealth]` |

`curl_cffi` impersonates a real browser TLS fingerprint and can bypass
bot-protection on scraping targets that reject `requests`.

## Environment variable

```bash
# Install the extra first
pip install audiobooker[stealth]

# Enable for the process
AUDIOBOOKER_TRANSPORT=curl_cffi python myscript.py
```

If `AUDIOBOOKER_TRANSPORT=curl_cffi` is set but `curl_cffi` is not installed,
`default_session()` silently falls back to a plain `requests.Session`.

## Per-instance injection

Every `AudioBookSource.__init__` accepts an optional `session` parameter —
`audiobooker/scrappers/__init__.py:21`.

```python
from curl_cffi import requests as cffi_requests
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks

session = cffi_requests.Session(impersonate="chrome")
lv = Librivox(session=session)
ga = GoldenAudioBooks(session=session)
```

When `session=None` (the default), the class-level `AudioBookSource.session`
is used — a module-level `requests.Session` initialised with a random
`User-Agent`.

## Pluggable session — `audiobooker/scrappers/__init__.py:14`

Any object that satisfies the `requests.Session` interface works:
`get()`, `post()`, `Session.headers`. The `curl_cffi.requests.Session` is
API-compatible.

## User-Agent rotation

`random_user_agent()` — `audiobooker/utils.py` — picks a random modern
browser UA string on every call. Both `default_session()` and the
module-level `_default_session` apply it at construction time.
