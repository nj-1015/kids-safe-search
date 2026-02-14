# KidSearch - Safe Search for Kids

A kid-friendly search engine that only searches parent-approved educational websites. Uses a RAG (Retrieval-Augmented Generation) pipeline with DuckDuckGo for search and Gemini AI for kid-friendly summaries.

**Live app**: Deployed on Streamlit Cloud with password protection.

## How It Works

1. Kid types a question (e.g., "Why is the sky blue?")
2. DuckDuckGo searches only whitelisted educational sites using `site:` filters
3. Article content is extracted from top results using BeautifulSoup
4. Articles are scored by relevance and the top 5 are selected
5. Gemini AI summarizes the content in simple, kid-friendly language with citations
6. Response shows an illustrated answer with clickable source cards

## Features

- **Whitelisted-only search** - Only searches 13 parent-approved educational sites
- **Two-phase search** - Combined search first, then per-domain search if more articles are needed
- **Relevance scoring** - Filters out off-topic results before sending to Gemini
- **Inline citations** - Clickable numbered badges linked to source articles
- **Source cards** - Each source shows title, domain, image, and a summary of what it contributed
- **Password protection** - Only accessible to kids who know the password
- **PWA support** - Installable as an app on Chromebook via Chrome
- **Mobile-friendly** - Designed with readable dark text and kid-friendly UI

## Whitelisted Sites

| Site | Category | Description |
|------|----------|-------------|
| Kiddle | Search | Google Safe Search powered, editor-curated |
| KidzSearch | Search | Strict filtering, 200K+ kid-friendly articles |
| SweetSearch | Search | Index vetted by librarians and teachers |
| TIME for Kids | News | Grade-level news stories |
| DOGOnews | News | Kids' news with vocabulary building |
| Smithsonian TweenTribune | News | Adjustable Lexile reading levels |
| Newsela | News | Current events at adjustable reading levels |
| Youngzine | News | News and current events for kids |
| Science News Explores | News | Science news written for students |
| Ducksters | Research | Bite-sized history, geography, science |
| National Geographic Kids | Research | Visual science and nature content |
| Britannica School | Research | Toggle Elementary/Middle levels |
| Wonderopolis | Research | Daily inquiry-based learning |

## Setup

### Prerequisites

- Python 3.11+
- Gemini API key ([Get one here](https://aistudio.google.com/apikey))

### Local Development

```bash
# Clone the repo
git clone https://github.com/nj-1015/kids-safe-search.git
cd kids-safe-search

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add: GEMINI_API_KEY=your_key_here

# Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `APP_PASSWORD` | No | Password to protect the app (leave empty for no password) |

## Deployment (Streamlit Cloud)

1. Push code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, select `app.py`
4. Add secrets in **Settings > Secrets**:
   ```toml
   GEMINI_API_KEY = "your_key"
   APP_PASSWORD = "your_password"
   ```
5. Deploy

## Architecture

```
User Question
      |
      v
DuckDuckGo Search (site: filters for 13 whitelisted domains)
      |
      v  (up to 20 results, per-domain fallback if needed)
Content Extraction (httpx + BeautifulSoup, parallel)
      |
      v  (score by keyword relevance, keep top 5)
Gemini 2.5 Pro (kid-friendly summary with [1] [2] citations)
      |
      v  (normalize citations, filter uncited sources)
Gemini 2.5 Flash (generate per-source summaries)
      |
      v
Streamlit UI (answer card + source cards)
```

## Project Structure

```
kids-safe-search/
├── app.py                          # Streamlit UI + CSS
├── config.py                       # API key and whitelist loader
├── whitelist.json                  # 13 safe educational sites
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variable template
├── .streamlit/
│   └── config.toml                 # Streamlit server config
├── services/
│   ├── web_searcher.py             # DuckDuckGo site-restricted search
│   ├── content_extractor.py        # Article text + metadata extraction
│   └── gemini_summarizer.py        # RAG pipeline orchestration
├── static/
│   ├── manifest.json               # PWA manifest
│   └── sw.js                       # Service worker
├── Dockerfile                      # For Docker/Cloud Run deployment
└── .dockerignore
```

## Tech Stack

- **UI**: Streamlit
- **Search**: DuckDuckGo (`ddgs` library) with `site:` operator
- **Content extraction**: httpx + BeautifulSoup4
- **AI**: Google Gemini 2.5 Pro (summary) + Gemini 2.5 Flash (source descriptions)
- **Deployment**: Streamlit Cloud (or Docker for self-hosting)
