"""Cassette-backed parser tests for the HPAudioTales scraper."""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    book = _first(HPTalesAudioBooks().iterate_all())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.streams, "expected at least one stream URL"


def test_iterate_popular_yields_typed_audiobooks():
    book = _first(HPTalesAudioBooks().iterate_popular())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.streams
