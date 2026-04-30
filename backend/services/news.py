import requests
from backend.core.config import settings


def get_news():
    """
    Fetch real news using NewsAPI
    """

    url = "https://newsapi.org/v2/top-headlines"

    params = {
        "country": "us",
        "apiKey": settings.NEWS_API_KEY
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        articles = data.get("articles", [])

        headlines = [
            article.get("title", "")
            for article in articles[:5]
            if article.get("title")
        ]

        return headlines

    except Exception:
        return ["Unable to fetch news right now."]