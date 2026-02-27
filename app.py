import os
import re
from datetime import datetime

import streamlit as st

from config import load_whitelist
from services.gemini_summarizer import search_and_summarize

# --- Page config ---
st.set_page_config(
    page_title="KidSearch - Safe Search for Kids",
    page_icon="🔍",
    layout="wide",
)

# --- PWA support (installable on Chromebook) ---
st.markdown("""
<link rel="manifest" href="app/static/manifest.json">
<meta name="theme-color" content="#4A90D9">
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('app/static/sw.js').catch(() => {});
}
</script>
""", unsafe_allow_html=True)

# --- Password gate ---
try:
    APP_PASSWORD = st.secrets.get("APP_PASSWORD", "") or os.environ.get("APP_PASSWORD", "")
except Exception:
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

if APP_PASSWORD:
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.markdown(
            "<h1 style='text-align:center; font-size:3rem;'>🔒</h1>"
            "<h2 style='text-align:center; color:#4A90D9;'>Enter the secret password</h2>",
            unsafe_allow_html=True,
        )
        pwd = st.text_input("Password", type="password", label_visibility="collapsed",
                            placeholder="Type the secret password...")
        if st.button("Enter"):
            if pwd == APP_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("That's not the right password! Ask your parent.")
        st.stop()

# --- Session state for search history ---
if "search_history" not in st.session_state:
    st.session_state.search_history = []
if "active_result" not in st.session_state:
    st.session_state.active_result = None

# --- CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Nunito', sans-serif;
    }

    .stApp {
        background: linear-gradient(180deg, #E8F4FD 0%, #FFF8E7 30%, #FFF0F5 100%);
        min-height: 100vh;
    }

    /* ---- Header ---- */
    .hero {
        text-align: center;
        padding: 2rem 1rem 1rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #4A90D9, #7B68EE, #FF6B9D);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }

    .hero-sub {
        color: #555;
        font-size: 1.15rem;
        margin-top: 4px;
    }

    .hero-badges {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
    }

    .hero-badge {
        display: inline-block;
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85rem;
        color: #444;
    }

    /* ---- Search bar ---- */
    .stTextInput > div > div > input {
        font-size: 1.2rem !important;
        padding: 14px 20px !important;
        border-radius: 50px !important;
        border: 3px solid #C5DAEF !important;
        background: white !important;
        color: #222 !important;
        box-shadow: 0 4px 15px rgba(74, 144, 217, 0.1) !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #888 !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #4A90D9 !important;
        box-shadow: 0 4px 20px rgba(74, 144, 217, 0.25) !important;
    }

    .stButton > button {
        font-size: 1.2rem !important;
        font-weight: 700 !important;
        padding: 14px 32px !important;
        border-radius: 50px !important;
        background: linear-gradient(135deg, #FF8C42, #FF6B9D) !important;
        color: white !important;
        border: none !important;
        width: 100%;
        box-shadow: 0 4px 15px rgba(255, 140, 66, 0.3) !important;
        transition: all 0.3s ease !important;
        letter-spacing: 0.5px !important;
    }

    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 140, 66, 0.4) !important;
    }

    /* ---- Section headers ---- */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.5rem 0 1rem;
    }

    .section-header .icon {
        font-size: 1.6rem;
    }

    .section-header .label {
        font-size: 1.3rem;
        font-weight: 700;
        color: #333;
    }

    .section-header .line {
        flex: 1;
        height: 3px;
        background: linear-gradient(90deg, #4A90D9, transparent);
        border-radius: 2px;
    }

    /* ---- Answer card ---- */
    .summary-card {
        background: white;
        border-radius: 20px;
        padding: 28px 32px;
        border-left: 6px solid #4A90D9;
        box-shadow: 0 4px 20px rgba(0,0,0,0.06);
        font-size: 1.1rem;
        line-height: 1.9;
        color: #222;
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
    }

    .summary-card::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 150px;
        height: 150px;
        background: radial-gradient(circle, rgba(74,144,217,0.05) 0%, transparent 70%);
        pointer-events: none;
    }

    .summary-card .inline-img {
        float: right;
        max-width: 200px;
        margin: 0 0 16px 20px;
        border-radius: 14px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }

    .summary-card .cite {
        display: inline-block;
        background: linear-gradient(135deg, #4A90D9, #7B68EE);
        color: white;
        font-size: 0.7rem;
        font-weight: 700;
        border-radius: 6px;
        padding: 1px 7px;
        margin-left: 2px;
        text-decoration: none;
        vertical-align: super;
        transition: all 0.2s ease;
    }

    .summary-card .cite:hover {
        transform: scale(1.15);
        box-shadow: 0 2px 8px rgba(74,144,217,0.4);
    }

    /* ---- Source cards (HTML version) ---- */
    .source-card {
        background: white;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        display: flex;
        gap: 16px;
        align-items: flex-start;
        transition: all 0.2s ease;
        border: 2px solid transparent;
    }

    .source-card:hover {
        border-color: #4A90D9;
        box-shadow: 0 4px 20px rgba(74,144,217,0.15);
        transform: translateY(-2px);
    }

    .source-card .source-img {
        width: 90px;
        height: 90px;
        border-radius: 12px;
        object-fit: cover;
        flex-shrink: 0;
    }

    .source-card .source-body {
        flex: 1;
        min-width: 0;
    }

    .source-card .source-num {
        display: inline-block;
        background: linear-gradient(135deg, #4A90D9, #7B68EE);
        color: white;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 6px;
        padding: 2px 8px;
        margin-right: 6px;
    }

    .source-card .source-title {
        font-weight: 700;
        color: #333;
        text-decoration: none;
        font-size: 1rem;
    }

    .source-card .source-title:hover {
        color: #4A90D9;
    }

    .source-card .source-domain {
        color: #666;
        font-size: 0.8rem;
        margin-top: 2px;
    }

    .source-card .source-desc {
        color: #333;
        font-size: 0.92rem;
        margin-top: 6px;
        line-height: 1.5;
    }

    /* ---- Footer ---- */
    .footer {
        text-align: center;
        color: #777;
        font-size: 0.85rem;
        padding: 2rem 0 1rem;
        max-width: 800px;
        margin-left: auto;
        margin-right: auto;
    }

    /* ---- Spinner / alerts ---- */
    .stSpinner > div > span {
        color: #333 !important;
        font-size: 1.1rem !important;
    }

    .stAlert p, .stAlert span {
        color: #333 !important;
    }

    .footer .shield {
        display: inline-block;
        background: #E8F5E9;
        color: #4CAF50;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #E8F4FD 0%, #FFF8E7 100%);
        font-family: 'Nunito', sans-serif;
    }

    [data-testid="stSidebar"] .sidebar-title {
        font-size: 1.2rem;
        font-weight: 700;
        color: #333;
        padding: 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    [data-testid="stSidebar"] .history-item {
        background: white;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        border: 2px solid transparent;
        transition: all 0.2s ease;
        cursor: pointer;
    }

    [data-testid="stSidebar"] .history-item:hover {
        border-color: #4A90D9;
        box-shadow: 0 3px 12px rgba(74,144,217,0.15);
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] .history-query {
        font-weight: 600;
        color: #333;
        font-size: 0.92rem;
        line-height: 1.3;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    [data-testid="stSidebar"] .history-time {
        font-size: 0.75rem;
        color: #999;
        margin-top: 4px;
    }

    [data-testid="stSidebar"] .history-sources {
        font-size: 0.75rem;
        color: #4A90D9;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)


def format_summary_with_citation_links(summary: str, sources: list[dict]) -> str:
    """Convert [1], [2], and [1, 2, 3] citations into clickable badge links."""

    def _make_badge(num: int) -> str:
        if 1 <= num <= len(sources):
            url = sources[num - 1].get("resolved_url") or sources[num - 1]["url"]
            return f'<a class="cite" href="{url}" target="_blank">{num}</a>'
        return f"[{num}]"

    def replace_cite_group(match):
        inner = match.group(1)
        nums = re.findall(r'\d+', inner)
        return " ".join(_make_badge(int(n)) for n in nums)

    # Match [1], [1, 2], [1, 3, 5], etc.
    return re.sub(r'\[([\d,\s]+)\]', replace_cite_group, summary)


def build_summary_html(summary: str, sources: list[dict]) -> str:
    """Build summary HTML with images floated inline between paragraphs."""
    images = [
        s["image_url"] for s in sources
        if s.get("image_url") and "favicons" not in s["image_url"]
    ]

    formatted = format_summary_with_citation_links(summary, sources)

    # Split into paragraphs
    paragraphs = [p.strip() for p in formatted.split("\n") if p.strip()]

    html_parts = []
    img_idx = 0
    for i, para in enumerate(paragraphs):
        if i in (0, 2) and img_idx < len(images):
            html_parts.append(
                f'<img class="inline-img" src="{images[img_idx]}" alt="">'
            )
            img_idx += 1
        html_parts.append(f"<p>{para}</p>")

    return "".join(html_parts)


def render_source_card_html(idx: int, source: dict) -> str:
    """Build HTML for a source card."""
    url = source.get("resolved_url") or source["url"]
    title = source["title"]
    desc = source.get("description", "")
    img_url = source.get("image_url", "")

    # Extract domain for display
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.replace("www.", "")

    img_html = ""
    if img_url:
        img_html = f'<img class="source-img" src="{img_url}" alt="">'

    desc_html = ""
    if desc:
        desc_html = f'<div class="source-desc">{desc}</div>'

    return f"""
    <a href="{url}" target="_blank" style="text-decoration:none;">
    <div class="source-card">
        {img_html}
        <div class="source-body">
            <div>
                <span class="source-num">{idx}</span>
                <span class="source-title">{title}</span>
            </div>
            <div class="source-domain">{domain}</div>
            {desc_html}
        </div>
    </div>
    </a>
    """


# --- Sidebar: Search History ---
with st.sidebar:
    st.markdown('<div class="sidebar-title">&#128336; Search History</div>', unsafe_allow_html=True)

    if not st.session_state.search_history:
        st.caption("Your searches will appear here.")
    else:
        for i, entry in enumerate(reversed(st.session_state.search_history)):
            idx = len(st.session_state.search_history) - 1 - i
            num_sources = len(entry.get("sources", []))
            item_html = f"""
            <div class="history-item" id="hist-{idx}">
                <div class="history-query">{entry['query']}</div>
                <div class="history-time">{entry['timestamp']}</div>
                <div class="history-sources">{num_sources} source{'s' if num_sources != 1 else ''}</div>
            </div>
            """
            st.markdown(item_html, unsafe_allow_html=True)
            if st.button(f"View", key=f"hist_{idx}", use_container_width=True):
                st.session_state.active_result = entry
                st.rerun()

        st.divider()
        if st.button("Clear History", use_container_width=True):
            st.session_state.search_history = []
            st.session_state.active_result = None
            st.rerun()

# --- Header ---
_all_sites = load_whitelist()
_badges_html = "\n".join(
    f'        <span class="hero-badge">{s["name"]}</span>' for s in _all_sites
)
st.markdown(f"""
<div class="hero">
    <div class="hero-title">KidSearch</div>
    <div class="hero-sub">Ask me anything — I only search safe sites!</div>
    <div class="hero-badges">
{_badges_html}
    </div>
</div>
""", unsafe_allow_html=True)

# --- Search form (centered on wide layout) ---
_, _search_col, _ = st.columns([1, 2, 1])
with _search_col:
    query = st.text_input(
        "Your question",
        placeholder="e.g., Why is the sky blue? How do volcanoes work?",
        max_chars=200,
        label_visibility="collapsed",
    )
    search_clicked = st.button("Search!")

# --- Search logic ---
if search_clicked and query.strip():
    with st.spinner("Searching safe sites for you..."):
        try:
            result = search_and_summarize(query.strip())
            entry = {
                "query": query.strip(),
                "summary": result["summary"],
                "sources": result["sources"],
                "timestamp": datetime.now().strftime("%I:%M %p"),
            }
            # Save to history (limit to 20)
            st.session_state.search_history.append(entry)
            if len(st.session_state.search_history) > 20:
                st.session_state.search_history = st.session_state.search_history[-20:]
            st.session_state.active_result = entry
            st.rerun()
        except Exception as e:
            st.error(f"Oops! Something went wrong. Please try again! ({e})")

elif search_clicked:
    st.warning("Please type a question first!")

# --- Display active result (side-by-side on wide screens) ---
if st.session_state.active_result:
    active = st.session_state.active_result
    sources = active["sources"]

    col_answer, col_sources = st.columns([3, 2], gap="large")

    with col_answer:
        st.markdown("""
        <div class="section-header">
            <span class="icon">📖</span>
            <span class="label">Answer</span>
            <span class="line"></span>
        </div>
        """, unsafe_allow_html=True)

        summary_html = build_summary_html(active["summary"], sources)
        st.markdown(
            f'<div class="summary-card">{summary_html}</div>',
            unsafe_allow_html=True,
        )

    with col_sources:
        if sources:
            st.markdown("""
            <div class="section-header">
                <span class="icon">📚</span>
                <span class="label">Where I Found This</span>
                <span class="line"></span>
            </div>
            """, unsafe_allow_html=True)

            cards_html = "".join(
                render_source_card_html(i, src) for i, src in enumerate(sources, 1)
            )
            st.markdown(cards_html, unsafe_allow_html=True)

# --- Footer ---
st.markdown("""
<div class="footer">
    <span class="shield">🛡️ Safe & Kid-Friendly</span>
    <p style="margin-top:8px;">Only searching trusted educational websites</p>
</div>
""", unsafe_allow_html=True)
