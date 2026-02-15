# KidSearch Skills Reference

Reusable technical patterns and recipes from this project, organized by category.

---

## Search & Retrieval

### Domain-Restricted Search with `site:` Operators
**File**: `services/web_searcher.py:13-26`

Restrict search results to approved domains using DuckDuckGo's `site:` operator.

```python
site_filter = " OR ".join(f"site:{d}" for d in domains)
full_query = f"{query} {site_filter}"
results = DDGS().text(full_query, max_results=20)
```

**Reuse when**: Building safety-critical search, partner content aggregation, or curated knowledge bases.

---

### Parallel Per-Domain Search Fallback
**File**: `services/web_searcher.py:28-44`

Search each domain individually in parallel when combined search yields too few results.

```python
with ThreadPoolExecutor(max_workers=len(domains)) as pool:
    all_results = list(pool.map(_search_one, domains))
```

**Reuse when**: Single-query search misses niche content across multiple sources.

---

### URL Whitelist Validation (Domain Post-Filter)
**File**: `services/web_searcher.py:7-10`

Double-check URLs against a domain allowlist, handling exact matches and subdomains.

```python
def _is_whitelisted(url: str, domains: list[str]) -> bool:
    netloc = urlparse(url).netloc.lower()
    return any(netloc == d or netloc.endswith("." + d) for d in domains)
```

**Reuse when**: Defense-in-depth filtering, API access control, content moderation.

---

## AI / LLM Patterns

### Two-Model RAG Pipeline (Pro + Flash)
**File**: `services/gemini_summarizer.py:88-215`

Use an expensive model (Gemini Pro) for the main task and a cheaper model (Gemini Flash) for secondary tasks.

- **Pro**: Main summarization with citations (temperature 0.3, 16K tokens)
- **Flash**: Per-source summaries (temperature 0.3, 8K tokens)

**Reuse when**: Balancing quality vs. cost — primary task needs reasoning, secondary tasks are lightweight.

---

### Context-Only Summarization (No Web Tools)
**File**: `services/gemini_summarizer.py:143-160`

Provide pre-fetched article text to Gemini with NO web search tools enabled.

```python
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt,  # Only sources we provide
    config=genai.types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.3,
    ),
    # NO tools parameter — context-only
)
```

**Reuse when**: You need to control exactly which sources the AI can use, preventing hallucinations or unauthorized data access.

---

### System Prompt with Strict Output Constraints
**File**: `services/gemini_summarizer.py:24-38`

Enforce reading level, word count, citation format, and source usage.

```
- Use simple words that a 4th grader can understand
- Keep your answer between 200-300 words
- You MUST cite EVERY source provided
- Answer ONLY based on the provided sources
```

**Reuse when**: Any output needing consistent formatting — reports, customer emails, educational content.

---

### Citation Normalization (Regex)
**File**: `services/gemini_summarizer.py:155-160`

Convert multi-number citations `[1, 3, 5]` into individual markers `[1] [3] [5]`.

```python
def _expand_citations(m):
    nums = re.findall(r'\d+', m.group(1))
    return " ".join(f"[{n}]" for n in nums)

summary = re.sub(r'\[([\d,\s]+)\]', _expand_citations, summary)
```

**Reuse when**: Post-processing LLM output for consistent citation rendering.

---

### Keyword Relevance Scoring
**File**: `services/gemini_summarizer.py:41-45`

Fast heuristic to rank articles before sending to expensive LLM calls.

```python
def _relevance_score(query: str, title: str, content: str) -> int:
    query_words = set(re.findall(r'[a-z]{3,}', query.lower()))
    text = f"{title} {content}".lower()
    return sum(1 for w in query_words if w in text)
```

**Reuse when**: Filtering candidates before costly operations (embeddings, LLM calls).

---

### Structured LLM Output Parsing
**File**: `services/gemini_summarizer.py:194-222`

Ask LLM for numbered output format, parse with regex, with graceful fallback.

```python
for line in text.strip().split("\n"):
    match = re.match(r'\[(\d+)\]\s*(.+)', line.strip())
    if match:
        idx = int(match.group(1)) - 1
        desc = match.group(2).strip()
        if 0 <= idx < len(sources):
            sources[idx]["description"] = desc
```

**Reuse when**: Getting structured metadata from LLMs — summaries, labels, classifications.

---

## Web Scraping

### HTTP Client with Realistic Browser Headers
**File**: `services/content_extractor.py:6-26`

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
with httpx.Client(timeout=10.0, follow_redirects=True, max_redirects=10) as client:
    resp = client.get(url, headers=HEADERS)
    resolved_url = str(resp.url)  # Final URL after redirects
```

**Reuse when**: Scraping sites that block bots, following redirect chains.

---

### Open Graph Meta Tag Extraction with Fallbacks
**File**: `services/content_extractor.py:34-87`

Priority chain: `og:image` > `twitter:image` > first content image > Google favicon.

**Reuse when**: Building link previews, rich cards, or knowledge graphs.

---

### Article Content Extraction (Container Priority)
**File**: `services/content_extractor.py:133-155`

Try containers in order: `<article>` > `<main>` > `[role='main']` > `<body>`. Remove nav/footer/scripts first.

```python
for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
    tag.decompose()
```

**Reuse when**: Extracting main content from news sites, blogs, or educational pages.

---

### Smart Image Selection (Skip Icons/Pixels)
**File**: `services/content_extractor.py:46-62`

Filter out tracking pixels, logos, SVGs, and 1x1 spacers.

```python
skip_patterns = ["icon", "logo", "pixel", "tracker", "badge", "1x1", "spacer", ".svg", "data:image"]
```

**Reuse when**: Selecting meaningful images from scraped HTML.

---

## Streamlit UI

### Session State + Password Gate
**File**: `app.py:27-57`

```python
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if not st.session_state.authenticated:
    pwd = st.text_input("Password", type="password")
    if st.button("Enter") and pwd == APP_PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    st.stop()
```

**Reuse when**: Adding access control to any Streamlit app.

---

### Custom CSS with Gradient Branding
**File**: `app.py:60-381`

Key techniques:
- `background: linear-gradient(...)` for page and text gradients
- `-webkit-background-clip: text` for gradient text effect
- `transform: translateY(-2px)` for hover lift
- `-webkit-line-clamp: 2` for text truncation
- `::before` pseudo-elements for decorative overlays

**Reuse when**: Creating branded, polished Streamlit apps beyond default styling.

---

### Citation Badge Rendering
**File**: `app.py:385-400`

Convert `[1]` in text to clickable `<a class="cite" href="url">1</a>` badges.

```python
def _make_badge(num: int) -> str:
    url = sources[num - 1].get("resolved_url") or sources[num - 1]["url"]
    return f'<a class="cite" href="{url}" target="_blank">{num}</a>'

return re.sub(r'\[([\d,\s]+)\]', replace_cite_group, summary)
```

**Reuse when**: Building sourced content displays, academic paper viewers, fact-checked articles.

---

### Sidebar Search History with View/Clear
**File**: `app.py:464-490`

Store results in `st.session_state.search_history`, display in sidebar with "View" buttons.

```python
st.session_state.search_history.append(entry)  # Max 20
if st.button("View", key=f"hist_{idx}"):
    st.session_state.active_result = entry
    st.rerun()
```

**Reuse when**: Chat history, recent items, undo/redo, any session-scoped data.

---

## Deployment

### Dual Environment Loading (Secrets + .env)
**File**: `config.py:1-14`

```python
load_dotenv(Path(__file__).parent / ".env")  # Local dev
try:
    GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
```

**Reuse when**: Apps deployed to Streamlit Cloud, Docker, and local dev simultaneously.

---

### Docker + Streamlit
**File**: `Dockerfile`

```dockerfile
FROM python:3.12-slim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.headless=true"]
```

**Reuse when**: Deploying Streamlit to Cloud Run, Kubernetes, or any container platform.

---

### PWA for Chromebook Install
**Files**: `static/manifest.json`, `static/sw.js`, `app.py:17-25`

Minimal manifest + service worker makes Streamlit apps installable on Chromebooks.

**Reuse when**: Targeting school Chromebooks or mobile home screen installation.

---

### Dynamic Config from JSON (No Code Changes)
**File**: `config.py:17-21`, `whitelist.json`

```python
def load_whitelist() -> list[dict]:
    with open(whitelist_path, "r", encoding="utf-8") as f:
        return json.load(f)["sites"]
```

**Reuse when**: Managing allowed sources, feature flags, or site lists without code deploys.

---

## Concurrency

### ThreadPoolExecutor for Batch URL Fetching
**File**: `services/gemini_summarizer.py:58-61`

```python
with ThreadPoolExecutor(max_workers=10) as pool:
    articles = list(pool.map(lambda r: extract_article_text(r["url"]), results))
```

10 workers balances throughput vs. server load. Used for both content extraction and per-domain search.

**Reuse when**: Any I/O-bound batch operation — HTTP fetches, API calls, file processing.

---

### Deduplication via Mutable Set
**File**: `services/gemini_summarizer.py:51-85`

Pass a `seen_urls` set across multiple search phases to prevent duplicate processing.

```python
seen_urls: set = set()
candidates = _fetch_and_score(query, phase1_results, seen_urls)
candidates.extend(_fetch_and_score(query, phase2_results, seen_urls))  # Skips dupes
```

**Reuse when**: Multi-phase data pipelines, merging results from multiple sources.
