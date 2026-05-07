"""Cassette-backed parser tests for the GoldenAudioBooks scraper.

This scraper had a silent-zero regression earlier in the year (the
sitemap URL filter rejected every entry, so ``iterate_all`` returned
nothing without raising). The ``test_iterate_all_yields_typed_audiobooks``
case below exists specifically to catch that class of drift.
"""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    """Regression: catch silent-zero failures from the sitemap parser."""
    book = _first(GoldenAudioBooks().iterate_all())
    assert isinstance(book, AudioBook), \
        "iterate_all returned nothing — sitemap parser likely regressed"
    assert book.title


def test_iterate_popular_yields_typed_audiobooks():
    book = _first(GoldenAudioBooks().iterate_popular())
    assert isinstance(book, AudioBook)
    assert book.title
