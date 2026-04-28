import random
import re
from difflib import SequenceMatcher

from bs4 import BeautifulSoup

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
    except Exception as e:
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


def fuzzy_match(query: str, text: str, threshold: float = 0.80) -> bool:
    """Return True if query fuzzy-matches text above threshold."""
    q, t = query.lower(), text.lower()
    if q in t:
        return True
    # Single-word query: slide over text (catches "Lovecraft" inside "H. P. Lovecraft")
    if " " not in q and len(q) <= len(t):
        for i in range(len(t) - len(q) + 1):
            if SequenceMatcher(None, q, t[i:i + len(q)]).ratio() >= threshold:
                return True
        return False
    # Multi-word query: compare directly (sliding creates false positives like "stephen king" ≈ "stephen vinc")
    return SequenceMatcher(None, q, t).ratio() >= threshold


def check_url_availability(url: str, timeout: int = 5) -> bool:
    """Return True if a HEAD request to url returns 2xx or 3xx."""
    from audiobooker.scrappers import AudioBookSource
    try:
        resp = AudioBookSource.session.head(url, timeout=timeout, allow_redirects=True)
        return resp.status_code < 400
    except Exception:
        return False
