# KidSearch Architecture

A kid-friendly search engine that searches only parent-approved educational websites, summarizes results with AI, and presents them with inline citations.

## System Overview

```
User Question
      |
DuckDuckGo Search (site: filters for 15 whitelisted domains)
      |  Phase 1: combined search (max 20 results)
      |  Phase 2: per-domain search (3 per domain, parallel)
      |
Content Extraction (httpx + BeautifulSoup, 10 parallel workers)
      |  Score by keyword relevance, keep top 5
      |
Gemini 2.5 Pro (context-only, no web tools)
      |  Kid-friendly summary with [1] [2] citations
      |
Gemini 2.5 Flash (generate per-source summaries)
      |
Streamlit UI (answer card + source cards + search history sidebar)
```

## Files

| File | Purpose |
|------|---------|
| `app.py` | Streamlit UI, CSS, session history, citation rendering |
| `config.py` | API key loading, whitelist loading |
| `services/web_searcher.py` | DuckDuckGo search with `site:` domain restriction |
| `services/gemini_summarizer.py` | RAG pipeline orchestrator |
| `services/content_extractor.py` | Article text + image extraction from URLs |
| `whitelist.json` | 15 approved educational sites |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | Streamlit server config |
| `static/manifest.json` | PWA manifest for Chromebook install |
| `static/sw.js` | Service worker (minimal) |
| `Dockerfile` | Docker deployment (port 8080) |
| `.devcontainer/devcontainer.json` | GitHub Codespaces config |

## Data Flow

### 1. Search (web_searcher.py)

```
search_whitelisted(query, domains, max_results=20)
  -> DuckDuckGo: "{query} site:kiddle.co OR site:ducksters.com OR ..."
  -> Post-filter: _is_whitelisted() removes any leaked non-whitelisted URLs
  -> Returns: [{title, url, snippet}]

search_per_domain(query, domains, results_per_domain=3)
  -> ThreadPoolExecutor: search each domain individually
  -> DuckDuckGo: "{query} site:{domain}" x 15 domains in parallel
  -> Post-filter + combine
  -> Returns: [{title, url, snippet}]
```

### 2. Fetch & Score (gemini_summarizer.py)

```
_fetch_and_score(query, search_results, seen_urls)
  -> ThreadPoolExecutor (10 workers): extract_article_text(url) for each result
  -> Deduplicate via seen_urls set
  -> Score: count of 3+ char query words found in title + content
  -> Returns: [{title, url, resolved_url, image_url, content, score}]
```

### 3. Select Top 5

```
All candidates sorted by score (descending)
Take first 5 regardless of score threshold
Build context: "[1] Title (URL)\n{content}" for each
```

### 4. Gemini Summarization

**Model**: gemini-2.5-pro | **Temperature**: 0.3 | **Max tokens**: 16,384

**System prompt** instructs Gemini to:
- Write at 4th-grade reading level (200-300 words)
- Use examples and comparisons
- Cite EVERY source with [1], [2], etc.
- Only use information from provided sources

**Input**: Question + 5 numbered source articles

**Output**: Kid-friendly answer with inline citation markers

### 5. Post-processing

- Normalize citations: `[1, 3, 5]` -> `[1] [3] [5]`
- Generate per-source summaries via Gemini 2.5 Flash (30-50 words each)

### 6. UI Rendering (app.py)

- `format_summary_with_citation_links()`: Converts `[1]` to clickable `<a class="cite">` badges
- `build_summary_html()`: Embeds source images inline between paragraphs
- `render_source_card_html()`: Builds source cards with image, title, domain, description
- Session history stored in `st.session_state` (max 20 entries, sidebar display)

## Whitelisted Sites (15)

| Category | Sites |
|----------|-------|
| **Search** | Kiddle, KidzSearch, SweetSearch |
| **News** | TIME for Kids, DOGOnews, TweenTribune, Newsela, Youngzine, Science News Explores, News for Kids, Teaching Kids News |
| **Research** | Ducksters, National Geographic Kids, Britannica School, Wonderopolis |

## External Services

| Service | Usage | Auth |
|---------|-------|------|
| DuckDuckGo | Web search with `site:` filters | None (free) |
| Gemini 2.5 Pro | Kid-friendly summarization | `GEMINI_API_KEY` |
| Gemini 2.5 Flash | Per-source summary generation | `GEMINI_API_KEY` |

## Safety Guarantees

1. **Search-level whitelisting**: DuckDuckGo `site:` operator restricts results at the search engine level
2. **Domain post-filter**: `_is_whitelisted()` catches any `site:` operator leaks
3. **Context-only AI**: Gemini has no web search tools - can only use provided article text
4. **System prompt constraints**: 4th-grade language, source-only answers, mandatory citations
5. **Optional password gate**: `APP_PASSWORD` in env/secrets

## Deployment

### Streamlit Cloud (production)
- GitHub repo: `nj-1015/kids-safe-search`
- Auto-deploys on push to `main`
- Secrets configured in Streamlit Cloud dashboard

### Local
```bash
pip install -r requirements.txt
echo "GEMINI_API_KEY=..." > .env
streamlit run app.py
```

### Docker
```bash
docker build -t kidsearch .
docker run -p 8080:8080 -e GEMINI_API_KEY=... kidsearch
```

## Performance

| Step | Typical Duration |
|------|-----------------|
| DuckDuckGo search (2 phases) | 1-2s |
| Content extraction (10 parallel) | 3-5s |
| Gemini Pro summarization | 2-4s |
| Gemini Flash source summaries | 1-2s |
| **Total** | **7-12 seconds** |

## Adding a New Site

1. Add entry to `whitelist.json`:
   ```json
   {
     "name": "Site Name",
     "domain": "example.com",
     "url": "https://example.com",
     "category": "news",
     "description": "Brief description"
   }
   ```
2. No code changes needed - domain list loaded dynamically from `config.load_whitelist()`
3. Push to GitHub -> auto-redeploy
