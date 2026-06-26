from backend.core.config import settings
from backend.core.privacy import make_safe_query, expand_query
from backend.services.search import multi_search

def safe_search(user_input: str) -> list[str]:

    if settings.PRIVACY_MODE == "HIGH":
        return []

    safe_query = make_safe_query(user_input)

    if not safe_query:
        return []

    queries = expand_query(safe_query)

    if not queries:
        queries = [safe_query]

    results = []

    for q in queries:
        try:
            res = multi_search(q)

            if isinstance(res, list):
                results.extend(res)
            elif isinstance(res, str):
                results.append(res)

        except Exception:
            continue

    clean_results = []
    seen = set()

    for r in results:
        r = r.strip()
        if r and r not in seen:
            seen.add(r)
            clean_results.append(r)

    return clean_results