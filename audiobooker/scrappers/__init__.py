import abc
from requests_cache import CachedSession
from datetime import timedelta
from audiobooker.utils import random_user_agent, fuzzy_match
from typing import Iterable
from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator


class AudioBookSource:
    expire_after = timedelta(hours=1)
    session = CachedSession(backend='memory', expire_after=expire_after)
    session.headers.update({"User-Agent": random_user_agent()})

    @property
    def source_name(self) -> str:
        return self.__class__.__name__

    def _tag(self, book: AudioBook) -> AudioBook:
        """Stamp the source field and return the book."""
        if not book.source:
            book.source = self.source_name
        return book

    def search(self, query) -> Iterable[AudioBook]:
        seen = set()
        for b in self.search_by_title(query):
            if id(b) not in seen:
                seen.add(id(b))
                yield b
        for b in self.search_by_author(query):
            if id(b) not in seen:
                seen.add(id(b))
                yield b
        for b in self.search_by_tag(query):
            if id(b) not in seen:
                seen.add(id(b))
                yield b

    def search_by_narrator(self, query) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            if b.narrator:
                full = f"{b.narrator.first_name} {b.narrator.last_name}".strip()
                if fuzzy_match(query, full) or fuzzy_match(query, b.narrator.last_name):
                    yield self._tag(b)

    def search_by_author(self, query) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            for a in b.authors:
                full = f"{a.first_name} {a.last_name}".strip()
                # Match full name, or last name alone (for single-word queries)
                q_words = query.split()
                if fuzzy_match(query, full) or \
                   (len(q_words) == 1 and a.last_name and fuzzy_match(query, a.last_name)):
                    yield self._tag(b)
                    break

    def search_by_title(self, query) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            if fuzzy_match(query, b.title):
                yield self._tag(b)

    def search_by_tag(self, query) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            if any(fuzzy_match(query, t) for t in b.tags):
                yield self._tag(b)

    @abc.abstractmethod
    def iterate_all(self) -> Iterable[AudioBook]:
        pass

    def iterate_popular(self) -> Iterable[AudioBook]:
        return self.iterate_all()

    def iterate_by_author(self, author) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            for a in b.authors:
                if fuzzy_match(author, a.last_name):
                    yield self._tag(b)
                    break

    def iterate_by_tag(self, tag) -> Iterable[AudioBook]:
        for b in self.iterate_all():
            if tag in b.tags:
                yield self._tag(b)
