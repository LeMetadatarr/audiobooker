"""Search audiobooker → typed mediavocab Release with parsed_license filtering.

Run:
  python examples/mediavocab_release.py
"""
from audiobooker import audiobook_to_release, search


def main() -> None:
    """Find Lovecraft titles whose mediavocab license parses as open."""
    print("Searching all sources for 'Lovecraft' (max 3 per source)...\n")
    for book in search("Lovecraft", max_per_source=3, timeout=30):
        release = audiobook_to_release(book)
        lic = release.parsed_license
        if lic and lic.is_open():
            title = release.work.title
            ident = lic.identifier
            print(f"[OPEN: {ident:14s}] {title}  ({book.source})")
        else:
            # Sources without an explicit public-domain stamp end up here.
            print(f"[unknown license] {release.work.title}  ({book.source})")


if __name__ == "__main__":
    main()
