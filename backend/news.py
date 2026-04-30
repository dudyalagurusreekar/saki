import requests

API_KEY = "db38652cf5eb46ac806d843e2cc16dd0"  # 🔴 Put your real API key here

def get_news(max_results=5):
    url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={API_KEY}"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        headlines = []

        if data.get("status") != "ok":
            return ["⚠ Unable to fetch news"]

        for article in data.get("articles", [])[:max_results]:
            title = article.get("title")
            if title:
                headlines.append(title)

        return headlines if headlines else ["No news found"]

    except requests.exceptions.Timeout:
        return ["⚠ News request timed out"]

    except Exception as e:
        return [f"⚠ Error fetching news: {e}"]
