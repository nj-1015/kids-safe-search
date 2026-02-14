from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

# Realistic browser headers to avoid blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def extract_metadata(url: str) -> dict:
    """Fetch a URL and extract og:image, description, and resolved URL."""
    result = {"image_url": "", "description": "", "resolved_url": url}

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, max_redirects=10) as client:
            resp = client.get(url, headers=HEADERS)
            result["resolved_url"] = str(resp.url)
            resp.raise_for_status()
    except Exception:
        # Even if fetch fails, set a favicon fallback
        _set_favicon_fallback(result)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Extract image ---
    # Priority: og:image > twitter:image > first content image
    for selector in [
        ("meta", {"property": "og:image"}),
        ("meta", {"attrs": {"name": "twitter:image"}}),
        ("meta", {"attrs": {"name": "twitter:image:src"}}),
    ]:
        tag = soup.find(selector[0], **selector[1])
        if tag and tag.get("content"):
            result["image_url"] = tag["content"]
            break

    # Fallback: first reasonably-sized image in content
    if not result["image_url"]:
        for container_tag in ["article", "main", "body"]:
            container = soup.find(container_tag)
            if container:
                for img in container.find_all("img", src=True, limit=5):
                    src = img.get("src", "")
                    # Skip tiny icons, tracking pixels, SVGs
                    if any(skip in src.lower() for skip in [
                        "icon", "logo", "pixel", "tracker", "badge",
                        "1x1", "spacer", ".svg", "data:image",
                    ]):
                        continue
                    result["image_url"] = src
                    break
                if result["image_url"]:
                    break

    # Make relative URLs absolute
    if result["image_url"] and not result["image_url"].startswith("http"):
        if result["image_url"].startswith("//"):
            result["image_url"] = "https:" + result["image_url"]
        elif result["image_url"].startswith("/"):
            parsed = urlparse(result["resolved_url"])
            result["image_url"] = f"{parsed.scheme}://{parsed.netloc}{result['image_url']}"

    # Final fallback: Google favicon
    if not result["image_url"]:
        _set_favicon_fallback(result)

    # --- Extract description ---
    for selector in [
        ("meta", {"property": "og:description"}),
        ("meta", {"attrs": {"name": "description"}}),
        ("meta", {"attrs": {"name": "twitter:description"}}),
    ]:
        tag = soup.find(selector[0], **selector[1])
        if tag and tag.get("content"):
            result["description"] = tag["content"][:300]
            break

    return result


def extract_article_text(url: str) -> dict:
    """Fetch a URL and extract article text, title, image, and resolved URL."""
    result = {"text": "", "title": "", "image_url": "", "url": url, "resolved_url": url}

    try:
        with httpx.Client(timeout=10.0, follow_redirects=True, max_redirects=10) as client:
            resp = client.get(url, headers=HEADERS)
            result["resolved_url"] = str(resp.url)
            resp.raise_for_status()
    except Exception:
        _set_favicon_fallback(result)
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    # Extract title
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        result["title"] = og_title["content"]
    elif soup.title and soup.title.string:
        result["title"] = soup.title.string.strip()

    # Extract image (same logic as extract_metadata)
    for selector in [
        ("meta", {"property": "og:image"}),
        ("meta", {"attrs": {"name": "twitter:image"}}),
    ]:
        tag = soup.find(selector[0], **selector[1])
        if tag and tag.get("content"):
            result["image_url"] = tag["content"]
            break

    if not result["image_url"]:
        _set_favicon_fallback(result)

    # Make relative image URLs absolute
    if result["image_url"] and not result["image_url"].startswith("http"):
        if result["image_url"].startswith("//"):
            result["image_url"] = "https:" + result["image_url"]
        elif result["image_url"].startswith("/"):
            parsed = urlparse(result["resolved_url"])
            result["image_url"] = f"{parsed.scheme}://{parsed.netloc}{result['image_url']}"

    # Remove non-content elements
    for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
        tag.decompose()

    # Extract article text from best container
    article_text = ""
    for container_tag in ["article", "main", "[role='main']"]:
        container = soup.select_one(container_tag) if "[" in container_tag else soup.find(container_tag)
        if container:
            paragraphs = container.find_all("p")
            article_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if len(article_text) > 100:
                break

    # Fallback: all paragraphs in body
    if len(article_text) < 100:
        body = soup.find("body")
        if body:
            paragraphs = body.find_all("p")
            article_text = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    # Truncate to keep Gemini context manageable
    result["text"] = article_text[:2000]
    return result


def _set_favicon_fallback(result: dict):
    """Set a Google favicon as fallback image."""
    try:
        parsed = urlparse(result["resolved_url"])
        domain = parsed.netloc or parsed.path
        if domain:
            result["image_url"] = (
                f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
            )
    except Exception:
        pass
