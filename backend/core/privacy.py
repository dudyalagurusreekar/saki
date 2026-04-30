from backend.services.ai_service import call_model


def make_safe_query(user_input: str) -> str:
    """
    Converts user input into a neutral, non-sensitive search query.
    Ensures no personal/emotional data is sent externally.
    """

    prompt = f"""
Convert this into a neutral, general search query.
Remove personal or sensitive details.

User input: {user_input}

Safe query:
"""

    result = call_model(prompt)

    if not result:
        return user_input

    return result.strip()


def expand_query(query: str) -> list[str]:
    """
    Expands a query into 1–2 smaller queries for better search coverage.
    """

    prompt = f"""
Break this into 2 short search queries:

Query: {query}
"""

    result = call_model(prompt)

    if not result:
        return [query]

    lines = [
        line.strip()
        for line in result.split("\n")
        if line.strip()
    ]

    return lines[:2] if lines else [query]