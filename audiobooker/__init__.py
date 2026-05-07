from audiobooker.base import (
    AudioBook as AudioBook,
    AudioBookChapter as AudioBookChapter,
    AudiobookNarrator as AudiobookNarrator,
    BookAuthor as BookAuthor,
    normalize_language as normalize_language,
)
from audiobooker.converters import audiobook_to_release as audiobook_to_release
from audiobooker.exceptions import (
    UnknownAuthorIdException as UnknownAuthorIdException,
    UnknownBookIdException as UnknownBookIdException,
    UnknownDurationError as UnknownDurationError,
    ScrappingError as ScrappingError,
    UnknownGenreIdException as UnknownGenreIdException,
    UnknownAuthorException as UnknownAuthorException,
    UnknownBookException as UnknownBookException,
    UnknownGenreException as UnknownGenreException,
    ParseErrorException as ParseErrorException,
)
from audiobooker.search import (
    search as search,
    search_by_title as search_by_title,
    search_by_author as search_by_author,
    search_by_narrator as search_by_narrator,
    search_by_tag as search_by_tag,
    ALL_SOURCES as ALL_SOURCES,
)
from audiobooker.utils import (
    check_url_availability as check_url_availability,
    score_book as score_book,
    iter_sitemap_urls as iter_sitemap_urls,
)
from audiobooker.index import BookIndex as BookIndex, IndexedSource as IndexedSource

try:
    from audiobooker.scrappers.youtube import (  # noqa: F401
        YoutubeChannelSource,
        YoutubePlaylistSource,
        TheCybrarian,
        HorrorBabble,
        TheDustyTome,
    )
except ImportError:
    pass

__all__ = [
    "AudioBook",
    "AudioBookChapter",
    "AudiobookNarrator",
    "BookAuthor",
    "normalize_language",
    "audiobook_to_release",
    "UnknownAuthorIdException",
    "UnknownBookIdException",
    "UnknownDurationError",
    "ScrappingError",
    "UnknownGenreIdException",
    "UnknownAuthorException",
    "UnknownBookException",
    "UnknownGenreException",
    "ParseErrorException",
    "search",
    "search_by_title",
    "search_by_author",
    "search_by_narrator",
    "search_by_tag",
    "ALL_SOURCES",
    "check_url_availability",
    "score_book",
    "iter_sitemap_urls",
    "BookIndex",
    "IndexedSource",
]
