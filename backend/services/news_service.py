from backend.services.news import get_news
from backend.services.search import multi_search


def get_safe_news():
    """
    Wrapper for news (can add filtering later)
    """

    news = get_news()

    # Clean + deduplicate
    clean = []
    seen = set()

    for n in news:
        n = n.strip()
        if n and n not in seen:
            seen.add(n)
            clean.append(n)

    return clean