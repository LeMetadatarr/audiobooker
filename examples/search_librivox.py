from pprint import pprint
from audiobooker.scrappers.librivox import Librivox

lv = Librivox()

print("=== search by title ===")
for book in lv.search_by_title("war of the worlds"):
    pprint(book.title)
    pprint(book.description)
    pprint(book.authors)
    pprint(book.streams)
    pprint(book.runtime)
    break

print("=== search by author ===")
for book in lv.search_by_author("Lovecraft"):
    pprint(book.title)
    pprint(book.authors)
    break

print("=== search by tag ===")
for book in lv.search_by_tag("horror"):
    pprint(book.title)
    break
