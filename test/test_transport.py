"""Tests for the pluggable HTTP transport layer."""
import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest
import requests

from audiobooker import transport
from audiobooker.scrappers import AudioBookSource
from audiobooker.scrappers.librivox import Librivox


def test_injected_session_captures_requests(monkeypatch):
    """A custom Session passed via __init__ is used for all HTTP calls."""
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"books": []}
    fake_session = MagicMock(spec=requests.Session)
    fake_session.headers = {"User-Agent": "test-agent"}
    fake_session.get.return_value = fake_resp

    lv = Librivox(session=fake_session)
    assert lv.session is fake_session
    # Trigger an API call. iterate_all is a generator — exhaust it.
    list(lv.search_by_author("Twain"))

    assert fake_session.get.called
    called_url = fake_session.get.call_args[0][0]
    assert "librivox.org" in called_url


def test_default_session_no_env_returns_requests_session(monkeypatch):
    """With no env var set, default_session() returns a requests.Session."""
    monkeypatch.delenv("AUDIOBOOKER_TRANSPORT", raising=False)
    sess = transport.default_session()
    assert isinstance(sess, requests.Session)
    assert sess.headers.get("User-Agent")


def test_env_var_falls_back_when_curl_cffi_missing(monkeypatch):
    """AUDIOBOOKER_TRANSPORT=curl_cffi without curl_cffi installed → requests."""
    monkeypatch.setenv("AUDIOBOOKER_TRANSPORT", "curl_cffi")
    # Force the import to fail regardless of environment.
    monkeypatch.setitem(sys.modules, "curl_cffi", None)
    sess = transport.default_session()
    assert isinstance(sess, requests.Session)


def test_env_var_uses_curl_cffi_when_available(monkeypatch):
    """AUDIOBOOKER_TRANSPORT=curl_cffi + importable curl_cffi → cffi session."""
    monkeypatch.setenv("AUDIOBOOKER_TRANSPORT", "curl_cffi")

    sentinel_session = MagicMock()
    sentinel_session.headers = {}

    fake_requests_mod = types.ModuleType("curl_cffi.requests")
    fake_requests_mod.Session = MagicMock(return_value=sentinel_session)
    fake_pkg = types.ModuleType("curl_cffi")
    fake_pkg.requests = fake_requests_mod

    monkeypatch.setitem(sys.modules, "curl_cffi", fake_pkg)
    monkeypatch.setitem(sys.modules, "curl_cffi.requests", fake_requests_mod)

    sess = transport.default_session()
    assert sess is sentinel_session
    fake_requests_mod.Session.assert_called_once()


def test_backward_compat_no_arg_constructor():
    """Librivox() with no args still works and uses the class-level default."""
    lv = Librivox()
    assert lv.session is AudioBookSource.session
