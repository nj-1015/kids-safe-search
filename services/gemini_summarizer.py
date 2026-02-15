import re
from concurrent.futures import ThreadPoolExecutor

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from services.content_extractor import extract_metadata

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


MODEL_NAME = "gemini-2.5-pro"

SYSTEM_PROMPT = """\
You are a friendly teacher who explains things to kids.

Rules:
- Use simple words that a 4th grader can understand
- Keep your answer between 200-300 words
- Use examples and comparisons to explain hard ideas
- Be encouraging and enthusiastic
- Use search results to answer accurately — do NOT make up information
- Cite your sources using [1], [2], etc. at the end of each sentence that uses information from that source
- Try to use as many sources as possible — aim for at least 3 different sources
- Stay focused on exactly what the user asked. Do NOT go on tangents about unrelated topics
- If you can't find enough information, say so honestly\
"""


def search_and_summarize(query: str) -> dict:
    """Search via Gemini Google Search grounding and return a kid-friendly summary."""

    # Step 1: Call Gemini with Google Search grounding
    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=16384,
        ),
    )

    summary = response.text or ""

    if not summary:
        return {
            "summary": "I couldn't find any information about that. "
                       "Try asking your question in a different way!",
            "sources": [],
        }

    # Step 2: Extract sources from grounding metadata
    sources = []
    candidate = response.candidates[0] if response.candidates else None
    grounding = getattr(candidate, "grounding_metadata", None) if candidate else None

    if grounding and grounding.grounding_chunks:
        seen_urls = set()
        for chunk in grounding.grounding_chunks:
            if chunk.web and chunk.web.uri:
                url = chunk.web.uri
                if url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({
                        "title": chunk.web.title or "",
                        "url": url,
                        "resolved_url": url,
                        "image_url": "",
                        "description": "",
                    })

    # Step 3: Normalize citations — convert [1, 3, 5] to [1] [3] [5]
    def _expand_citations(m):
        nums = re.findall(r'\d+', m.group(1))
        return " ".join(f"[{n}]" for n in nums)

    summary = re.sub(r'\[([\d,\s]+)\]', _expand_citations, summary)

    # Step 4: Keep only sources actually cited in the answer, renumber
    cited_nums = set(int(n) for n in re.findall(r'\[(\d+)\]', summary))
    if cited_nums:
        cited_sources = [s for i, s in enumerate(sources, 1) if i in cited_nums]
        old_to_new = {}
        new_idx = 1
        for old_idx in sorted(cited_nums):
            if old_idx <= len(sources):
                old_to_new[old_idx] = new_idx
                new_idx += 1
        summary = re.sub(
            r'\[(\d+)\]',
            lambda m: f'[{old_to_new[int(m.group(1))]}]' if int(m.group(1)) in old_to_new else m.group(0),
            summary,
        )
        sources = cited_sources

    # Step 5: Fetch images for source cards (parallel)
    if sources:
        with ThreadPoolExecutor(max_workers=5) as pool:
            metadata_list = list(pool.map(
                lambda s: extract_metadata(s["url"]), sources
            ))
        for src, meta in zip(sources, metadata_list):
            src["image_url"] = meta.get("image_url", "")
            src["resolved_url"] = meta.get("resolved_url", src["url"])

    # Step 6: Generate per-source summaries
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
            config=types.GenerateContentConfig(
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
