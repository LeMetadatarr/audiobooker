"""Converters from audiobooker models to mediavocab typed objects."""
from __future__ import annotations

from mediavocab import (
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

from audiobooker.base import AudioBook, BookAuthor, AudiobookNarrator


def _author_ref(author: BookAuthor) -> EntityRef:
    name = f"{author.first_name} {author.last_name}".strip()
    return EntityRef(name=name, kind=EntityKind.PERSON)


def _narrator_ref(narrator: AudiobookNarrator) -> EntityRef:
    name = f"{narrator.first_name} {narrator.last_name}".strip()
    return EntityRef(name=name, kind=EntityKind.PERSON)


def audiobook_to_release(book: AudioBook) -> MvRelease:
    """Convert an ``AudioBook`` to a mediavocab ``Release``."""
    credits: list = []
    for author in book.authors:
        ref = _author_ref(author)
        credits.append(Credit(entity=ref, role="author",
                               relation_role=RelationRole.CREATOR,
                               section=MvCreditSection.PRINCIPAL))
    if book.narrator:
        ref = _narrator_ref(book.narrator)
        credits.append(Credit(entity=ref, role="narrator",
                               relation_role=RelationRole.PERFORMER,
                               section=MvCreditSection.PRINCIPAL))

    extra: dict = {}
    if book.source:
        extra["source"] = book.source
    if book.score:
        extra["score"] = book.score
    if book.tags:
        extra["tags"] = book.tags
    if book.streams:
        extra["stream_urls"] = book.streams
    if book.description:
        extra["description"] = book.description

    external_ids: dict = {}
    if book.stable_id():
        external_ids["audiobooker_id"] = book.stable_id()

    work = Work(
        title=book.title,
        media_type=MediaType.AUDIOBOOK,
        year=book.year or None,
        runtime=float(book.runtime) if book.runtime else None,
        language=book.language,
        credits=credits,
        external_ids=external_ids,
        extra=extra,
    )
    uri = book.streams[0] if book.streams else ""
    return MvRelease(
        work=work,
        uri=uri,
        image=book.image,
        stream_mode=StreamMode.ON_DEMAND,
        external_ids=external_ids,
        extra=extra,
    )
