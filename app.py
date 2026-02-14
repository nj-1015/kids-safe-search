import os
import re

import streamlit as st

from services.gemini_summarizer import search_and_summarize

# --- Page config ---
st.set_page_config(
    page_title="KidSearch - Safe Search for Kids",
    page_icon="🔍",
    layout="centered",
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
</style>
""", unsafe_allow_html=True)


def format_summary_with_citation_links(summary: str, sources: list[dict]) -> str:
    """Convert [1] [2] citations into clickable links."""
    def replace_cite(match):
        num = int(match.group(1))
        if 1 <= num <= len(sources):
            url = sources[num - 1].get("resolved_url") or sources[num - 1]["url"]
            return f'<a class="cite" href="{url}" target="_blank">{num}</a>'
        return match.group(0)

    return re.sub(r'\[(\d+)\]', replace_cite, summary)


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


# --- Header ---
st.markdown("""
<div class="hero">
    <div class="hero-title">KidSearch</div>
    <div class="hero-sub">Ask me anything — I only search safe sites!</div>
    <div class="hero-badges">
        <span class="hero-badge">National Geographic Kids</span>
        <span class="hero-badge">Wonderopolis</span>
        <span class="hero-badge">TIME for Kids</span>
        <span class="hero-badge">Ducksters</span>
        <span class="hero-badge">Newsela</span>
        <span class="hero-badge">+ 8 more</span>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Search form ---
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
            sources = result["sources"]

            # Answer section
            st.markdown("""
            <div class="section-header">
                <span class="icon">📖</span>
                <span class="label">Answer</span>
                <span class="line"></span>
            </div>
            """, unsafe_allow_html=True)

            summary_html = build_summary_html(result["summary"], sources)
            st.markdown(
                f'<div class="summary-card">{summary_html}</div>',
                unsafe_allow_html=True,
            )

            # Source articles
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

        except Exception as e:
            st.error(f"Oops! Something went wrong. Please try again! ({e})")

elif search_clicked:
    st.warning("Please type a question first!")

# --- Footer ---
st.markdown("""
<div class="footer">
    <span class="shield">🛡️ Safe & Kid-Friendly</span>
    <p style="margin-top:8px;">Only searching trusted educational websites</p>
</div>
""", unsafe_allow_html=True)
