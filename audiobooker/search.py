"""Unified parallel search across all audiobooker sources."""
import queue
import threading
from typing import Iterable, List, Optional, Type

from audiobooker.base import AudioBook
from audiobooker.scrappers import AudioBookSource
from audiobooker.scrappers.librivox import Librivox
from audiobooker.scrappers.loyalbooks import LoyalBooks
from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
from audiobooker.scrappers.audioanarchy import AudioAnarchy
from audiobooker.scrappers.darkerprojects import DarkerProjects
from audiobooker.scrappers.hpaudiotales import HPTalesAudioBooks
from audiobooker.scrappers.stephenkingaudiobooks import StephenKingAudioBooks

_SENTINEL = object()

ALL_SOURCES: List[Type[AudioBookSource]] = [
    Librivox,
    LoyalBooks,
    StephenKingAudioBooks,
    GoldenAudioBooks,
    AudioAnarchy,
    DarkerProjects,
    HPTalesAudioBooks,
]


def _worker(source: AudioBookSource, method: str, query: Optional[str],
            result_queue: queue.Queue, max_results: int,
            stop: threading.Event) -> None:
    try:
        count = 0
        fn = getattr(source, method)
        iterable = fn(query) if query is not None else fn()
        for book in iterable:
            if stop.is_set():
                break
            result_queue.put(book)
            count += 1
            if 0 < max_results <= count:
                break
    except Exception:
        pass
    finally:
        result_queue.put(_SENTINEL)


def _parallel_search(method: str, query: Optional[str],
                     sources: Optional[List[AudioBookSource]],
                     max_per_source: int,
                     timeout: Optional[float]) -> Iterable[AudioBook]:
    if sources is None:
        sources = [cls() for cls in ALL_SOURCES]

    result_queue: queue.Queue = queue.Queue()
    stop_events = []

    for source in sources:
        stop = threading.Event()
        stop_events.append(stop)
        threading.Thread(
            target=_worker,
            args=(source, method, query, result_queue, max_per_source, stop),
            daemon=True,
        ).start()

    import time
    deadline = time.monotonic() + timeout if timeout is not None else None
    done = 0

    while done < len(sources):
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                for s in stop_events:
                    s.set()
                return  # daemon threads will clean up on their own
            try:
                item = result_queue.get(timeout=min(remaining, 1.0))
            except queue.Empty:
                continue
        else:
            item = result_queue.get()

        if item is _SENTINEL:
            done += 1
        else:
            yield item


def search(query: str,
           sources: Optional[List[AudioBookSource]] = None,
           max_per_source: int = 10,
           timeout: Optional[float] = 30.0) -> Iterable[AudioBook]:
    """Search all sources in parallel, yielding results as they arrive.

    Args:
        query: Search string matched against title, author, and tag.
        sources: Instantiated source objects. Defaults to all sources.
        max_per_source: Max results per source (0 = unlimited).
        timeout: Seconds before cancelling slow sources (default 30s).
    """
    yield from _parallel_search("search", query, sources, max_per_source, timeout)


def search_by_title(query: str,
                    sources: Optional[List[AudioBookSource]] = None,
                    max_per_source: int = 10,
                    timeout: Optional[float] = 30.0) -> Iterable[AudioBook]:
    """Search by title across all sources in parallel."""
    yield from _parallel_search("search_by_title", query, sources, max_per_source, timeout)


def search_by_author(query: str,
                     sources: Optional[List[AudioBookSource]] = None,
                     max_per_source: int = 10,
                     timeout: Optional[float] = 30.0) -> Iterable[AudioBook]:
    """Search by author across all sources in parallel."""
    yield from _parallel_search("search_by_author", query, sources, max_per_source, timeout)


def search_by_narrator(query: str,
                       sources: Optional[List[AudioBookSource]] = None,
                       max_per_source: int = 10,
                       timeout: Optional[float] = 30.0) -> Iterable[AudioBook]:
    """Search by narrator across all sources in parallel."""
    yield from _parallel_search("search_by_narrator", query, sources, max_per_source, timeout)


def search_by_tag(query: str,
                  sources: Optional[List[AudioBookSource]] = None,
                  max_per_source: int = 10,
                  timeout: Optional[float] = 30.0) -> Iterable[AudioBook]:
    """Search by tag across all sources in parallel."""
    yield from _parallel_search("search_by_tag", query, sources, max_per_source, timeout)
