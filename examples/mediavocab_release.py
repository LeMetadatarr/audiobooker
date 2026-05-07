"""Search audiobooker → typed mediavocab Release with rich field coverage.

Shows off the fields the LibriVox scraper now populates end-to-end:
  - chapters (per-section offsets, titles, durations)
  - narrators (author + reader credits)
  - content_genres
  - external_ids (librivox_id)
  - codec / bitrate / audio_language
  - parsed_license (public_domain → is_open())

Run:
  python examples/mediavocab_release.py
"""
from audiobooker import audiobook_to_release
from audiobooker.scrappers.librivox import Librivox


def _format_offset(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{sec:02d}"


def main() -> None:
    print("Searching LibriVox for 'Lovecraft' (first hit)...\n")
    book = next(Librivox().search_by_author("Lovecraft"), None)
    if book is None:
        print("No results.")
        return

    release = audiobook_to_release(book)
    work = release.work
    lic = release.parsed_license

    print(f"Title:          {work.title}")
    print(f"Source:         {book.source}")
    print(f"Year:           {work.year}")
    print(f"Runtime:        {_format_offset(work.runtime or 0)}")
    print(f"Language:       {work.language}")
    print(f"Audio language: {release.audio_language}")
    print(f"Codec/bitrate:  {release.codec} @ {release.bitrate} kbps")
    print(f"Genres:         {', '.join(work.content_genres) or '(none)'}")
    print(f"License:        {release.license}"
          f"  (open={lic.is_open() if lic else False})")
    print(f"External IDs:   {release.external_ids}")
    print()

    authors = [c.entity.name for c in work.credits if c.role == "author"]
    narrators = [c.entity.name for c in work.credits if c.role == "narrator"]
    print(f"Authors:        {', '.join(authors) or '(none)'}")
    print(f"Narrators:      {', '.join(narrators) or '(none)'}")
    print()

    print(f"Chapters ({len(release.chapters)}):")
    for i, c in enumerate(release.chapters[:10], 1):
        print(f"  {i:2d}. [{_format_offset(c.offset)}] {c.title}")
    if len(release.chapters) > 10:
        print(f"  ... ({len(release.chapters) - 10} more)")


if __name__ == "__main__":
    main()
