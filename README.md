# 🎓 PhD Professor Outreach Assistant

An AI agent pipeline that reads your resume, searches for professors whose research matches your background, scrapes their official faculty pages for contact details, ranks them by fit, and drafts personalized outreach emails — all through a Streamlit UI.

Built with **LangChain**, **LangGraph agents**, **Mistral AI**, and **Tavily Search**.

---

## ✨ Features

- **Resume parsing** — upload a PDF/DOCX/TXT resume; an LLM extracts your research interests, degree, skills, and publications into structured data.
- **Country-scoped professor search** — a Tavily-powered search agent finds current faculty at universities in your target country whose research matches your interests.
- **Faculty page scraping** — a scraping agent visits official `.edu`/university pages to pull each professor's name, email, and research focus.
- **Fit ranking** — an LLM scores and sorts every candidate professor against your profile (1–10 fit score with a one-line justification).
- **Personalized email drafts** — auto-generates a short, specific cold-outreach email per top match, referencing their actual research area.
- **Streamlit UI** — upload, run, and review results (profile summary, fit-scored professor cards, editable email drafts, JSON export) in the browser.

> ⚠️ This tool **drafts** emails only — nothing is sent automatically. Always review and personalize each draft before sending.

---

## 🏗️ Architecture

```
Resume upload + country
        │
        ▼
 1. Resume Parser Agent   →  research interests, degree, skills, publications (JSON)
        │
        ▼
 2. Professor Search Agent (Tavily)  →  candidate professors per research interest
        │
        ▼
 3. Scrape Agent (BeautifulSoup / trafilatura)  →  name, email, research area per faculty page
        │
        ▼
 4. Fit Ranker  →  scores + sorts professors against your profile
        │
        ▼
 5. Email Draft Agent  →  personalized outreach email per top match
        │
        ▼
   Streamlit UI  →  profile summary, ranked professor cards, editable drafts, JSON export
```

Two Mistral models are used to balance cost, speed, and quality:
- `mistral-small-latest` — search and scraping (tool-use, extraction)
- `mistral-large-latest` — resume parsing, fit ranking, and email drafting (reasoning-heavy)

---

## 📁 Project structure

```
.
├── src/
│   ├── agents/
│   │   └── agent.py          # search agent, scrape agent, resume/ranker/email chains
│   ├── tools/
│   │   ├── tools.py          # web_search (Tavily), scrape_web
│   │   └── resume_utils.py   # PDF/DOCX text extraction, email/URL regex helpers
│   └── pipelines/
│       └── pipeline.py       # orchestrates the 5-step pipeline, retry/backoff logic
├── streamlit_app.py           # Streamlit UI
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Clone and install dependencies

```bash
git clone <your-repo-url>
cd <your-repo-name>
pip install -r requirements.txt
```

### 2. Set environment variables

Create a `.env` file in the project root:

```env
TAVILY_API_KEY=your_tavily_api_key
MISTRAL_API_KEY=your_mistral_api_key
```

Get API keys from [Tavily](https://tavily.com) and [Mistral AI](https://console.mistral.ai).

> In production (e.g. Render, Railway, etc.), set these as environment variables in your hosting dashboard rather than relying on a `.env` file.

### 3. Run the app

```bash
streamlit run streamlit_app.py
```

Open the local URL Streamlit prints (usually `http://localhost:8501`).

---

## 🚀 Usage

1. Upload your resume (PDF, DOCX, or TXT).
2. Enter your target country (e.g. `USA`).
3. Click **Find professors**.
4. Review your extracted profile, browse ranked professor matches, and read/edit each generated email draft.
5. Download all results as JSON if needed.

---

## 🧰 Tech stack

| Layer | Tool |
|---|---|
| LLM | Mistral AI (`mistral-small-latest`, `mistral-large-latest`) |
| Agent framework | LangChain / LangGraph (`create_agent`) |
| Web search | Tavily API |
| Scraping | `requests`, `BeautifulSoup4`, `trafilatura`, `readability-lxml` |
| Resume parsing | `pypdf`, `python-docx` |
| UI | Streamlit |

---

## ⚠️ Known limitations

- LLM-based JSON extraction can occasionally fail to parse; the pipeline falls back gracefully but may return partial results.
- Scraped emails come from public faculty pages and are not guaranteed to be accurate or current — always verify before sending.
- API rate limits (especially on free-tier Mistral accounts) can slow down or interrupt runs; the pipeline includes automatic retry with backoff for `429` errors.
- Search results depend entirely on what Tavily indexes and are not exhaustive.

---

## 📄 License

MIT (or update this to match your project's actual license).

---

## 🙋 Disclaimer

This project is intended to help with research and drafting only. It is not a substitute for genuine, personalized outreach — always read, verify, and edit each email before sending it to a real professor.
