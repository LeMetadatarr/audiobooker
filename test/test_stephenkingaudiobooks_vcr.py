"""Cassette-backed parser tests for the StephenKingAudioBooks scraper."""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    book = _first(StephenKingAudioBooks().iterate_all())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.streams, "expected at least one stream URL"
    assert book.authors


def test_search_by_title():
    book = _first(StephenKingAudioBooks().search_by_title("Carrie"))
    assert isinstance(book, AudioBook)
    assert book.title


def test_search_by_author():
    book = _first(StephenKingAudioBooks().search_by_author("King"))
    assert isinstance(book, AudioBook)
    assert book.authors


def test_search():
    book = _first(StephenKingAudioBooks().search("Shining"))
    assert isinstance(book, AudioBook)
    assert book.title
