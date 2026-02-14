from ddgs import DDGS


def search_whitelisted(query: str, domains: list[str], max_results: int = 5) -> list[dict]:
    """Search only whitelisted domains using DuckDuckGo site: operator."""
    site_filter = " OR ".join(f"site:{d}" for d in domains)
    full_query = f"{query} {site_filter}"

    try:
        results = DDGS().text(full_query, max_results=max_results)
    except Exception:
        results = []

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in results
        if r.get("href")
    ]
