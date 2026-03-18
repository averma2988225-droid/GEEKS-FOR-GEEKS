# QueryViz

Conversational AI for Instant Business Intelligence Dashboards. Ask questions in natural language → get SQL + interactive chart visualizations.

## Tech Stack

- **Backend:** Python · FastAPI · SQLite · Google Gemini 2.5 Flash
- **Frontend:** Next.js 15 · React 19 · TypeScript · Recharts

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Gemini API key](https://aistudio.google.com/apikey)

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Open

Navigate to **http://localhost:3000**

Or use the one-click launcher: `start.bat` (Windows)

## Features

- **Natural Language → SQL** — Gemini-powered query conversion
- **Auto-Visualization** — Bar, line, pie, scatter, histogram, KPI charts
- **Conversational Context** — Follow-up queries refine previous results
- **CSV Upload** — Bring your own data
- **Smart Clarification** — Asks for details on vague queries
- **Auto-Insights** — Highlights key findings from results

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/query` | Natural language → SQL → results |
| `POST` | `/api/upload` | Upload CSV dataset |
| `GET` | `/api/datasets` | List uploaded datasets |
| `DELETE` | `/api/datasets/:id` | Delete a dataset |
| `GET` | `/health` | Health check |

## Example Queries

```
"What is the average age by gender?"
"Show income distribution by city tier"
"Count customers by shopping preference"
"now only for females"  ← follow-up
"top 5 results"         ← follow-up
```

## Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI entry point
│   ├── llm_engine.py           # Gemini LLM integration
│   ├── database.py             # SQLite management
│   ├── schema_info.py          # DB schema metadata
│   ├── csv_handler.py          # CSV upload handling
│   ├── conversation_manager.py # Chat context
│   ├── insight_generator.py    # Auto-insights
│   ├── requirements.txt
│   ├── .env.example
│   └── data/
│       └── dataset.csv
├── frontend/
│   ├── app/
│   │   ├── page.tsx
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── components/
│   │       ├── Chart.tsx
│   │       ├── DataTable.tsx
│   │       └── FileUpload.tsx
│   ├── package.json
│   └── next.config.js
├── .gitignore
├── README.md
└── start.bat
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `NEXT_PUBLIC_API_URL` | ❌ | Backend URL (default: `http://localhost:8000`) |

## Deployment

1. Set `GEMINI_API_KEY` in your environment
2. Backend: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. Frontend: `npm run build && npm start` or deploy to Vercel
4. Set `NEXT_PUBLIC_API_URL` to your backend URL in production
