import logging
import random
import re

from bs4 import BeautifulSoup
from rapidfuzz import fuzz

# sitemapparser logs.critical when get_urls/get_sitemaps is called on the wrong
# root type — silence it; we guard with has_urls()/has_sitemaps() ourselves.
logging.getLogger("sitemapparser").setLevel(logging.ERROR)

USER_AGENTS = [
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/57.0.2987.110 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/61.0.3163.79 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) '
     'Gecko/20100101 '
     'Firefox/55.0'),  # firefox
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/61.0.3163.91 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/62.0.3202.89 '
     'Safari/537.36'),  # chrome
    ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/63.0.3239.108 '
     'Safari/537.36'),  # chrome
    ("Mozilla/5.0 (Windows NT 6.1; WOW64) "
     "AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/ 58.0.3029.81 Safari/537.36"),
]


def random_user_agent():
    return random.choice(USER_AGENTS)


def get_html(url, **kwargs):
    from audiobooker.scrappers import AudioBookSource
    try:
        return AudioBookSource.session.get(url, **kwargs).text
    except Exception:
        try:
            return AudioBookSource.session.get(url, verify=False, **kwargs).text
        except:
            return None


def get_soup(url, **kwargs):
    html = get_html(url, **kwargs)
    if html:
        return BeautifulSoup(html, "html.parser")


def extract_year(title: str) -> int:
    match = re.search(r'\b\d{4}\b', title)
    if match:
        return int(match.group())
    return 0


def extractor_narrator(title):
    from audiobooker.base import AudiobookNarrator
    narrator = None
    title = title.replace("\xa0", " ").strip()
    matches = re.findall(r'\b(?:read by|audiobook by|narrated by)\b\s*(.*?)(?:\s*–|$)', title, flags=re.IGNORECASE)

    if matches:
        narrator_str = matches[0].strip()  # Consider only the first "read by" occurrence
        # Split the narrator's name using a regex pattern
        names = re.findall(r'(?:[A-Z]\.)+|\S+', narrator_str)
        # Ensure we only take up to two words for the narrator's name
        names = names[:2]
        if len(names) > 0:
            first_name = names[0].strip()
            last_name = " ".join(names[1:]).strip() if len(names) > 1 else ""
            if last_name and first_name[0].isupper() and not last_name[0].isupper():
                last_name = ""  # not part of the name
            narrator = AudiobookNarrator(first_name=first_name.title(),
                                         last_name=last_name.title())
    return narrator


def normalize_name(name):
    """convert a name string to first and last name"""
    name = name.replace("(", "").replace(")", "").title().strip()
    if " " in name:
        return name.split(" ", 1)
    else:
        return name, ""


def _wratio(a: str, b: str) -> float:
    """rapidfuzz WRatio normalised to 0..1."""
    return fuzz.WRatio(a, b, processor=str.lower) / 100.0


def fuzzy_match(query: str, text: str, threshold: float = 0.80) -> bool:
    """Return True if query fuzzy-matches text at or above threshold (0..1)."""
    # WRatio handles partial matches, token reordering, and typos in one call
    return _wratio(query, text) >= threshold


def _title_score(query: str, title: str) -> float:
    """Score a query against a book title.

    Combines WRatio with a containment bonus so 'Harry Potter' in
    'Harry Potter and the Philosopher's Stone' scores higher than
    'Beatrix Potter' (which shares only the 'Potter' token).
    """
    base = fuzz.WRatio(query, title, processor=str.lower) / 100.0
    # Bonus when all query words appear in the title
    q_words = query.lower().split()
    t_lower = title.lower()
    if all(w in t_lower for w in q_words):
        base = min(1.0, base + 0.15)
    return base


_SCORE_WEIGHTS = {
    "title":    ("title",    0.55),
    "author":   ("author",   0.30),
    "tag":      ("tag",      0.10),
    "narrator": ("narrator", 0.05),
}

# Per-method field weights: only score the primary field at full weight
_METHOD_WEIGHTS = {
    "search_by_title":    {"title": 1.0},
    "search_by_author":   {"author": 1.0},
    "search_by_tag":      {"tag": 1.0},
    "search_by_narrator": {"narrator": 1.0},
    "search":             {"title": 0.55, "author": 0.30, "tag": 0.10, "narrator": 0.05},
    "iterate_all":        {},
}


def score_book(query: str, book, method: str = "search") -> float:
    """Return a relevance score 0..1 for query against an AudioBook.

    The scoring field weights depend on the search method so that
    search_by_title('Harry Potter') doesn't boost Beatrix Potter via author.
    """
    weights = _METHOD_WEIGHTS.get(method, _METHOD_WEIGHTS["search"])
    if not weights:
        return 0.0

    title_score = _title_score(query, book.title)

    author_score = 0.0
    for a in book.authors:
        full = f"{a.first_name} {a.last_name}".strip()
        s = max(_wratio(query, full), _wratio(query, a.last_name))
        author_score = max(author_score, s)

    tag_score = max((_wratio(query, t) for t in book.tags), default=0.0)

    narrator_score = 0.0
    if book.narrator:
        full = f"{book.narrator.first_name} {book.narrator.last_name}".strip()
        narrator_score = max(_wratio(query, full), _wratio(query, book.narrator.last_name))

    scores = {"title": title_score, "author": author_score,
              "tag": tag_score, "narrator": narrator_score}
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    return sum(scores[f] * w for f, w in weights.items()) / total_weight


def iter_sitemap_urls(url: str):
    """Yield every leaf URL from a sitemap or sitemap index, recursively.

    Handles both <urlset> (plain sitemap) and <sitemapindex> transparently
    without logging noise.  Silently skips URLs that fail to fetch or parse.
    """
    from sitemapparser import SiteMapParser
    try:
        sm = SiteMapParser(url)
    except Exception:
        return
    if sm.has_urls():
        for u in sm.get_urls():
            yield str(u)
    elif sm.has_sitemaps():
        for child in sm.get_sitemaps():
            yield from iter_sitemap_urls(str(child.loc))


def check_url_availability(url: str, timeout: int = 5) -> bool:
    """Return True if a HEAD request to url returns 2xx or 3xx."""
    from audiobooker.scrappers import AudioBookSource
    try:
        resp = AudioBookSource.session.head(url, timeout=timeout, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False
