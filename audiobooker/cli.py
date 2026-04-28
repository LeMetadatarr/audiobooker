"""Click-based CLI for audiobooker.

Entry point: audiobooker (registered in pyproject.toml)

Commands
--------
  audiobooker search   <query>    — live search across web sources
  audiobooker index               — manage the local SQLite index
    index build
    index update
    index search  <query>
    index stats
    index follow  <url>
    index unfollow <url>
    index list
  audiobooker cache               — local file cache
    cache download <query>
    cache play     <query>
    cache list
    cache clear
    cache info     <query>
"""

import sys

import click

from audiobooker.cache import (
    clear_cache, download, is_cached, list_cached, cached_paths, play,
)
from audiobooker.index import BookIndex, _resolve_sources, _default_sources


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_db_option = click.option(
    "--db", default=None, metavar="PATH",
    help="Index database path (default ~/.audiobooker/index.db)",
)
_cache_option = click.option(
    "--cache-dir", default=None, metavar="PATH",
    help="Cache directory (default ~/.cache/audiobooker)",
)
_source_option = click.option(
    "--source", default=None, metavar="NAME",
    help="Limit to books from this source",
)
_language_option = click.option(
    "--language", default=None, metavar="CODE",
    help="Limit to books with this language code (e.g. en, de)",
)
_n_option = click.option(
    "-n", default=10, show_default=True,
    help="Maximum number of results",
)
_min_score_option = click.option(
    "--min-score", default=0.45, show_default=True, metavar="FLOAT",
    help="Minimum fuzzy match score (0–1)",
)
_min_dur_option = click.option(
    "--min-duration", default=0, metavar="SECS",
    help="Minimum runtime in seconds",
)
_max_dur_option = click.option(
    "--max-duration", default=0, metavar="SECS",
    help="Maximum runtime in seconds",
)
_method_option = click.option(
    "--method",
    type=click.Choice(["search", "search_by_title", "search_by_author",
                       "search_by_tag", "search_by_narrator"]),
    default="search_by_title", show_default=True,
    help="Search method",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_book(book, verbose: bool = False):
    authors = ", ".join(
        f"{a.first_name} {a.last_name}".strip() for a in book.authors
    ) or "?"
    score = f"[{book.score:.2f}] " if book.score else ""
    runtime = f"  {book.runtime // 60}min" if book.runtime else ""
    click.echo(f"  {score}{book.title!r}  — {authors}{runtime}  [{book.source}]")
    if verbose:
        if book.tags:
            click.echo(f"      tags: {', '.join(book.tags)}")
        if book.narrator:
            n = f"{book.narrator.first_name} {book.narrator.last_name}".strip()
            click.echo(f"      narrator: {n}")
        if book.streams:
            click.echo(f"      streams: {len(book.streams)}")
            for s in book.streams[:2]:
                click.echo(f"        {s}")


def _open_index(db):
    return BookIndex(db)


def _find_book(query, method, db, source):
    """Look up a book: index first, live Librivox fallback."""
    from audiobooker.scrappers.librivox import Librivox
    try:
        idx = _open_index(db)
        fn = getattr(idx, method)
        kw = {"max_results": 1}
        if source:
            kw["source"] = source
        results = fn(query, **kw)
        idx.close()
        if results:
            return results[0]
    except Exception:
        pass
    src = Librivox()
    fn = getattr(src, method, src.search_by_title)
    for book in fn(query):
        if source and book.source != source:
            continue
        return book
    return None


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="audiobooker")
def cli():
    """audiobooker — search, index, and cache audiobooks from the web."""


# ---------------------------------------------------------------------------
# audiobooker search
# ---------------------------------------------------------------------------

@cli.command("search")
@click.argument("query")
@_method_option
@_n_option
@_min_score_option
@_source_option
@_language_option
@_min_dur_option
@_max_dur_option
@click.option("--timeout", default=30, show_default=True, metavar="SECS")
@click.option("-v", "--verbose", is_flag=True)
def cmd_search(query, method, n, min_score, source, language,
               min_duration, max_duration, timeout, verbose):
    """Live search across all web sources."""
    from audiobooker import search as live_search
    from audiobooker.scrappers.librivox import Librivox
    from audiobooker.scrappers.loyalbooks import LoyalBooks
    from audiobooker.scrappers.goldenaudiobooks import GoldenAudioBooks
    from audiobooker.scrappers.audioanarchy import AudioAnarchy
    from audiobooker.scrappers.darkerprojects import DarkerProjects

    sources = [Librivox(), LoyalBooks(), AudioAnarchy(), DarkerProjects(), GoldenAudioBooks()]
    count = 0
    for book in live_search(query, sources=sources, timeout=timeout,
                            max_per_source=n):
        if source and book.source != source:
            continue
        if language and book.language != language:
            continue
        if min_duration and book.runtime < min_duration:
            continue
        if max_duration and book.runtime > max_duration:
            continue
        _print_book(book, verbose)
        count += 1
        if count >= n:
            break
    if not count:
        click.echo("No results.")


# ---------------------------------------------------------------------------
# audiobooker index  (sub-group)
# ---------------------------------------------------------------------------

@cli.group("index")
@_db_option
@click.pass_context
def cmd_index(ctx, db):
    """Manage the local SQLite book index."""
    ctx.ensure_object(dict)
    ctx.obj["db"] = db


@cmd_index.command("build")
@click.option("--sources", "-s", multiple=True, metavar="NAME",
              help="Source names (default: all web sources)")
@click.pass_context
def index_build(ctx, sources):
    """Clear and rebuild the index for the given sources."""
    db = ctx.obj["db"]
    src_list = _resolve_sources(sources) if sources else None
    idx = _open_index(db)
    click.echo("Building index…")
    total = idx.build(sources=src_list)
    idx.close()
    click.echo(f"Done. {total} books indexed.")


@cmd_index.command("update")
@click.option("--sources", "-s", multiple=True, metavar="NAME",
              help="Source names (default: all + followed YouTube sources)")
@click.pass_context
def index_update(ctx, sources):
    """Add new books without clearing existing records."""
    db = ctx.obj["db"]
    src_list = _resolve_sources(sources) if sources else None
    idx = _open_index(db)
    click.echo("Updating index…")
    total = idx.update(sources=src_list)
    idx.close()
    click.echo(f"Done. {total} new books added.")


@cmd_index.command("stats")
@click.pass_context
def index_stats(ctx):
    """Show index statistics."""
    db = ctx.obj["db"]
    idx = _open_index(db)
    s = idx.stats()
    idx.close()
    click.echo(f"Total books: {s['total']}\n")
    click.echo("By source:")
    for src, n in s["by_source"].items():
        click.echo(f"  {src:30s} {n}")
    click.echo("\nBy language:")
    for lang, n in s["by_language"].items():
        click.echo(f"  {lang or '(unknown)':10s} {n}")


@cmd_index.command("search")
@click.argument("query")
@_method_option
@_n_option
@_min_score_option
@_source_option
@_language_option
@_min_dur_option
@_max_dur_option
@click.option("-v", "--verbose", is_flag=True)
@click.pass_context
def index_search(ctx, query, method, n, min_score, source, language,
                 min_duration, max_duration, verbose):
    """Search the local index."""
    db = ctx.obj["db"]
    idx = _open_index(db)
    fn = getattr(idx, method)
    kw = dict(max_results=n, min_score=min_score)
    if source:
        kw["source"] = source
    if language:
        kw["language"] = language
    if min_duration:
        kw["min_duration"] = min_duration
    if max_duration:
        kw["max_duration"] = max_duration
    results = fn(query, **kw)
    idx.close()
    click.echo(f"{len(results)} result(s) for {query!r}:\n")
    for book in results:
        _print_book(book, verbose)
    if not results:
        click.echo("No results.")


@cmd_index.command("follow")
@click.argument("url")
@click.option("--kind", type=click.Choice(["channel", "playlist"]),
              default="channel", show_default=True)
@click.option("--name", default="", help="Human-readable label")
@click.option("--tags", multiple=True, metavar="TAG")
@click.option("--language", default="en", show_default=True)
@click.option("--min-runtime", default=300, show_default=True, metavar="SECS",
              help="Skip videos shorter than N seconds")
@click.option("--blacklist", multiple=True, metavar="PHRASE",
              help="Skip books whose title contains this string (repeatable)")
@click.pass_context
def index_follow(ctx, url, kind, name, tags, language, min_runtime, blacklist):
    """Follow a YouTube channel or playlist."""
    db = ctx.obj["db"]
    idx = _open_index(db)
    idx.follow(url, kind=kind, name=name, tags=list(tags),
               language=language, min_runtime=min_runtime,
               title_blacklist=list(blacklist))
    idx.close()
    label = name or url
    click.echo(f"Following {kind}: {label}")


@cmd_index.command("unfollow")
@click.argument("url")
@click.pass_context
def index_unfollow(ctx, url):
    """Stop following a YouTube channel or playlist."""
    db = ctx.obj["db"]
    idx = _open_index(db)
    removed = idx.unfollow(url)
    idx.close()
    if removed:
        click.echo(f"Unfollowed: {url}")
    else:
        click.secho(f"Not found: {url}", fg="yellow")


@cmd_index.command("list")
@click.pass_context
def index_list(ctx):
    """List all followed YouTube sources."""
    db = ctx.obj["db"]
    idx = _open_index(db)
    followed = idx.list_followed()
    idx.close()
    if not followed:
        click.echo("No followed sources.")
        return
    click.echo(f"{'Kind':<10} {'Name/URL':<50} {'Lang':<6} {'Tags'}")
    click.echo("-" * 80)
    for f in followed:
        label = f["name"] or f["url"]
        tags = ", ".join(f["tags"]) if f["tags"] else ""
        bl = f"  blacklist={f['title_blacklist']}" if f["title_blacklist"] else ""
        click.echo(f"  {f['kind']:<8} {label:<50} {f['language']:<6} {tags}{bl}")


# ---------------------------------------------------------------------------
# audiobooker cache  (sub-group)
# ---------------------------------------------------------------------------

@cli.group("cache")
@_cache_option
@click.pass_context
def cmd_cache(ctx, cache_dir):
    """Download and manage cached audiobook files."""
    ctx.ensure_object(dict)
    from pathlib import Path
    ctx.obj["cache_root"] = Path(cache_dir) if cache_dir else None


@cmd_cache.command("download")
@click.argument("query")
@_method_option
@_source_option
@_db_option
@click.option("--stream", default=None, type=int, metavar="INDEX",
              help="Stream index (default: all)")
@click.pass_context
def cache_download(ctx, query, method, source, db, stream):
    """Download a book's streams to cache."""
    cache_root = ctx.obj["cache_root"]
    book = _find_book(query, method, db, source)
    if not book:
        click.secho(f"No results for {query!r}", fg="red")
        sys.exit(1)
    click.echo(f"Downloading: {book.title!r}")
    paths = download(book, stream=stream, cache_root=cache_root)
    if paths:
        click.echo(f"\nDownloaded {len(paths)} file(s):")
        for p in paths:
            click.echo(f"  {p}")
    else:
        click.secho("Download failed.", fg="red")
        sys.exit(1)


@cmd_cache.command("play")
@click.argument("query")
@_method_option
@_source_option
@_db_option
@click.option("--stream", default=0, show_default=True, type=int)
@click.pass_context
def cache_play(ctx, query, method, source, db, stream):
    """Play a book (downloads to cache first if needed)."""
    cache_root = ctx.obj["cache_root"]
    book = _find_book(query, method, db, source)
    if not book:
        click.secho(f"No results for {query!r}", fg="red")
        sys.exit(1)
    click.echo(f"Playing: {book.title!r}")
    play(book, stream=stream, cache_root=cache_root)


@cmd_cache.command("list")
@click.pass_context
def cache_list(ctx):
    """List all cached books."""
    cache_root = ctx.obj["cache_root"]
    books = list(list_cached(cache_root))
    if not books:
        click.echo("Cache is empty.")
        return
    total_kb = 0
    for book in books:
        paths = cached_paths(book, cache_root)
        size_kb = sum(p.stat().st_size for p in paths if p.exists()) // 1024
        total_kb += size_kb
        click.echo(f"  {book.title!r}  [{book.source}]  {size_kb}KB  {len(paths)} file(s)")
    click.echo(f"\nTotal: {len(books)} book(s), {total_kb}KB")


@cmd_cache.command("clear")
@click.argument("query", required=False)
@_method_option
@_source_option
@_db_option
@click.confirmation_option(prompt="Clear cache?")
@click.pass_context
def cache_clear(ctx, query, method, source, db):
    """Clear cache for one book or the entire cache."""
    cache_root = ctx.obj["cache_root"]
    if query:
        book = _find_book(query, method, db, source)
        if not book:
            click.secho(f"No results for {query!r}", fg="red")
            sys.exit(1)
        n = clear_cache(book, cache_root)
        click.echo(f"Cleared {n} cached book(s).")
    else:
        n = clear_cache(cache_root=cache_root)
        click.echo(f"Cleared {n} cached book(s).")


@cmd_cache.command("info")
@click.argument("query")
@_method_option
@_source_option
@_db_option
@click.pass_context
def cache_info(ctx, query, method, source, db):
    """Show cache status for a book."""
    cache_root = ctx.obj["cache_root"]
    book = _find_book(query, method, db, source)
    if not book:
        click.secho(f"No results for {query!r}", fg="red")
        sys.exit(1)
    click.echo(f"Title:   {book.title}")
    click.echo(f"Source:  {book.source}")
    click.echo(f"Cached:  {is_cached(book, cache_root)}")
    click.echo(f"Streams: {len(book.streams)}")
    from audiobooker.cache import _book_dir, _stream_filename, _DEFAULT_CACHE
    root = cache_root or _DEFAULT_CACHE
    for i, url in enumerate(book.streams):
        local = _book_dir(book, root) / _stream_filename(url, i)
        status = f"{local.stat().st_size // 1024}KB" if local.exists() else "not cached"
        click.echo(f"  [{i}] {url}")
        click.echo(f"       → {local}  ({status})")


if __name__ == "__main__":
    cli()
