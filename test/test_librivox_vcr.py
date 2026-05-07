"""Cassette-backed parser tests for the LibriVox scraper.

These tests replay real captured HTTP responses against the parser so
upstream HTML/JSON changes surface as test failures rather than silent
empty results (the failure mode that produced the ``GoldenAudioBooks``
sitemap regression earlier in the year).

Re-record cassettes::

    pytest --vcr-record=all test/test_librivox_vcr.py

The nightly CI workflow runs without cassettes against the live API.
"""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.librivox import Librivox


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    book = _first(Librivox().iterate_all(offset=0, max_offset=0))
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.language
    assert book.streams, "expected at least one stream URL"
    assert book.codec == "mp3"


def test_search_by_author():
    book = _first(Librivox().search_by_author("Tolstoy"))
    assert isinstance(book, AudioBook)
    assert any("tolstoy" in (a.last_name or "").lower() or
               "tolstoy" in (a.first_name or "").lower()
               for a in book.authors)


def test_search_by_title():
    book = _first(Librivox().search_by_title("Pride and Prejudice"))
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.chapters, "expected chapter list"
    assert book.runtime > 0


def test_search_by_tag():
    book = _first(Librivox().search_by_tag("Science Fiction"))
    assert isinstance(book, AudioBook)
    assert book.title


def test_search_by_narrator():
    book = _first(Librivox().search_by_narrator("Karen Savage"))
    assert isinstance(book, AudioBook)
    assert book.narrators
