"""Cassette-backed parser tests for the LoyalBooks scraper."""
from __future__ import annotations

import pytest

from audiobooker.base import AudioBook
from audiobooker.scrappers.loyalbooks import LoyalBooks


pytestmark = pytest.mark.vcr


def _first(it):
    for x in it:
        return x
    return None


def test_iterate_all_yields_typed_audiobooks():
    book = _first(LoyalBooks().iterate_all())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.chapters, "expected chapter list from RSS feed"
    assert book.streams


def test_iterate_popular_yields_typed_audiobooks():
    book = _first(LoyalBooks().iterate_popular())
    assert isinstance(book, AudioBook)
    assert book.title
    assert book.chapters


def test_search_by_title():
    book = _first(LoyalBooks().search_by_title("Dracula"))
    assert isinstance(book, AudioBook)
    assert book.title


def test_search_by_author():
    book = _first(LoyalBooks().search_by_author("Stoker"))
    assert isinstance(book, AudioBook)
    assert book.title


def test_search_by_tag():
    book = _first(LoyalBooks().search_by_tag("Horror"))
    assert isinstance(book, AudioBook)
    assert book.title
