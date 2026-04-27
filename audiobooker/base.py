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
    s = lang.strip().lower()
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
class AudioBook:
    title: str = ""
    description: str = ""
    image: str = ""
    language: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    streams: List[str] = field(default_factory=list)
    narrator: Optional[AudiobookNarrator] = None
    year: int = 0
    runtime: int = 0
    source: str = ""

    def __post_init__(self):
        if self.language:
            self.language = normalize_language(self.language)

    def __hash__(self):
        author_key = tuple(sorted(
            (a.first_name.lower(), a.last_name.lower()) for a in self.authors
        ))
        return hash((self.title.lower().strip(), author_key))

    def __eq__(self, other):
        if not isinstance(other, AudioBook):
            return False
        return hash(self) == hash(other)

    def has_live_streams(self) -> bool:
        """Return True if at least one stream URL is reachable."""
        from audiobooker.utils import check_url_availability
        return any(check_url_availability(s) for s in self.streams)
