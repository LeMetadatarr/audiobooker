"""Cassette-backed parser tests for the DarkerProjects scraper."""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.darkerprojects import DarkerProjects


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    book = _first(DarkerProjects().iterate_all())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.authors


def test_iterate_popular_yields_typed_audiobooks():
    book = _first(DarkerProjects().iterate_popular())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.streams
