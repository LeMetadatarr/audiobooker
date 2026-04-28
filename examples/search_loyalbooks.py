from pprint import pprint
from audiobooker.scrappers.loyalbooks import LoyalBooks

lb = LoyalBooks()

print("=== search by author ===")
for book in lb.search_by_author("Lovecraft"):
    pprint(book.title)
    pprint(book.streams)
    break

print("=== search by title ===")
for book in lb.search_by_title("sherlock"):
    pprint(book.title)
    break

print("=== iterate all (first 3) ===")
for i, book in enumerate(lb.iterate_all()):
    pprint(book.title)
    if i >= 2:
        break
