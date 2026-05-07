import hashlib
from typing import List, Optional
from dataclasses import dataclass, field

_LANG_MAP = {
    "english": "en", "french": "fr", "german": "de", "spanish": "es",
    "italian": "it", "portuguese": "pt", "dutch": "nl", "russian": "ru",
    "polish": "pl", "swedish": "sv", "norwegian": "no", "danish": "da",
    "finnish": "fi", "hungarian": "hu", "czech": "cs", "romanian": "ro",
    "chinese": "zh", "japanese": "ja", "korean": "ko", "arabic": "ar",
    "latin": "la", "greek": "el", "turkish": "tr", "hebrew": "he",
}


def normalize_language(lang: str) -> str:
    """Normalise any language string to an ISO 639-1 code."""
    if not lang:
        return ""
    # strip region subtag: "en-US", "en_US" → "en"
    s = lang.strip().lower().split("-")[0].split("_")[0]
    if s in _LANG_MAP:
        return _LANG_MAP[s]
    if len(s) == 2:
        return s
    for key, code in _LANG_MAP.items():
        if s.startswith(key[:4]):
            return code
    return s


@dataclass
class BookAuthor:
    first_name: str = ""
    last_name: str = ""

    def __hash__(self):
        return hash((self.first_name.lower(), self.last_name.lower()))

    def __eq__(self, other):
        if not isinstance(other, BookAuthor):
            return False
        return self.first_name.lower() == other.first_name.lower() and \
               self.last_name.lower() == other.last_name.lower()


@dataclass
class AudiobookNarrator:
    first_name: str = ""
    last_name: str = ""

    def __hash__(self):
        return hash((self.first_name.lower(), self.last_name.lower()))

    def __eq__(self, other):
        if not isinstance(other, AudiobookNarrator):
            return False
        return self.first_name.lower() == other.first_name.lower() and \
               self.last_name.lower() == other.last_name.lower()


@dataclass
class AudioBookChapter:
    """A single chapter / section of an audiobook.

    ``offset`` is the start position in seconds from the beginning of the
    book. ``runtime`` is the chapter duration in seconds. ``stream`` is the
    per-chapter audio URL when known.
    """
    title: str = ""
    offset: float = 0.0
    runtime: float = 0.0
    stream: str = ""
    image: str = ""


@dataclass
class AudioBook:
    title: str = ""
    description: str = ""
    image: str = ""
    language: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    streams: List[str] = field(default_factory=list)
    narrator: Optional[AudiobookNarrator] = None
    narrators: List[AudiobookNarrator] = field(default_factory=list)
    chapters: List[AudioBookChapter] = field(default_factory=list)
    genres: List[str] = field(default_factory=list)
    year: int = 0
    runtime: int = 0
    source: str = ""
    score: float = 0.0
    # Codec / bitrate of the primary audio stream when known by the source.
    codec: str = ""
    bitrate: str = ""
    # Source-specific identifiers (e.g. librivox_id, gutenberg_id, isbn_13).
    # Keys must match mediavocab.ExternalIds field names where applicable.
    external_ids: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.language:
            self.language = normalize_language(self.language)
        # Keep singular ``narrator`` and plural ``narrators`` consistent so
        # callers can use either.  When both are supplied, the list is
        # authoritative; ``narrator`` is reconciled to its first element.
        if self.narrator and not self.narrators:
            self.narrators = [self.narrator]
        elif self.narrators:
            self.narrator = self.narrators[0]

    def __hash__(self):
        return int(self.stable_id(), 16) & 0x7FFFFFFFFFFFFFFF

    def __eq__(self, other):
        if not isinstance(other, AudioBook):
            return False
        return self.stable_id() == other.stable_id()

    def stable_id(self) -> str:
        """Deterministic hex digest derived from title + authors.

        Safe to use as a cache directory name or database key — unlike
        Python's built-in hash(), this value is stable across processes
        and Python versions (not affected by PYTHONHASHSEED).
        """
        author_key = "|".join(sorted(
            f"{a.first_name.lower()}_{a.last_name.lower()}" for a in self.authors
        ))
        raw = f"{self.title.lower().strip()}||{author_key}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def has_live_streams(self) -> bool:
        """Return True if at least one stream URL is reachable."""
        from audiobooker.utils import check_url_availability
        return any(check_url_availability(s) for s in self.streams)
