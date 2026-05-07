"""Pluggable HTTP transport for audiobooker.

By default, ``default_session()`` returns a ``requests.Session`` configured
with a randomized User-Agent header (matching the historical behaviour).

If the environment variable ``AUDIOBOOKER_TRANSPORT`` is set to
``curl_cffi`` and the optional ``curl_cffi`` package is importable
(install via the ``[stealth]`` extra), a ``curl_cffi.requests.Session``
is returned instead. ``curl_cffi`` impersonates a real browser's TLS
fingerprint and tends to bypass bot-protection on some scraping targets.

If ``curl_cffi`` is requested but not importable, we silently fall back
to the plain ``requests`` session so callers don't need to handle the
ImportError.
"""
import os

import requests

from audiobooker.utils import random_user_agent


def default_session():
    """Return the default HTTP session for audiobooker scrapers.

    Returns a ``curl_cffi.requests.Session`` if
    ``AUDIOBOOKER_TRANSPORT=curl_cffi`` is set in the environment AND
    ``curl_cffi`` is importable. Otherwise returns a standard
    ``requests.Session`` with a randomized User-Agent header.
    """
    if os.environ.get("AUDIOBOOKER_TRANSPORT") == "curl_cffi":
        try:
            from curl_cffi import requests as cffi_requests
            session = cffi_requests.Session()
            try:
                session.headers.update({"User-Agent": random_user_agent()})
            except Exception:
                pass
            return session
        except ImportError:
            pass
    session = requests.Session()
    session.headers.update({"User-Agent": random_user_agent()})
    return session
