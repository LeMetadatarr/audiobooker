from typing import List
from dataclasses import dataclass, field


@dataclass
class BookAuthor:
    first_name: str = ""
    last_name: str = ""


@dataclass
class AudiobookNarrator:
    first_name: str = ""
    last_name: str = ""


@dataclass
class AudioBook:
    title: str = ""
    description: str = ""
    image: str = ""
    language: str = ""
    authors: List[BookAuthor] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    streams: List[str] = field(default_factory=list)
    narrator: AudiobookNarrator = None
    year: int = 0
    runtime: int = 0
