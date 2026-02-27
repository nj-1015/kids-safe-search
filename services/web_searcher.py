from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

from ddgs import DDGS

from config import load_whitelist

# Build a lookup for domains that require path prefix checking
_SITES = load_whitelist()
_PATH_PREFIXES = {s["domain"]: s["path_prefix"] for s in _SITES if s.get("path_prefix")}


def _is_whitelisted(url: str, domains: list[str]) -> bool:
    """Check if a URL belongs to one of the whitelisted domains (with optional path prefix)."""
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    for d in domains:
        if netloc == d or netloc.endswith("." + d):
            # If this domain has a path_prefix requirement, check the path too
            prefix = _PATH_PREFIXES.get(d)
            if prefix and not parsed.path.lower().startswith(prefix):
                return False
            return True
    return False


def search_whitelisted(query: str, domains: list[str], max_results: int = 20) -> list[dict]:
    """Search only whitelisted domains using DuckDuckGo site: operator."""
    site_filter = " OR ".join(f"site:{d}" for d in domains)
    full_query = f"{query} {site_filter}"

    try:
        results = DDGS().text(full_query, max_results=max_results)
    except Exception:
        results = []

    # Post-filter: DuckDuckGo site: operator sometimes leaks non-whitelisted URLs
    parsed = _parse_results(results)
    return [r for r in parsed if _is_whitelisted(r["url"], domains)]


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
    return [r for r in combined if _is_whitelisted(r["url"], domains)]


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
