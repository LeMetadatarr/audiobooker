"""Converters from audiobooker models to mediavocab typed objects."""
from __future__ import annotations

from mediavocab import (
    Chapter as MvChapter,
    Credit,
    CreditSection as MvCreditSection,
    EntityKind,
    EntityRef,
    MediaType,
    RelationRole,
    Release as MvRelease,
    StreamMode,
    Work,
)

from audiobooker.base import (
    AudioBook,
    AudioBookChapter,
    AudiobookNarrator,
    BookAuthor,
)

# Sources whose entire catalogue is dedicated public-domain material.
_PUBLIC_DOMAIN_SOURCES = {"librivox", "loyalbooks"}


def _author_ref(author: BookAuthor) -> EntityRef:
    name = f"{author.first_name} {author.last_name}".strip()
    return EntityRef(name=name, kind=EntityKind.PERSON)


def _narrator_ref(narrator: AudiobookNarrator) -> EntityRef:
    name = f"{narrator.first_name} {narrator.last_name}".strip()
    return EntityRef(name=name, kind=EntityKind.PERSON)


def _to_mv_chapter(c: AudioBookChapter) -> MvChapter:
    return MvChapter(
        offset=float(c.offset),
        title=c.title,
        image=c.image,
        end=(float(c.offset) + float(c.runtime)) if c.runtime else None,
    )


def audiobook_to_release(book: AudioBook) -> MvRelease:
    """Convert an ``AudioBook`` to a mediavocab ``Release``."""
    credits: list = []
    for author in book.authors:
        credits.append(
            Credit(
                entity=_author_ref(author),
                role="author",
                relation_role=RelationRole.CREATOR,
                section=MvCreditSection.PRINCIPAL,
            )
        )
    # Multi-reader sources (LibriVox) populate ``narrators``; single-reader
    # sources still populate ``narrator``. base.AudioBook keeps them in sync.
    narrators = book.narrators or ([book.narrator] if book.narrator else [])
    seen_narrators: set = set()
    for narrator in narrators:
        if not narrator:
            continue
        key = (narrator.first_name.lower(), narrator.last_name.lower())
        if key in seen_narrators:
            continue
        seen_narrators.add(key)
        credits.append(
            Credit(
                entity=_narrator_ref(narrator),
                role="narrator",
                relation_role=RelationRole.PERFORMER,
                section=MvCreditSection.PRINCIPAL,
            )
        )

    extra: dict = {}
    if book.source:
        extra["source"] = book.source
    if book.score:
        extra["score"] = str(book.score)
    if book.tags:
        extra["tags"] = ", ".join(book.tags)
    if book.streams:
        extra["stream_urls"] = ", ".join(book.streams)
    if book.description:
        extra["description"] = book.description

    external_ids: dict = {}
    # Pass through typed external_ids the source already populated
    # (e.g. ``librivox_id`` from the LibriVox API). Keys must match
    # mediavocab.ExternalIds field names.
    for key, val in (book.external_ids or {}).items():
        if val:
            external_ids[key] = str(val)
    external_ids["audiobooker_id"] = book.stable_id()

    # Genres: prefer the dedicated ``genres`` field; fall back to ``tags``
    # only when the source doesn't distinguish them.
    content_genres = list(book.genres) if book.genres else []

    work = Work(
        title=book.title,
        media_type=MediaType.AUDIOBOOK,
        year=book.year or None,
        runtime=float(book.runtime) if book.runtime else None,
        language=book.language,
        credits=credits,
        content_genres=content_genres,
        external_ids=external_ids,
        extra=extra,
    )

    # IsoDate-compatible YYYY string when we only know the year
    release_date = str(book.year) if book.year else ""

    license_id = ""
    src = (book.source or "").lower()
    if any(s in src for s in _PUBLIC_DOMAIN_SOURCES):
        license_id = "public_domain"

    uri = book.streams[0] if book.streams else ""

    chapters = [_to_mv_chapter(c) for c in (book.chapters or [])]

    return MvRelease(
        work=work,
        uri=uri,
        image=book.image,
        stream_mode=StreamMode.ON_DEMAND,
        release_date=release_date,
        license=license_id,
        codec=book.codec or "",
        bitrate=book.bitrate or "",
        audio_language=book.language or "",
        chapters=chapters,
        external_ids=external_ids,
        extra=extra,
    )
