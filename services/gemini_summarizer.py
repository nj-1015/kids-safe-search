import re
from concurrent.futures import ThreadPoolExecutor

from google import genai

from config import GEMINI_API_KEY, load_whitelist
from services.content_extractor import extract_article_text
from services.web_searcher import search_per_domain, search_whitelisted

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

MODEL_NAME = "gemini-2.5-pro"

WHITELISTED_SITES = load_whitelist()
WHITELISTED_DOMAINS = [site["domain"] for site in WHITELISTED_SITES]

SYSTEM_PROMPT = """\
You are a friendly teacher who explains things to kids.

Rules:
- Use simple words that a 4th grader can understand
- Keep your answer between 200-300 words
- Use examples and comparisons to explain hard ideas
- Be encouraging and enthusiastic
- Answer ONLY based on the provided sources below — do NOT make up information
- Cite your sources using [1], [2], etc. at the end of each sentence that uses information from that source
- You MUST cite EVERY source provided. Each source has useful information — find something relevant from each one and cite it
- Do NOT skip any source unless it is about a completely different topic with zero relevance
- Stay focused on exactly what the user asked. Do NOT go on tangents about unrelated topics
- If the question asks about a specific year but the sources are from different years, still share what the sources say — explain the topic using the available sources and note which years the information comes from
- If the sources don't have enough information to answer the question, say so honestly\
"""


def _fetch_candidates(search_results: list[dict], seen_urls: set) -> list[dict]:
    """Fetch article content and return candidates (skipping duplicates)."""
    new_results = [r for r in search_results if r["url"] not in seen_urls]
    if not new_results:
        return []

    with ThreadPoolExecutor(max_workers=10) as pool:
        articles = list(pool.map(
            lambda r: extract_article_text(r["url"]), new_results
        ))

    candidates = []
    for result, article in zip(new_results, articles):
        seen_urls.add(result["url"])
        title = article.get("title") or result["title"]
        url = article.get("resolved_url") or result["url"]
        text = article.get("text", "")
        snippet = result.get("snippet", "")

        content = text if len(text) > 50 else snippet
        if not content:
            continue

        candidates.append({
            "title": title,
            "url": result["url"],
            "resolved_url": url,
            "image_url": article.get("image_url", ""),
            "description": "",
            "content": content,
        })
    return candidates


def _rank_by_relevance(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    """Use Gemini to pick the most relevant articles for the query."""
    if len(candidates) <= top_n:
        return candidates

    article_list = []
    for i, c in enumerate(candidates):
        preview = c["content"][:800].replace("\n", " ")
        article_list.append(f"[{i+1}] {c['title']}\n{preview}")
    articles_text = "\n\n".join(article_list)

    prompt = f"""\
User's question: "{query}"

Below are {len(candidates)} articles. Select up to {top_n} articles that actually discuss the topic the user is asking about.

IMPORTANT:
- Only select articles that are genuinely about the topic, not ones that merely share a word
- For example, "shooting hoops" (basketball) is NOT relevant to "school shooting"
- Return between 1 and {top_n} numbers, one per line, most relevant first
- Do NOT include irrelevant filler articles just to reach {top_n}
- Output ONLY numbers, no text

Articles:
{articles_text}"""

    try:
        resp = _get_client().models.generate_content(
            model="gemini-3.1-pro-preview",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=256,
            ),
        )
        text = resp.text or ""
        picked = []
        for line in text.strip().split("\n"):
            nums = re.findall(r'\d+', line)
            if nums:
                idx = int(nums[0]) - 1
                if 0 <= idx < len(candidates) and idx not in [p for p, _ in picked]:
                    picked.append((idx, candidates[idx]))
            if len(picked) >= top_n:
                break
        if picked:
            return [c for _, c in picked]
    except Exception:
        pass

    # Fallback: return first top_n candidates (search engine order)
    return candidates[:top_n]


def search_and_summarize(query: str) -> dict:
    """Search whitelisted sites and return a kid-friendly summary with sources."""
    seen_urls: set = set()

    # Phase 1: Combined search across all whitelisted domains
    search_results = search_whitelisted(query, WHITELISTED_DOMAINS, max_results=20)
    candidates = _fetch_candidates(search_results, seen_urls)

    # Phase 2: Always search each domain individually for more candidates
    per_domain_results = search_per_domain(query, WHITELISTED_DOMAINS, results_per_domain=3)
    extra = _fetch_candidates(per_domain_results, seen_urls)
    candidates.extend(extra)

    if not candidates:
        return {
            "summary": "I couldn't find any information about that on our safe websites. "
                       "Try asking your question in a different way!",
            "sources": [],
        }

    # Use Gemini to pick the most relevant articles
    good = _rank_by_relevance(query, candidates)

    sources = []
    context_parts = []
    for c in good:
        sources.append({
            "title": c["title"],
            "url": c["url"],
            "resolved_url": c["resolved_url"],
            "image_url": c["image_url"],
            "description": "",
        })
        context_parts.append(
            f"[{len(sources)}] {c['title']} ({c['resolved_url']})\n{c['content']}"
        )

    if not sources:
        return {
            "summary": "I found some pages but couldn't read them properly. "
                       "Try asking your question in a different way!",
            "sources": [],
        }

    # Step 3: Build context and call Gemini (no web search — context only)
    context = "\n\n---\n\n".join(context_parts)

    prompt = f"""Question: {query}

Sources:
{context}

Using ONLY the sources above, write a kid-friendly answer. Cite sources with [1], [2], etc."""

    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=16384,
        ),
    )

    summary = response.text or ""

    # Step 4: Normalize citations — convert [1, 3, 5] to [1] [3] [5]
    def _expand_citations(m):
        nums = re.findall(r'\d+', m.group(1))
        return " ".join(f"[{n}]" for n in nums)

    summary = re.sub(r'\[([\d,\s]+)\]', _expand_citations, summary)

    # Step 5: Normalize citations (keep all sources — don't filter uncited ones)
    # Sources are already numbered [1]-[5] matching the context, no renumbering needed

    # Step 5: Generate per-source summaries
    _generate_source_summaries(summary, sources)

    return {"summary": summary, "sources": sources}


def _generate_source_summaries(answer: str, sources: list[dict]):
    """Use Gemini to generate a kid-friendly summary for each source."""
    if not sources:
        return

    source_list = "\n".join(
        f"[{i+1}] {s['title']} ({s.get('resolved_url', s['url'])})"
        for i, s in enumerate(sources)
    )

    prompt = f"""\
Based on this answer about a kid's question:

\"\"\"{answer}\"\"\"

These are the sources used. Write a 2-3 sentence summary (30-50 words) for EACH source explaining what key facts it provided for the answer. Be specific — mention actual facts, numbers, or details from the answer that came from each source. You MUST provide a summary for every single source listed. Return ONLY the summaries, one per line, in this exact format:
[1] summary text
[2] summary text

Sources:
{source_list}"""

    try:
        resp = _get_client().models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=8192,
            ),
        )
        text = resp.text or ""

        for line in text.strip().split("\n"):
            match = re.match(r'\[(\d+)\]\s*(.+)', line.strip())
            if match:
                idx = int(match.group(1)) - 1
                desc = match.group(2).strip()
                if 0 <= idx < len(sources):
                    sources[idx]["description"] = desc
    except Exception:
        for src in sources:
            if not src.get("description"):
                src["description"] = src.get("title", "Source article")
