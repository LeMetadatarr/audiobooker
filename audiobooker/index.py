"""Persistent SQLite index for AudioBook catalogues.

Build once, search instantly — no network required after indexing.

Usage
-----
    from audiobooker.index import BookIndex

    # Build (or update) the index from all sources
    idx = BookIndex()
    idx.build()                          # iterate_all() on every source
    idx.build(sources=[Librivox()])      # specific sources only
    idx.update(sources=[Librivox()])     # add new books, skip existing

    # Search offline
    for book in idx.search_by_title("Sherlock Holmes"):
        print(book.title, book.score)

    # Use as a drop-in AudioBookSource in unified search()
    from audiobooker import search
    for book in search("Lovecraft", sources=[idx.as_source()]):
        print(book.title)

CLI
---
    python -m audiobooker.index build
    python -m audiobooker.index build --sources librivox loyalbooks
    python -m audiobooker.index update
    python -m audiobooker.index stats
    python -m audiobooker.index search "Lovecraft"
"""

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable, List, Optional

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator
from audiobooker.utils import score_book

_DEFAULT_DB = Path("~/.audiobooker/index.db").expanduser()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    hash        INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT DEFAULT '',
    image       TEXT DEFAULT '',
    language    TEXT DEFAULT '',
    year        INTEGER DEFAULT 0,
    runtime     INTEGER DEFAULT 0,
    source      TEXT DEFAULT '',
    streams     TEXT DEFAULT '[]',
    tags        TEXT DEFAULT '[]',
    authors     TEXT DEFAULT '[]',
    narrator    TEXT
);
CREATE INDEX IF NOT EXISTS idx_source   ON books (source);
CREATE INDEX IF NOT EXISTS idx_language ON books (language);
"""


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _book_to_row(book: AudioBook) -> dict:
    narrator = None
    if book.narrator:
        narrator = json.dumps({"first_name": book.narrator.first_name,
                               "last_name": book.narrator.last_name})
    return {
        "hash":        hash(book),
        "title":       book.title,
        "description": book.description,
        "image":       book.image,
        "language":    book.language,
        "year":        book.year,
        "runtime":     book.runtime,
        "source":      book.source,
        "streams":     json.dumps(book.streams),
        "tags":        json.dumps(book.tags),
        "authors":     json.dumps([{"first_name": a.first_name,
                                    "last_name": a.last_name}
                                   for a in book.authors]),
        "narrator":    narrator,
    }


def _row_to_book(row: sqlite3.Row) -> AudioBook:
    authors = [BookAuthor(**a) for a in json.loads(row["authors"])]
    narrator = None
    if row["narrator"]:
        narrator = AudiobookNarrator(**json.loads(row["narrator"]))
    return AudioBook(
        title=row["title"],
        description=row["description"],
        image=row["image"],
        language=row["language"],
        year=row["year"],
        runtime=row["runtime"],
        source=row["source"],
        streams=json.loads(row["streams"]),
        tags=json.loads(row["tags"]),
        authors=authors,
        narrator=narrator,
    )


# ---------------------------------------------------------------------------
# BookIndex
# ---------------------------------------------------------------------------

class BookIndex:
    """SQLite-backed persistent index of AudioBook records.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.
        Defaults to ``~/.audiobooker/index.db``.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._con = sqlite3.connect(str(self.db_path))
        self._con.row_factory = sqlite3.Row
        self._con.executescript(_SCHEMA)
        self._con.commit()

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, sources=None, progress: bool = True) -> int:
        """Clear all records for the given sources and repopulate.

        Parameters
        ----------
        sources:
            List of instantiated ``AudioBookSource`` objects.
            Defaults to all web sources (YouTube excluded — those change too
            fast to be worth indexing).
        progress:
            Print a one-line progress indicator per source.

        Returns
        -------
        int
            Total number of books inserted.
        """
        if sources is None:
            sources = _default_sources()
        total = 0
        for source in sources:
            name = source.__class__.__name__
            # Remove existing records for this source so a full rebuild is clean
            self._con.execute("DELETE FROM books WHERE source = ?", (name,))
            self._con.commit()
            count = 0
            t0 = time.monotonic()
            for book in source.iterate_all():
                self._upsert(book)
                count += 1
                if progress and count % 50 == 0:
                    print(f"  {name}: {count} books…", end="\r", flush=True)
            self._con.commit()
            elapsed = time.monotonic() - t0
            if progress:
                print(f"  {name}: {count} books indexed in {elapsed:.1f}s")
            total += count
        return total

    def update(self, sources=None, progress: bool = True) -> int:
        """Add books not yet in the index; skip existing records.

        Uses ``AudioBook.__hash__`` (title + authors) as the uniqueness key.

        Returns
        -------
        int
            Number of new books inserted.
        """
        if sources is None:
            sources = _default_sources()
        total = 0
        for source in sources:
            name = source.__class__.__name__
            count = 0
            t0 = time.monotonic()
            for book in source.iterate_all():
                h = hash(book)
                exists = self._con.execute(
                    "SELECT 1 FROM books WHERE hash = ?", (h,)
                ).fetchone()
                if not exists:
                    self._upsert(book)
                    count += 1
            self._con.commit()
            elapsed = time.monotonic() - t0
            if progress:
                print(f"  {name}: {count} new books in {elapsed:.1f}s")
            total += count
        return total

    def _upsert(self, book: AudioBook):
        row = _book_to_row(book)
        self._con.execute("""
            INSERT OR REPLACE INTO books
              (hash, title, description, image, language, year, runtime,
               source, streams, tags, authors, narrator)
            VALUES
              (:hash, :title, :description, :image, :language, :year, :runtime,
               :source, :streams, :tags, :authors, :narrator)
        """, row)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def _all_books(self, source: Optional[str] = None,
                   language: Optional[str] = None) -> List[AudioBook]:
        clauses, params = [], []
        if source:
            clauses.append("source = ?")
            params.append(source)
        if language:
            clauses.append("language = ?")
            params.append(language)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._con.execute(f"SELECT * FROM books {where}", params).fetchall()
        return [_row_to_book(r) for r in rows]

    def search_by_title(self, query: str, max_results: int = 10,
                        min_score: float = 0.45,
                        source: Optional[str] = None,
                        language: Optional[str] = None) -> List[AudioBook]:
        results = []
        for book in self._all_books(source, language):
            book.score = score_book(query, book, "search_by_title")
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def search_by_author(self, query: str, max_results: int = 10,
                         min_score: float = 0.45,
                         source: Optional[str] = None,
                         language: Optional[str] = None) -> List[AudioBook]:
        results = []
        for book in self._all_books(source, language):
            book.score = score_book(query, book, "search_by_author")
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def search_by_tag(self, query: str, max_results: int = 10,
                      min_score: float = 0.45,
                      source: Optional[str] = None,
                      language: Optional[str] = None) -> List[AudioBook]:
        results = []
        for book in self._all_books(source, language):
            book.score = score_book(query, book, "search_by_tag")
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def search_by_narrator(self, query: str, max_results: int = 10,
                           min_score: float = 0.45,
                           source: Optional[str] = None,
                           language: Optional[str] = None) -> List[AudioBook]:
        results = []
        for book in self._all_books(source, language):
            if not book.narrator:
                continue
            book.score = score_book(query, book, "search_by_narrator")
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def search(self, query: str, max_results: int = 10,
               min_score: float = 0.45,
               source: Optional[str] = None,
               language: Optional[str] = None) -> List[AudioBook]:
        results = []
        for book in self._all_books(source, language):
            book.score = score_book(query, book, "search")
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def iterate_all(self, source: Optional[str] = None,
                    language: Optional[str] = None) -> Iterable[AudioBook]:
        yield from self._all_books(source, language)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        """Return a summary dict: total books, per-source counts, languages."""
        total = self._con.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        by_source = dict(self._con.execute(
            "SELECT source, COUNT(*) FROM books GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall())
        by_language = dict(self._con.execute(
            "SELECT language, COUNT(*) FROM books GROUP BY language ORDER BY COUNT(*) DESC"
        ).fetchall())
        return {"total": total, "by_source": by_source, "by_language": by_language}

    # ------------------------------------------------------------------
    # AudioBookSource adapter
    # ------------------------------------------------------------------

    def as_source(self) -> "IndexedSource":
        """Return an AudioBookSource backed by this index."""
        return IndexedSource(self)

    def __len__(self) -> int:
        return self._con.execute("SELECT COUNT(*) FROM books").fetchone()[0]

    def __repr__(self) -> str:
        return f"BookIndex({self.db_path}, {len(self)} books)"

    def close(self):
        self._con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ---------------------------------------------------------------------------
# IndexedSource — drop-in AudioBookSource backed by the index
# ---------------------------------------------------------------------------

class IndexedSource:
    """AudioBookSource interface backed by a BookIndex.

    Supports the full search API and can be used anywhere an
    ``AudioBookSource`` is accepted, including ``sources=`` in
    ``audiobooker.search()``.

    Parameters
    ----------
    index:
        A ``BookIndex`` instance.
    source_filter:
        If set, only return books from this source name.
    language_filter:
        If set, only return books with this language code.
    """

    source_name = "Index"

    def __init__(self, index: BookIndex,
                 source_filter: Optional[str] = None,
                 language_filter: Optional[str] = None):
        self._index = index
        self._source = source_filter
        self._language = language_filter

    def iterate_all(self) -> Iterable[AudioBook]:
        yield from self._index.iterate_all(self._source, self._language)

    def iterate_popular(self) -> Iterable[AudioBook]:
        return self.iterate_all()

    def iterate_by_author(self, author: str) -> Iterable[AudioBook]:
        for book in self._index.search_by_author(author, max_results=0):
            yield book

    def iterate_by_tag(self, tag: str) -> Iterable[AudioBook]:
        for book in self._index.search_by_tag(tag, max_results=0):
            yield book

    def search(self, query: str) -> Iterable[AudioBook]:
        yield from self._index.search(query, max_results=0,
                                      source=self._source,
                                      language=self._language)

    def search_by_title(self, query: str) -> Iterable[AudioBook]:
        yield from self._index.search_by_title(query, max_results=0,
                                               source=self._source,
                                               language=self._language)

    def search_by_author(self, query: str) -> Iterable[AudioBook]:
        yield from self._index.search_by_author(query, max_results=0,
                                                source=self._source,
                                                language=self._language)

    def search_by_tag(self, query: str) -> Iterable[AudioBook]:
        yield from self._index.search_by_tag(query, max_results=0,
                                             source=self._source,
                                             language=self._language)

    def search_by_narrator(self, query: str) -> Iterable[AudioBook]:
        yield from self._index.search_by_narrator(query, max_results=0,
                                                  source=self._source,
                                                  language=self._language)

    def __repr__(self) -> str:
        return f"IndexedSource({self._index!r})"


# ---------------------------------------------------------------------------
# Default sources for build/update (web only, no YouTube)
# ---------------------------------------------------------------------------

def _default_sources():
    from audiobooker.scrappers.librivox import Librivox
    from audiobooker.scrappers.loyalbooks import LoyalBooks
    from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
    from audiobooker.scrappers.audioanarchy import AudioAnarchy
    from audiobooker.scrappers.darkerprojects import DarkerProjects
    from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
    from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks
    return [
        Librivox(),
        LoyalBooks(),
        StephenKingAudioBooks(),
        GoldenAudioBooks(),
        AudioAnarchy(),
        DarkerProjects(),
        HPTalesAudioBooks(),
    ]


# ---------------------------------------------------------------------------
# CLI  (python -m audiobooker.index)
# ---------------------------------------------------------------------------

_SOURCE_MAP = {
    "librivox":              "audiobooker.scrappers.librivox.Librivox",
    "loyalbooks":            "audiobooker.scrappers.loyalbooks.LoyalBooks",
    "goldenaudiobooks":      "audiobooker.scrappers.goldenaudiobooks.GoldenAudioBooks",
    "audioanarchy":          "audiobooker.scrappers.audioanarchy.AudioAnarchy",
    "darkerprojects":        "audiobooker.scrappers.darkerprojects.DarkerProjects",
    "hpaudiotales":          "audiobooker.scrappers.hpaudiotales.HPTalesAudioBooks",
    "stephenkingaudiobooks": "audiobooker.scrappers.stephenkingaudiobooks.StephenKingAudioBooks",
}


def _resolve_sources(names):
    import importlib
    sources = []
    for name in names:
        key = name.lower().replace("-", "").replace("_", "")
        match = next((v for k, v in _SOURCE_MAP.items()
                      if k.replace("_", "") == key), None)
        if not match:
            print(f"Unknown source: {name!r}. Valid: {', '.join(_SOURCE_MAP)}")
            continue
        mod, cls = match.rsplit(".", 1)
        sources.append(getattr(importlib.import_module(mod), cls)())
    return sources


def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m audiobooker.index",
        description="Build and query the audiobooker local index.",
    )
    parser.add_argument("--db", default=None, help="Path to index database")
    sub = parser.add_subparsers(dest="cmd")

    p_build = sub.add_parser("build", help="(Re)build index for all or selected sources")
    p_build.add_argument("--sources", nargs="*", help="Sources to index (default: all)")

    p_update = sub.add_parser("update", help="Add new books without clearing existing records")
    p_update.add_argument("--sources", nargs="*", help="Sources to update (default: all)")

    p_stats = sub.add_parser("stats", help="Show index statistics")

    p_search = sub.add_parser("search", help="Search the index")
    p_search.add_argument("query")
    p_search.add_argument("--method", default="search",
                          choices=["search", "search_by_title", "search_by_author",
                                   "search_by_tag", "search_by_narrator"])
    p_search.add_argument("--n", type=int, default=10, help="Max results")
    p_search.add_argument("--source", default=None, help="Filter by source name")

    args = parser.parse_args()

    idx = BookIndex(args.db)

    if args.cmd == "build":
        sources = _resolve_sources(args.sources) if args.sources else None
        print("Building index…")
        total = idx.build(sources=sources)
        print(f"Done. {total} books indexed.")

    elif args.cmd == "update":
        sources = _resolve_sources(args.sources) if args.sources else None
        print("Updating index…")
        total = idx.update(sources=sources)
        print(f"Done. {total} new books added.")

    elif args.cmd == "stats":
        s = idx.stats()
        print(f"Total books: {s['total']}")
        print("\nBy source:")
        for src, n in s["by_source"].items():
            print(f"  {src:30s} {n}")
        print("\nBy language:")
        for lang, n in s["by_language"].items():
            print(f"  {lang or '(unknown)':10s} {n}")

    elif args.cmd == "search":
        fn = getattr(idx, args.method)
        results = fn(args.query, max_results=args.n,
                     **({'source': args.source} if args.source else {}))
        print(f"{len(results)} result(s) for {args.query!r}:\n")
        for book in results:
            authors = ", ".join(
                f"{a.first_name} {a.last_name}".strip() for a in book.authors
            )
            print(f"  [{book.score:.2f}] {book.title!r}")
            print(f"         source={book.source}  author={authors or '?'}"
                  f"  lang={book.language}  runtime={book.runtime}s")
    else:
        parser.print_help()

    idx.close()


if __name__ == "__main__":
    main()
