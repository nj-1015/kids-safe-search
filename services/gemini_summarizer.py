import re
from concurrent.futures import ThreadPoolExecutor

from google import genai

from config import GEMINI_API_KEY, load_whitelist
from services.content_extractor import extract_article_text
from services.web_searcher import search_whitelisted

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
- You MUST cite EVERY source at least once. Pull at least one fact or detail from each source provided
- Spread citations across all sources to give a well-rounded answer
- If the sources don't have enough information to answer the question, say so honestly\
"""


def search_and_summarize(query: str) -> dict:
    """Search whitelisted sites and return a kid-friendly summary with sources."""

    # Step 1: Search whitelisted sites via DuckDuckGo
    search_results = search_whitelisted(query, WHITELISTED_DOMAINS, max_results=5)

    if not search_results:
        return {
            "summary": "I couldn't find any information about that on our safe websites. "
                       "Try asking your question in a different way!",
            "sources": [],
        }

    # Step 2: Fetch and extract content from each result in parallel
    with ThreadPoolExecutor(max_workers=5) as pool:
        articles = list(pool.map(
            lambda r: extract_article_text(r["url"]), search_results
        ))

    # Merge search result info with extracted content
    sources = []
    context_parts = []
    for i, (result, article) in enumerate(zip(search_results, articles), 1):
        title = article.get("title") or result["title"]
        url = article.get("resolved_url") or result["url"]
        text = article.get("text", "")
        snippet = result.get("snippet", "")

        # Use article text if available, otherwise fall back to search snippet
        content = text if len(text) > 50 else snippet

        if not content:
            continue

        sources.append({
            "title": title,
            "url": result["url"],
            "resolved_url": url,
            "image_url": article.get("image_url", ""),
            "description": "",
        })

        context_parts.append(
            f"[{len(sources)}] {title} ({url})\n{content}"
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
            temperature=0.7,
            max_output_tokens=16384,
        ),
    )

    summary = response.text or ""

    # Step 4: Keep only sources actually cited in the answer, renumber
    cited_nums = set(int(n) for n in re.findall(r'\[(\d+)\]', summary))
    if cited_nums:
        cited_sources = [s for i, s in enumerate(sources, 1) if i in cited_nums]
        # Renumber citations in summary to be sequential
        old_to_new = {}
        new_idx = 1
        for old_idx in sorted(cited_nums):
            old_to_new[old_idx] = new_idx
            new_idx += 1
        summary = re.sub(
            r'\[(\d+)\]',
            lambda m: f'[{old_to_new[int(m.group(1))]}]' if int(m.group(1)) in old_to_new else m.group(0),
            summary,
        )
        sources = cited_sources

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
