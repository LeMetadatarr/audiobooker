"""Persistent SQLite index for AudioBook catalogues.

Build once, search instantly — no network required after indexing.

Search strategy
---------------
Two-phase: SQLite FTS5 pre-filters candidates (token-level, fast), then
rapidfuzz re-ranks the shortlist with WRatio scoring (typo-tolerant, accurate).
When FTS returns no hits (e.g. a misspelled query), the search automatically
falls back to a full rapidfuzz scan so typos never produce zero results.

Usage
-----
    from audiobooker.index import BookIndex

    idx = BookIndex()
    idx.build()                          # iterate_all() on every source
    idx.build(sources=[Librivox()])      # specific sources only
    idx.update(sources=[Librivox()])     # add new books, skip existing

    for book in idx.search_by_title("Sherlock Holmes"):
        print(book.title, book.score)

    # Drop-in for unified search()
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
import sqlite3
import time
from pathlib import Path
from typing import Iterable, List, Optional

from audiobooker.base import AudioBook, AudioBookChapter, BookAuthor, AudiobookNarrator
from audiobooker.utils import score_book

_DEFAULT_DB = Path("~/.audiobooker/index.db").expanduser()

# FTS candidate pool — rapidfuzz re-ranks this shortlist.
# Large enough that the real answer is almost always in it;
# small enough that re-ranking stays fast even at 18k books.
_FTS_CANDIDATE_LIMIT = 500

_SCHEMA = """
CREATE TABLE IF NOT EXISTS followed_sources (
    id              INTEGER PRIMARY KEY,
    kind            TEXT NOT NULL,   -- 'channel' or 'playlist'
    url             TEXT NOT NULL UNIQUE,
    name            TEXT DEFAULT '',
    tags            TEXT DEFAULT '[]',
    authors         TEXT DEFAULT '[]',
    narrator        TEXT,
    language        TEXT DEFAULT 'en',
    min_runtime     INTEGER DEFAULT 300,
    title_blacklist TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS books (
    id            INTEGER PRIMARY KEY,
    hash          TEXT UNIQUE NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT DEFAULT '',
    image         TEXT DEFAULT '',
    language      TEXT DEFAULT '',
    year          INTEGER DEFAULT 0,
    runtime       INTEGER DEFAULT 0,
    source        TEXT DEFAULT '',
    streams       TEXT DEFAULT '[]',
    tags          TEXT DEFAULT '[]',
    authors       TEXT DEFAULT '[]',
    narrator      TEXT,
    narrators     TEXT DEFAULT '[]',
    genres        TEXT DEFAULT '[]',
    codec         TEXT DEFAULT '',
    bitrate       TEXT DEFAULT '',
    external_ids  TEXT DEFAULT '{}',
    chapters      TEXT DEFAULT '[]',
    -- Flattened plaintext copies for FTS indexing
    authors_text  TEXT DEFAULT '',
    tags_text     TEXT DEFAULT '',
    narrator_text TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_hash     ON books (hash);
CREATE INDEX IF NOT EXISTS idx_source   ON books (source);
CREATE INDEX IF NOT EXISTS idx_language ON books (language);

-- FTS5 content table — kept in sync via _fts_insert / _fts_delete helpers.
-- Columns mirror the four searchable text fields; rowid links to books.id.
CREATE VIRTUAL TABLE IF NOT EXISTS books_fts USING fts5(
    title,
    authors_text,
    tags_text,
    narrator_text,
    content=books,
    content_rowid=id,
    tokenize='unicode61 remove_diacritics 1'
);
"""


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------

def _flatten_authors(book: AudioBook) -> str:
    return " ".join(
        f"{a.first_name} {a.last_name}".strip() for a in book.authors
    )


def _flatten_tags(book: AudioBook) -> str:
    return " ".join(book.tags)


def _flatten_narrator(book: AudioBook) -> str:
    if book.narrator:
        return f"{book.narrator.first_name} {book.narrator.last_name}".strip()
    return ""


def _book_to_row(book: AudioBook) -> dict:
    narrator_json = None
    if book.narrator:
        narrator_json = json.dumps({"first_name": book.narrator.first_name,
                                    "last_name":  book.narrator.last_name})
    return {
        "hash":          book.stable_id(),
        "title":         book.title,
        "description":   book.description,
        "image":         book.image,
        "language":      book.language,
        "year":          book.year,
        "runtime":       book.runtime,
        "source":        book.source,
        "streams":       json.dumps(book.streams),
        "tags":          json.dumps(book.tags),
        "authors":       json.dumps([{"first_name": a.first_name,
                                      "last_name":  a.last_name}
                                     for a in book.authors]),
        "narrator":      narrator_json,
        "narrators":     json.dumps([{"first_name": n.first_name,
                                      "last_name":  n.last_name}
                                     for n in book.narrators]),
        "genres":        json.dumps(book.genres),
        "codec":         book.codec,
        "bitrate":       book.bitrate,
        "external_ids":  json.dumps(book.external_ids),
        "chapters":      json.dumps([{"title": c.title, "offset": c.offset,
                                      "runtime": c.runtime, "stream": c.stream,
                                      "image": c.image} for c in book.chapters]),
        "authors_text":  _flatten_authors(book),
        "tags_text":     _flatten_tags(book),
        "narrator_text": _flatten_narrator(book),
    }


def _row_to_book(row: sqlite3.Row) -> AudioBook:
    authors = [BookAuthor(**a) for a in json.loads(row["authors"])]
    narrator = None
    if row["narrator"]:
        narrator = AudiobookNarrator(**json.loads(row["narrator"]))
    narrators = [AudiobookNarrator(**n) for n in json.loads(row["narrators"])] \
        if row["narrators"] else []
    chapters = [AudioBookChapter(**c) for c in json.loads(row["chapters"])] \
        if row["chapters"] else []
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
        narrators=narrators,
        genres=json.loads(row["genres"]) if row["genres"] else [],
        codec=row["codec"] or "",
        bitrate=row["bitrate"] or "",
        external_ids=json.loads(row["external_ids"]) if row["external_ids"] else {},
        chapters=chapters,
    )


# ---------------------------------------------------------------------------
# FTS query builder
# ---------------------------------------------------------------------------

def _fts_query(query: str, field: Optional[str] = None) -> str:
    """Build an FTS5 MATCH expression from a free-text query.

    Each word becomes a prefix term so "love" matches "Lovecraft".
    Multi-word queries use OR so partial matches still surface results.
    """
    tokens = [w.strip('"\'.,:;!?') for w in query.split() if w.strip('"\'.,:;!?')]
    if not tokens:
        return '""'
    # Prefix-match each token; quote to handle special chars
    terms = " OR ".join(f'"{t}"*' for t in tokens)
    if field:
        return f"{field}:({terms})"
    return terms


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
        self._migrate()
        self._con.executescript(_SCHEMA)
        self._con.commit()

    def _migrate(self):
        pass  # no legacy DBs exist; schema is created fresh by _SCHEMA

    # ------------------------------------------------------------------
    # Building
    # ------------------------------------------------------------------

    def build(self, sources=None, progress: bool = True) -> int:
        """Clear records for the given sources and repopulate from scratch.

        Rebuilds the FTS index after each source completes.

        Returns the total number of books inserted.
        """
        if sources is None:
            sources = _default_sources()
        total = 0
        for source in sources:
            name = source.__class__.__name__
            # Delete existing books for this source and their FTS entries
            ids = [r[0] for r in self._con.execute(
                "SELECT id FROM books WHERE source = ?", (name,)
            ).fetchall()]
            if ids:
                self._fts_delete_ids(ids)
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
            # Rebuild FTS for this source's rows
            self._fts_rebuild()
            elapsed = time.monotonic() - t0
            if progress:
                print(f"  {name}: {count} books indexed in {elapsed:.1f}s")
            total += count
        return total

    def update(self, sources=None, progress: bool = True) -> int:
        """Add books not yet in the index; skip existing records.

        Uses ``AudioBook.__hash__`` (title + authors) as the uniqueness key.
        When ``sources`` is ``None``, also includes any channels/playlists
        registered via ``follow()``.

        Returns the number of new books inserted.
        """
        if sources is None:
            sources = _default_sources() + self._followed_as_sources()
        total = 0
        for source in sources:
            name = source.__class__.__name__
            count = 0
            t0 = time.monotonic()
            new_ids = []
            for book in source.iterate_all():
                row_id = self._upsert_if_new(book)
                if row_id is not None:
                    new_ids.append(row_id)
                    count += 1
            if new_ids:
                self._con.commit()
                self._fts_insert_ids(new_ids)
            elapsed = time.monotonic() - t0
            if progress:
                print(f"  {name}: {count} new books in {elapsed:.1f}s")
            total += count
        return total

    # ------------------------------------------------------------------
    # Low-level write helpers
    # ------------------------------------------------------------------

    def _upsert(self, book: AudioBook):
        row = _book_to_row(book)
        self._con.execute("""
            INSERT OR REPLACE INTO books
              (hash, title, description, image, language, year, runtime,
               source, streams, tags, authors, narrator, narrators,
               genres, codec, bitrate, external_ids, chapters,
               authors_text, tags_text, narrator_text)
            VALUES
              (:hash, :title, :description, :image, :language, :year, :runtime,
               :source, :streams, :tags, :authors, :narrator, :narrators,
               :genres, :codec, :bitrate, :external_ids, :chapters,
               :authors_text, :tags_text, :narrator_text)
        """, row)

    def _upsert_if_new(self, book: AudioBook) -> Optional[int]:
        """Insert book if not already present. Returns new rowid or None."""
        h = book.stable_id()
        existing = self._con.execute(
            "SELECT id FROM books WHERE hash = ?", (h,)
        ).fetchone()
        if existing:
            return None
        row = _book_to_row(book)
        cur = self._con.execute("""
            INSERT INTO books
              (hash, title, description, image, language, year, runtime,
               source, streams, tags, authors, narrator, narrators,
               genres, codec, bitrate, external_ids, chapters,
               authors_text, tags_text, narrator_text)
            VALUES
              (:hash, :title, :description, :image, :language, :year, :runtime,
               :source, :streams, :tags, :authors, :narrator, :narrators,
               :genres, :codec, :bitrate, :external_ids, :chapters,
               :authors_text, :tags_text, :narrator_text)
        """, row)
        return cur.lastrowid

    # ------------------------------------------------------------------
    # FTS maintenance
    # ------------------------------------------------------------------

    def _fts_rebuild(self):
        """Rebuild the entire FTS index from the books table."""
        self._con.execute("INSERT INTO books_fts(books_fts) VALUES('rebuild')")
        self._con.commit()

    def _fts_insert_ids(self, ids: List[int]):
        """Insert specific book rows into FTS by their rowid."""
        for row_id in ids:
            self._con.execute("""
                INSERT INTO books_fts(rowid, title, authors_text, tags_text, narrator_text)
                SELECT id, title, authors_text, tags_text, narrator_text
                FROM books WHERE id = ?
            """, (row_id,))
        self._con.commit()

    def _fts_delete_ids(self, ids: List[int]):
        """Remove specific rows from FTS before deleting from main table."""
        for row_id in ids:
            self._con.execute("""
                INSERT INTO books_fts(books_fts, rowid, title, authors_text, tags_text, narrator_text)
                SELECT 'delete', id, title, authors_text, tags_text, narrator_text
                FROM books WHERE id = ?
            """, (row_id,))
        self._con.commit()

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def _fts_search(self, query: str, field: Optional[str] = None,
                    source: Optional[str] = None,
                    language: Optional[str] = None) -> List[AudioBook]:
        """FTS5 pre-filter returning up to _FTS_CANDIDATE_LIMIT candidates."""
        fts_q = _fts_query(query, field)
        filters, params = ["books_fts MATCH ?"], [fts_q]
        if source:
            filters.append("b.source = ?")
            params.append(source)
        if language:
            filters.append("b.language = ?")
            params.append(language)
        where = " AND ".join(filters)
        params.append(_FTS_CANDIDATE_LIMIT)
        try:
            rows = self._con.execute(f"""
                SELECT b.* FROM books b
                JOIN books_fts ON books_fts.rowid = b.id
                WHERE {where}
                ORDER BY rank
                LIMIT ?
            """, params).fetchall()
            return [_row_to_book(r) for r in rows]
        except sqlite3.OperationalError:
            return []

    def _full_scan(self, source: Optional[str] = None,
                   language: Optional[str] = None) -> List[AudioBook]:
        clauses, params = [], []
        if source:
            clauses.append("source = ?")
            params.append(source)
        if language:
            clauses.append("language = ?")
            params.append(language)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = self._con.execute(
            f"SELECT * FROM books {where}", params
        ).fetchall()
        return [_row_to_book(r) for r in rows]

    def _rank(self, query: str, books: List[AudioBook], method: str,
              min_score: float, max_results: int,
              min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        results = []
        for book in books:
            if method == "search_by_narrator" and not book.narrator:
                continue
            if min_duration and book.runtime < min_duration:
                continue
            if max_duration and book.runtime > max_duration:
                continue
            book.score = score_book(query, book, method)
            if book.score >= min_score:
                results.append(book)
        results.sort(key=lambda b: b.score, reverse=True)
        return results[:max_results] if max_results else results

    def _search(self, query: str, method: str,
                fts_field: Optional[str],
                max_results: int, min_score: float,
                source: Optional[str], language: Optional[str],
                min_duration: int = 0, max_duration: int = 0,
                fts_fallback_threshold: int = 5) -> List[AudioBook]:
        """Two-phase search: FTS pre-filter → rapidfuzz re-rank.

        Falls back to a full table scan when FTS returns fewer than
        ``fts_fallback_threshold`` hits (handles typos and rare terms).
        """
        candidates = self._fts_search(query, fts_field, source, language)
        if len(candidates) < fts_fallback_threshold:
            if fts_field:
                candidates = self._fts_search(query, None, source, language)
            if len(candidates) < fts_fallback_threshold:
                candidates = self._full_scan(source, language)
        return self._rank(query, candidates, method, min_score, max_results,
                          min_duration, max_duration)

    def search(self, query: str, max_results: int = 10,
               min_score: float = 0.45,
               source: Optional[str] = None,
               language: Optional[str] = None,
               min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        return self._search(query, "search", None,
                            max_results, min_score, source, language,
                            min_duration, max_duration)

    def search_by_title(self, query: str, max_results: int = 10,
                        min_score: float = 0.45,
                        source: Optional[str] = None,
                        language: Optional[str] = None,
                        min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        return self._search(query, "search_by_title", "title",
                            max_results, min_score, source, language,
                            min_duration, max_duration)

    def search_by_author(self, query: str, max_results: int = 10,
                         min_score: float = 0.45,
                         source: Optional[str] = None,
                         language: Optional[str] = None,
                         min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        return self._search(query, "search_by_author", "authors_text",
                            max_results, min_score, source, language,
                            min_duration, max_duration)

    def search_by_tag(self, query: str, max_results: int = 10,
                      min_score: float = 0.45,
                      source: Optional[str] = None,
                      language: Optional[str] = None,
                      min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        return self._search(query, "search_by_tag", "tags_text",
                            max_results, min_score, source, language,
                            min_duration, max_duration)

    def search_by_narrator(self, query: str, max_results: int = 10,
                           min_score: float = 0.45,
                           source: Optional[str] = None,
                           language: Optional[str] = None,
                           min_duration: int = 0, max_duration: int = 0) -> List[AudioBook]:
        return self._search(query, "search_by_narrator", "narrator_text",
                            max_results, min_score, source, language,
                            min_duration, max_duration)

    # ------------------------------------------------------------------
    # Iteration
    # ------------------------------------------------------------------

    def iterate_all(self, source: Optional[str] = None,
                    language: Optional[str] = None) -> Iterable[AudioBook]:
        yield from self._full_scan(source, language)

    # ------------------------------------------------------------------
    # Followed YouTube sources
    # ------------------------------------------------------------------

    def follow(self, url: str, kind: str = "channel", *,
               name: str = "",
               tags: Optional[List[str]] = None,
               authors: Optional[List[BookAuthor]] = None,
               narrator=None,
               language: str = "en",
               min_runtime: int = 300,
               title_blacklist: Optional[List[str]] = None) -> None:
        """Register a YouTube channel or playlist to be included in update().

        Parameters
        ----------
        url:
            Full YouTube channel URL (``https://www.youtube.com/@Name/videos``)
            or playlist URL (``https://www.youtube.com/playlist?list=PLxxx``).
        kind:
            ``"channel"`` or ``"playlist"``.
        name:
            Human-readable label (displayed in ``list_followed()``).
        tags:
            Tags stamped on every book from this source.
        authors:
            Default author list (extraction can override per-video).
        narrator:
            Default narrator stamped on every book.
        language:
            ISO 639-1 code, default ``"en"``.
        min_runtime:
            Skip videos shorter than this many seconds.
        """
        narrator_json = None
        if narrator is not None:
            narrator_json = json.dumps({"first_name": narrator.first_name,
                                        "last_name":  narrator.last_name})
        authors_json = json.dumps([{"first_name": a.first_name,
                                    "last_name":  a.last_name}
                                   for a in (authors or [])])
        self._con.execute("""
            INSERT OR REPLACE INTO followed_sources
              (kind, url, name, tags, authors, narrator, language, min_runtime, title_blacklist)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (kind, url, name, json.dumps(tags or []),
              authors_json, narrator_json, language, min_runtime,
              json.dumps(title_blacklist or [])))
        self._con.commit()

    def unfollow(self, url: str) -> bool:
        """Remove a followed source by URL. Returns True if it existed."""
        cur = self._con.execute(
            "DELETE FROM followed_sources WHERE url = ?", (url,)
        )
        self._con.commit()
        return cur.rowcount > 0

    def list_followed(self) -> List[dict]:
        """Return all followed sources as a list of dicts."""
        rows = self._con.execute(
            "SELECT * FROM followed_sources ORDER BY kind, name, url"
        ).fetchall()
        result = []
        for r in rows:
            result.append({
                "kind":            r["kind"],
                "url":             r["url"],
                "name":            r["name"],
                "tags":            json.loads(r["tags"]),
                "authors":         json.loads(r["authors"]),
                "narrator":        json.loads(r["narrator"]) if r["narrator"] else None,
                "language":        r["language"],
                "min_runtime":     r["min_runtime"],
                "title_blacklist": json.loads(r["title_blacklist"]) if r["title_blacklist"] else [],
            })
        return result

    def _followed_as_sources(self):
        """Instantiate all followed YouTube sources."""
        try:
            from audiobooker.scrappers.youtube import (
                YoutubeChannelSource, YoutubePlaylistSource
            )
        except ImportError:
            return []

        sources = []
        for f in self.list_followed():
            authors = [BookAuthor(**a) for a in f["authors"]]
            narrator = None
            if f["narrator"]:
                from audiobooker.base import AudiobookNarrator
                narrator = AudiobookNarrator(**f["narrator"])
            kwargs = dict(
                authors=authors,
                narrator=narrator,
                tags=f["tags"],
                language=f["language"],
                min_runtime=f["min_runtime"],
                title_blacklist=f["title_blacklist"],
            )
            if f["kind"] == "playlist":
                sources.append(YoutubePlaylistSource(
                    playlist_url=f["url"], **kwargs
                ))
            else:
                sources.append(YoutubeChannelSource(
                    channel_url=f["url"], **kwargs
                ))
        return sources

    # ------------------------------------------------------------------
    # Stats / meta
    # ------------------------------------------------------------------

    def stats(self) -> dict:
        total = self._con.execute("SELECT COUNT(*) FROM books").fetchone()[0]
        by_source = dict(self._con.execute(
            "SELECT source, COUNT(*) FROM books GROUP BY source ORDER BY COUNT(*) DESC"
        ).fetchall())
        by_language = dict(self._con.execute(
            "SELECT language, COUNT(*) FROM books GROUP BY language ORDER BY COUNT(*) DESC"
        ).fetchall())
        return {"total": total, "by_source": by_source, "by_language": by_language}

    def as_source(self) -> "IndexedSource":
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

    Can be used anywhere an ``AudioBookSource`` is accepted, including
    ``sources=`` in ``audiobooker.search()``.

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
        yield from self._index.search_by_author(author, max_results=0,
                                                source=self._source,
                                                language=self._language)

    def iterate_by_tag(self, tag: str) -> Iterable[AudioBook]:
        yield from self._index.search_by_tag(tag, max_results=0,
                                             source=self._source,
                                             language=self._language)

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
# Default sources (web only — no YouTube)
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
        Librivox(), LoyalBooks(), StephenKingAudioBooks(),
        GoldenAudioBooks(), AudioAnarchy(), DarkerProjects(), HPTalesAudioBooks(),
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
    p_build.add_argument("--sources", nargs="*")

    p_update = sub.add_parser("update", help="Add new books without clearing existing")
    p_update.add_argument("--sources", nargs="*")

    sub.add_parser("stats", help="Show index statistics")

    p_search = sub.add_parser("search", help="Search the index")
    p_search.add_argument("query")
    p_search.add_argument("--method", default="search",
                          choices=["search", "search_by_title", "search_by_author",
                                   "search_by_tag", "search_by_narrator"])
    p_search.add_argument("--n", type=int, default=10)
    p_search.add_argument("--source", default=None)
    p_search.add_argument("--language", default=None)
    p_search.add_argument("--min-duration", type=int, default=0,
                          metavar="SECS", help="Minimum runtime in seconds")
    p_search.add_argument("--max-duration", type=int, default=0,
                          metavar="SECS", help="Maximum runtime in seconds")

    p_follow = sub.add_parser("follow", help="Follow a YouTube channel or playlist")
    p_follow.add_argument("url", help="Channel or playlist URL")
    p_follow.add_argument("--kind", default="channel", choices=["channel", "playlist"])
    p_follow.add_argument("--name", default="", help="Human-readable label")
    p_follow.add_argument("--tags", nargs="*", default=[], metavar="TAG")
    p_follow.add_argument("--language", default="en")
    p_follow.add_argument("--min-runtime", type=int, default=300,
                          help="Skip videos shorter than N seconds (default 300)")
    p_follow.add_argument("--blacklist", nargs="*", default=[], metavar="PHRASE",
                          help="Skip books whose title contains any of these strings")

    p_unfollow = sub.add_parser("unfollow", help="Stop following a channel or playlist")
    p_unfollow.add_argument("url", help="Channel or playlist URL to remove")

    sub.add_parser("list", help="List followed YouTube sources")

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

    elif args.cmd == "follow":
        idx.follow(args.url, kind=args.kind, name=args.name,
                   tags=args.tags, language=args.language,
                   min_runtime=args.min_runtime,
                   title_blacklist=args.blacklist)
        label = args.name or args.url
        print(f"Following {args.kind}: {label}")

    elif args.cmd == "unfollow":
        removed = idx.unfollow(args.url)
        if removed:
            print(f"Unfollowed: {args.url}")
        else:
            print(f"Not found: {args.url}")

    elif args.cmd == "list":
        followed = idx.list_followed()
        if not followed:
            print("No followed sources.")
        else:
            print(f"{'Kind':<10} {'Name/URL':<50} {'Language':<8} {'Tags'}")
            print("-" * 80)
            for f in followed:
                label = f["name"] or f["url"]
                tags = ", ".join(f["tags"]) if f["tags"] else ""
                print(f"  {f['kind']:<8} {label:<50} {f['language']:<8} {tags}")

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
        kw = {}
        if args.source:
            kw["source"] = args.source
        if args.language:
            kw["language"] = args.language
        if args.min_duration:
            kw["min_duration"] = args.min_duration
        if args.max_duration:
            kw["max_duration"] = args.max_duration
        results = fn(args.query, max_results=args.n, **kw)
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
