# NetGuard AI — Predictive Network Intelligence Platform

A production-ready network failure prediction system that monitors 500 telecom devices using **Markov Chain analysis** and **Monte Carlo simulation**, with **GPT-4o-mini AI chat** for natural language insights.

## What it does

- Predicts device failures up to **24 hours in advance** with 99.8% model accuracy
- Shows each device's exact failure probability at 1h / 6h / 24h / 7-day horizons
- Flags devices that look healthy to the human eye but are statistically at high risk
- Lets you **upload your own telemetry CSV** to run a fresh Markov analysis on your data
- Includes an **AI assistant** that answers questions about the network in plain English

## Dataset

| Metric | Value |
|---|---|
| Network elements | 500 (RAN, OPTICAL, EDGE, CORE) |
| Telemetry records | 168,000 (hourly, Aug 1–14 2025) |
| Failure events | 4,284 |
| Regions | North, South, East, West, Central |
| Model accuracy | 99.8% (Markov vs Monte Carlo cross-validated) |

## Quick start

```bash
# 1. Clone and enter the directory
cd health_device

# 2. Create a virtual environment
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Azure OpenAI credentials
cp .env.example .env   # then edit .env with your keys

# 5. Start the server
uvicorn server:app --host 0.0.0.0 --port 3721 --reload

# 6. Open the dashboard
# http://localhost:3721
```

> **No AI key?** The dashboard and all analytics endpoints work without Azure OpenAI.  
> Only the `/api/ai/chat` endpoint (chat widget) requires a valid key.

## Architecture

```
dashboard.html   ←→   server.py (FastAPI, port 3721)
                            │
                 ┌──────────┼──────────────┐
                 │          │              │
          CSV files      Azure OpenAI   Math helpers
       (pre-computed)   (GPT-4o-mini)  (NumPy Markov)
```

**Request flow for pre-computed data:**  
`GET /api/*` → read in-memory DataFrame → return JSON → Chart.js renders

**Request flow for interactive features:**  
`POST /api/analyze/custom-matrix` → validate → NumPy matrix math → return curves + MTTF  
`POST /api/upload/telemetry` → parse CSV → MLE transition estimation → full analysis  
`POST /api/ai/chat` → inject live network context → Azure OpenAI → return reply

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Dashboard HTML |
| GET | `/api/summary` | Risk & state distribution, avg MTTF, by-type & by-region |
| GET | `/api/elements` | Paginated element table (filter, sort, search) |
| GET | `/api/transition-matrix` | 5×5 Markov hourly transition matrix |
| GET | `/api/kpi-correlation` | KPI Pearson correlation matrix (6×6) |
| GET | `/api/failure-curves` | 168h cumulative failure curves per starting state |
| GET | `/api/mttf-breakdown` | MTTF by device type and region |
| GET | `/api/monte-carlo` | Markov vs Monte Carlo cross-validation |
| GET | `/api/business-impact` | Reactive vs predictive maintenance ROI |
| GET | `/api/priority-actions` | Top 10 highest-risk pre-failure devices |
| GET | `/api/sample-csv` | Download sample telemetry CSV template |
| POST | `/api/ai/chat` | LLM chat with live network context |
| POST | `/api/analyze/custom-matrix` | What-if analysis on a custom transition matrix |
| POST | `/api/upload/telemetry` | Upload telemetry CSV → estimate matrix → full analysis |

Interactive API docs: `http://localhost:3721/docs`

## Telemetry CSV format

Upload your own device state history to train a Markov model on your data:

```csv
element_id,state
NE001,Healthy
NE001,Warning
NE001,Minor
NE001,Failure
NE002,Healthy
NE002,Healthy
NE002,Warning
```

- `state` — required. One of: `Healthy`, `Warning`, `Minor`, `Major`, `Failure`
- `element_id` — optional. If present, transitions are computed *within* each device (so NE001→NE002 is not counted as a transition)

Minimum: ~50 rows for a meaningful matrix estimate.

## Custom Matrix API

POST your own 5×5 transition matrix to run instant what-if analysis:

```json
POST /api/analyze/custom-matrix
{
  "states": ["Healthy", "Warning", "Minor", "Major", "Failure"],
  "matrix": [
    [0.90, 0.06, 0.02, 0.01, 0.01],
    [0.20, 0.62, 0.12, 0.04, 0.02],
    [0.06, 0.25, 0.53, 0.12, 0.04],
    [0.02, 0.07, 0.24, 0.51, 0.16],
    [0.00, 0.00, 0.00, 0.00, 1.00]
  ]
}
```

Returns: failure probability curves over 168h + MTTF per state.

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
AZURE_API_KEY=your-key-here
AZURE_API_BASE=https://your-resource.openai.azure.com/
AZURE_API_VERSION=2024-10-21
AZURE_DEPLOYMENT_NAME=gpt-4o-mini
```

## Tech stack

- **Backend**: FastAPI + Uvicorn, Python 3.11+
- **Math**: NumPy (Markov chain, fundamental matrix, MLE estimation)
- **Data**: Pandas (CSV loading, filtering, groupby)
- **AI**: Azure OpenAI GPT-4o-mini (chat endpoint)
- **Frontend**: Vanilla JS + Chart.js 4 (no framework, single HTML file)
- **Charts**: Chart.js doughnut, line, bar; custom HTML heatmaps
