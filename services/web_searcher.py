from concurrent.futures import ThreadPoolExecutor

from ddgs import DDGS


def search_whitelisted(query: str, domains: list[str], max_results: int = 20) -> list[dict]:
    """Search only whitelisted domains using DuckDuckGo site: operator."""
    site_filter = " OR ".join(f"site:{d}" for d in domains)
    full_query = f"{query} {site_filter}"

    try:
        results = DDGS().text(full_query, max_results=max_results)
    except Exception:
        results = []

    return _parse_results(results)


def search_per_domain(query: str, domains: list[str], results_per_domain: int = 3) -> list[dict]:
    """Search each whitelisted domain individually in parallel."""

    def _search_one(domain: str) -> list[dict]:
        try:
            results = DDGS().text(f"{query} site:{domain}", max_results=results_per_domain)
            return _parse_results(results)
        except Exception:
            return []

    with ThreadPoolExecutor(max_workers=len(domains)) as pool:
        all_results = list(pool.map(_search_one, domains))

    combined = []
    for batch in all_results:
        combined.extend(batch)
    return combined


def _parse_results(results: list) -> list[dict]:
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", ""),
            "snippet": r.get("body", ""),
        }
        for r in (results or [])
        if r.get("href")
    ]
