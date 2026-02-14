# KidSearch - Safe Search for Kids

A whitelist RAG (Retrieval-Augmented Generation) search agent that only searches parent-approved safe websites and summarizes results in kid-friendly language using Gemini AI.

## How It Works

1. Kid asks a question (e.g., "Why is the sky blue?")
2. System searches only whitelisted educational sites via Google Custom Search
3. Article content is extracted from top results
4. Gemini AI summarizes the content in kid-friendly language
5. Response shows the summary + source articles with links

## Whitelisted Sites

| Site | Category |
|------|----------|
| Kiddle | Search |
| KidzSearch | Search |
| SweetSearch | Search |
| TIME for Kids | News |
| DOGOnews | News |
| Smithsonian TweenTribune | News |
| Ducksters | Research |
| National Geographic Kids | Research |
| Britannica School | Research |
| Wonderopolis | Research |

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud account
- Gemini API key

### 1. Google Programmable Search Engine Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "kids-search-agent")
3. Navigate to **APIs & Services > Library**
4. Search for **"Custom Search API"** and enable it
5. Go to **APIs & Services > Credentials**
6. Click **Create Credentials > API key**
7. Copy the API key (this is your `GOOGLE_CSE_API_KEY`)

Then create the search engine:

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/controlpanel/create)
2. Under **"Sites to search"**, add these domains:
   - `kiddle.co`
   - `kidzsearch.com`
   - `sweetsearch.com`
   - `timeforkids.com`
   - `dogonews.com`
   - `tweentribune.com`
   - `ducksters.com`
   - `kids.nationalgeographic.com`
   - `school.britannica.com`
   - `wonderopolis.org`
3. Set **"Search the entire web"** to **OFF**
4. Click **Create**
5. Copy the **Search Engine ID** (this is your `GOOGLE_CSE_ID`)

### 2. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Create .env from template
cp .env.example .env
# Edit .env and add your API keys
```

### 3. Frontend Setup

```bash
cd frontend
npm install
```

### 4. Run

Start both servers:

```bash
# Terminal 1 - Backend (from backend/)
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend (from frontend/)
npm run dev
```

Open http://localhost:3000 in your browser.

## Project Structure

```
kids_search_agent/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Settings loader
│   ├── whitelist.json        # Safe site list
│   ├── routers/search.py     # /api/search endpoint
│   └── services/
│       ├── google_search.py      # Google CSE integration
│       ├── content_extractor.py  # Article text extraction
│       └── gemini_summarizer.py  # Gemini kid-friendly summary
└── frontend/                 # Next.js React app
    └── app/
        ├── page.tsx          # Main search page
        └── components/       # UI components
```
