"""06 — Convert an AudioBook to a mediavocab Release.

Shows the full field coverage: Work, credits, chapters, external_ids,
codec/bitrate, license.

Requires: pip install audiobooker mediavocab
Run:      python examples/06_convert_to_mediavocab.py
"""
from audiobooker import audiobook_to_release
from audiobooker.scrappers.librivox import Librivox


def fmt_offset(seconds: float) -> str:
    s = int(seconds)
    h, r = divmod(s, 3600)
    m, sec = divmod(r, 60)
    return f"{h}:{m:02d}:{sec:02d}"


book = next(Librivox().search_by_author("Lovecraft"), None)
if book is None:
    print("No results.")
else:
    release = audiobook_to_release(book)
    work = release.work
    lic = release.license_model

    print(f"Title:        {work.title}")
    print(f"Year:         {work.year}")
    print(f"Runtime:      {fmt_offset(work.runtime or 0)}")
    print(f"Language:     {work.language}")
    print(f"Genres:       {', '.join(work.content_genres) or '(none)'}")
    print(f"Codec:        {release.codec} @ {release.bitrate} kbps")
    print(f"License:      {release.license}  open={lic.is_open() if lic else False}")
    print(f"External IDs: {release.external_ids}")
    print()

    authors = [c.entity.name for c in work.credits if c.role == "author"]
    narrators = [c.entity.name for c in work.credits if c.role == "narrator"]
    print(f"Authors:   {', '.join(authors) or '(none)'}")
    print(f"Narrators: {', '.join(narrators) or '(none)'}")
    print()

    print(f"Chapters ({len(release.chapters)}):")
    for i, ch in enumerate(release.chapters[:8], 1):
        end = f" → {fmt_offset(ch.end)}" if ch.end else ""
        print(f"  {i:2d}. [{fmt_offset(ch.offset)}]{end}  {ch.title}")
    if len(release.chapters) > 8:
        print(f"  ... ({len(release.chapters) - 8} more)")
