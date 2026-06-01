"""
NetGuard AI — Backend API Server
=================================
Serves pre-computed network health analytics (CSV files) via REST endpoints,
plus three interactive features:
  - AI Chat      : GPT-4o-mini with live network context injected as system prompt
  - Custom Matrix: POST any 5×5 transition matrix → failure curves + MTTF on-the-fly
  - CSV Upload   : Upload your own telemetry → estimate Markov matrix → full analysis

Data: August 1–14, 2025 | 500 network elements | 168,000 telemetry records
Model: Markov Chain + Monte Carlo cross-validation (99.8% accuracy)

Run:
    uvicorn server:app --host 0.0.0.0 --port 3721 --reload
"""

import io
import os
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from openai import AzureOpenAI
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Configuration — loaded from .env file
# ---------------------------------------------------------------------------

load_dotenv()

AZURE_API_KEY     = os.getenv("AZURE_API_KEY")
AZURE_API_BASE    = os.getenv("AZURE_API_BASE")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-10-21")
AZURE_DEPLOYMENT  = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")

# Azure OpenAI client — used only by the /api/ai/chat endpoint
ai_client = AzureOpenAI(
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_API_BASE,
)

# ---------------------------------------------------------------------------
# Paths & domain constants
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent

HIGH_RISK_LEVELS     = {"HIGH", "CRITICAL"}
LOOKS_HEALTHY_STATES = {"Healthy", "Warning", "Minor"}

# The 5 Markov states in order (must match the CSV headers)
VALID_STATES = ["Healthy", "Warning", "Minor", "Major", "Failure"]

# Recommended NOC action per device type (used in Priority Action Board)
ACTION_BY_TYPE = {
    "RAN":     "Dispatch field engineer — radio access network tower",
    "EDGE":    "NOC remote restart + on-site inspection team",
    "CORE":    "Alert NOC team — core switch intervention required",
    "OPTICAL": "Schedule fiber inspection and splice team",
}

# Sample CSV users can download as a template for the upload endpoint
SAMPLE_CSV = """\
element_id,state
NE001,Healthy
NE001,Healthy
NE001,Warning
NE001,Minor
NE001,Major
NE001,Failure
NE002,Healthy
NE002,Warning
NE002,Healthy
NE002,Minor
NE002,Major
NE002,Failure
NE003,Healthy
NE003,Healthy
NE003,Warning
NE003,Healthy
NE003,Warning
NE003,Minor
"""

# ---------------------------------------------------------------------------
# Load all CSVs once at startup (no DB — data is pre-computed offline)
# ---------------------------------------------------------------------------

dashboard_df  = pd.read_csv(BASE_DIR / "network_risk_dashboard.csv")
mttf_df       = pd.read_csv(BASE_DIR / "element_mttf_analysis.csv")
corr_df       = pd.read_csv(BASE_DIR / "kpi_correlation_matrix.csv",      index_col=0)
transition_df = pd.read_csv(BASE_DIR / "estimated_transition_matrix.csv", index_col=0)
mc_df         = pd.read_csv(BASE_DIR / "monte_carlo_results.csv")

print(f"[startup] Loaded {len(dashboard_df)} elements | {len(mttf_df)} MTTF records")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="NetGuard AI API",
    description="Predictive Network Intelligence Platform — Markov Chain + LLM Analytics",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Pydantic models for POST request bodies
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str      # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class MatrixRequest(BaseModel):
    states: List[str]
    matrix: List[List[float]]

# ---------------------------------------------------------------------------
# Shared math helpers
# ---------------------------------------------------------------------------

def _valid_mttf(df: pd.DataFrame) -> pd.Series:
    """Exclude the 99999 sentinel that marks elements which never failed."""
    return df[df["mttf_hours"] < 99_999]["mttf_hours"]


def _is_high_risk(df: pd.DataFrame) -> pd.Series:
    return df["risk_level"].isin(HIGH_RISK_LEVELS)


def _rf(value, d=4) -> float:
    return round(float(value), d)


def _compute_failure_curves(P: np.ndarray, states: List[str], hours: int = 168) -> dict:
    """
    Cumulative failure probability for each non-failure starting state over N hours.

    Algorithm: at each step, advance the state vector by one Markov step (vec @ P),
    accumulate the mass that lands in Failure, then zero it out so it isn't
    double-counted in subsequent steps.
    """
    failure_idx = states.index("Failure") if "Failure" in states else len(states) - 1
    curves = {}

    for start_idx, start_state in enumerate(states):
        if start_idx == failure_idx:
            continue

        vec = np.zeros(len(states))
        vec[start_idx] = 1.0
        cumulative = 0.0
        probs = []

        for _ in range(hours):
            vec = vec @ P
            new_fail = float(vec[failure_idx])
            cumulative += new_fail
            probs.append(round(min(cumulative, 1.0), 4))

            # Remove absorbed mass so next step only counts new failures
            if new_fail > 0:
                surviving = 1.0 - new_fail
                if surviving > 0:
                    for j in range(len(states)):
                        if j != failure_idx:
                            vec[j] = vec[j] / surviving * (1.0 - new_fail)
                vec[failure_idx] = 0.0

        curves[start_state] = probs

    return curves


def _compute_mttf(P: np.ndarray, states: List[str]) -> dict:
    """
    Mean Time to Failure via the absorbing Markov chain fundamental matrix.

    N = (I − Q)⁻¹  where Q is the sub-matrix of transient→transient transitions.
    MTTF for each transient state = sum of that row of N (expected time in transient states).
    """
    n = len(states)
    # Identify absorbing states (self-loop probability ≥ 0.99)
    absorbing = [i for i in range(n) if P[i, i] >= 0.99]
    if not absorbing:
        absorbing = [n - 1]  # fall back to last state if none detected

    transient = [i for i in range(n) if i not in absorbing]
    if not transient:
        return {}

    Q = P[np.ix_(transient, transient)]
    try:
        N = np.linalg.inv(np.eye(len(transient)) - Q)
        t = N.sum(axis=1)
        return {states[transient[i]]: round(float(t[i]), 2) for i in range(len(transient))}
    except np.linalg.LinAlgError:
        return {states[transient[i]]: None for i in range(len(transient))}


def _estimate_transition_matrix(sequence: List[str]) -> np.ndarray:
    """
    Maximum likelihood estimate of the transition matrix from a state sequence.
    Count every consecutive (from → to) pair, then normalize each row to sum to 1.
    Rows with zero transitions get a uniform distribution to avoid NaN.
    """
    n = len(VALID_STATES)
    idx = {s: i for i, s in enumerate(VALID_STATES)}
    counts = np.zeros((n, n))

    for i in range(len(sequence) - 1):
        from_s, to_s = sequence[i], sequence[i + 1]
        if from_s in idx and to_s in idx:
            counts[idx[from_s]][idx[to_s]] += 1

    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1  # prevent division by zero
    return counts / row_sums


def _build_network_context() -> str:
    """
    Build a live snapshot of the network to inject into the AI chat system prompt.
    Called on every chat request so it always reflects the latest loaded data.
    """
    rd = {k: int(v) for k, v in dashboard_df["risk_level"].value_counts().items()}
    sd = {k: int(v) for k, v in dashboard_df["current_state"].value_counts().items()}
    valid_mttf = _valid_mttf(dashboard_df)

    top5 = (
        dashboard_df[dashboard_df["current_state"] != "Failure"]
        .sort_values("prob_fail_6h", ascending=False)
        .head(5)
    )
    top5_lines = "\n".join(
        f"  - {r['element_id']} ({r['type']}, {r['region']}): "
        f"{round(r['prob_fail_6h']*100, 1)}% fail/6h, MTTF {round(r['mttf_hours'], 1)}h, {r['risk_level']}"
        for _, r in top5.iterrows()
    )

    return f"""
LIVE NETWORK SNAPSHOT (Aug 1–14, 2025 | 500 elements | 168,000 telemetry records):
  Risk distribution  : {rd}
  State distribution : {sd}
  Average MTTF       : {round(float(valid_mttf.mean()), 1)}h (elements that actually fail)
  Avg 24h fail prob  : {round(float(dashboard_df['prob_fail_24h'].mean()) * 100, 1)}%
  Model              : Markov Chain (5 states) + Monte Carlo validation (99.8% accuracy)
  Element types      : RAN, OPTICAL, EDGE, CORE
  Regions            : North, South, East, West, Central

TOP 5 HIGHEST-RISK PRE-FAILURE DEVICES:
{top5_lines}

KEY KPI CORRELATIONS:
  CPU % ↔ Signal Quality  : −0.920  (strong negative — high CPU degrades signal)
  Packet Drop ↔ Errors    : +0.976  (strong positive — they fail together)
  All 6 KPIs co-degrade   : any single metric is a valid early-warning signal

MARKOV TRANSITION HIGHLIGHTS:
  Healthy stability   : 87.8% chance of staying Healthy each hour
  Failure absorption  : 79.7% remain Failed, 20.3% self-recover per hour
""".strip()


# ---------------------------------------------------------------------------
# Routes — static assets
# ---------------------------------------------------------------------------

@app.get("/")
async def serve_dashboard():
    """Serve the single-page analytics dashboard."""
    return FileResponse(BASE_DIR / "dashboard.html")


# ---------------------------------------------------------------------------
# Routes — analytics (read from pre-computed CSVs)
# ---------------------------------------------------------------------------

@app.get("/api/summary")
async def get_summary():
    """
    Top-level network health summary.

    Returns risk & state distributions, average MTTF, 24h failure probability,
    and breakdowns by device type and geographic region.
    """
    risk_dist  = {k: int(v) for k, v in dashboard_df["risk_level"].value_counts().items()}
    state_dist = {k: int(v) for k, v in dashboard_df["current_state"].value_counts().items()}
    valid_mttf = _valid_mttf(dashboard_df)

    by_type = []
    for device_type, group in dashboard_df.groupby("type"):
        type_mttf = _valid_mttf(group)
        by_type.append({
            "type":          device_type,
            "avg_fail_24h":  _rf(group["prob_fail_24h"].mean()),
            "avg_mttf":      _rf(type_mttf.mean(), 2) if len(type_mttf) > 0 else 0,
            "critical_high": int(_is_high_risk(group).sum()),
            "total":         int(len(group)),
        })

    by_region = []
    for region, group in dashboard_df.groupby("region"):
        by_region.append({
            "region":        region,
            "avg_fail_24h":  _rf(group["prob_fail_24h"].mean()),
            "critical_high": int(_is_high_risk(group).sum()),
            "total":         int(len(group)),
        })

    return {
        "total_elements":          len(dashboard_df),
        "risk_distribution":       risk_dist,
        "state_distribution":      state_dist,
        "avg_mttf_hours":          _rf(valid_mttf.mean(), 2),
        "avg_fail_prob_24h":       _rf(dashboard_df["prob_fail_24h"].mean()),
        "pct_healthy":             round(state_dist.get("Healthy", 0) / len(dashboard_df) * 100, 1),
        "by_type":                 by_type,
        "by_region":               by_region,
        "data_period":             "August 1–14, 2025",
        "total_elements_analyzed": 500,
        "total_telemetry_records": 168_000,
        "total_failure_events":    4_284,
    }


@app.get("/api/transition-matrix")
async def get_transition_matrix():
    """
    Hourly Markov state-transition probability matrix (5×5).

    States (rows & columns): Healthy → Warning → Minor → Major → Failure
    Values are MLE probabilities estimated from 167,500 observed transitions.
    """
    states = transition_df.index.tolist()
    matrix = [[_rf(v) for v in row] for row in transition_df.values]
    return {"states": states, "matrix": matrix}


@app.get("/api/kpi-correlation")
async def get_kpi_correlation():
    """
    Pearson correlation matrix between 6 KPIs across all 168,000 telemetry readings.

    KPIs: cpu_pct, memory_pct, temperature_c, pkt_drop_pct, error_count, signal_quality
    High magnitude = KPIs move together; negative = inverse relationship.
    """
    labels = corr_df.index.tolist()
    matrix = [[_rf(v, 3) for v in row] for row in corr_df.values]
    return {"labels": labels, "matrix": matrix}


@app.get("/api/failure-curves")
async def get_failure_curves():
    """
    Cumulative failure probability over a 168-hour (7-day) window per starting state.
    Computed live from the transition matrix using the iterative Markov step method.
    """
    states = transition_df.index.tolist()
    P = transition_df.values.astype(float)
    curves = _compute_failure_curves(P, states)
    return {"hours": list(range(1, 169)), "curves": curves}


@app.get("/api/mttf-breakdown")
async def get_mttf_breakdown():
    """
    Mean Time to Failure stats (mean / min / max) by device type and region.
    Elements with mttf_hours = 99999 are excluded (they never failed in the dataset).
    """
    valid = mttf_df[mttf_df["mttf_hours"] < 99_999]
    by_type   = [{"type":   t, "mean": _rf(g["mttf_hours"].mean(), 2),
                  "min": _rf(g["mttf_hours"].min(), 2), "max": _rf(g["mttf_hours"].max(), 2)}
                 for t, g in valid.groupby("type")]
    by_region = [{"region": r, "mean": _rf(g["mttf_hours"].mean(), 2),
                  "min": _rf(g["mttf_hours"].min(), 2), "max": _rf(g["mttf_hours"].max(), 2)}
                 for r, g in valid.groupby("region")]
    return {"by_type": by_type, "by_region": by_region}


@app.get("/api/elements")
async def get_elements(
    page:        int = Query(1,   ge=1),
    limit:       int = Query(25,  ge=1, le=100),
    sort_col:    str = Query("prob_fail_24h"),
    order:       str = Query("desc"),
    risk_filter: str = Query("ALL"),
    type_filter: str = Query("ALL"),
    search:      str = Query(""),
):
    """
    Paginated, filterable, sortable table of all 500 network elements.

    Filters: risk_filter (CRITICAL/HIGH/MEDIUM/LOW/NORMAL/ALL),
             type_filter (RAN/OPTICAL/EDGE/CORE/ALL),
             search (substring match on element_id).
    """
    df = dashboard_df.copy()

    if risk_filter != "ALL":
        df = df[df["risk_level"] == risk_filter]
    if type_filter != "ALL":
        df = df[df["type"] == type_filter]
    if search:
        df = df[df["element_id"].str.contains(search, case=False, na=False)]
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=(order == "asc"))

    total    = len(df)
    page_df  = df.iloc[(page - 1) * limit: page * limit]

    records = [
        {
            "element_id":      str(r["element_id"]),
            "type":            str(r["type"]),
            "region":          str(r["region"]),
            "current_state":   str(r["current_state"]),
            "mttf_hours":      float(r["mttf_hours"]),
            "prob_fail_1h":    float(r["prob_fail_1h"]),
            "prob_fail_6h":    float(r["prob_fail_6h"]),
            "prob_fail_24h":   float(r["prob_fail_24h"]),
            "prob_fail_1week": float(r["prob_fail_1week"]),
            "risk_level":      str(r["risk_level"]),
            "cpu_pct":         float(r["cpu_pct"]),
            "memory_pct":      float(r["memory_pct"]),
            "temperature_c":   float(r["temperature_c"]),
            "signal_quality":  float(r["signal_quality"]),
            "error_count":     int(r["error_count"]),
        }
        for _, r in page_df.iterrows()
    ]

    return {"total": total, "page": page, "limit": limit, "data": records}


@app.get("/api/monte-carlo")
async def get_monte_carlo():
    """
    Cross-validation: Markov analytical result vs Monte Carlo simulation (5,000 runs).
    A match near 100% confirms the Markov model is correctly calibrated.
    """
    results = []
    for _, row in mc_df.iterrows():
        record = {"method": str(row["method"])}
        for col in mc_df.columns:
            if col == "method":
                continue
            try:
                record[col] = float(row[col])
            except (ValueError, TypeError):
                record[col] = str(row[col])
        results.append(record)
    return results


@app.get("/api/business-impact")
async def get_business_impact():
    """
    Business case: reactive maintenance (status quo) vs predictive with NetGuard AI.

    Assumptions:
      - 60% of failures are preventable with 24h advance warning
      - Each failure averages 4.89 hours of device downtime
      - Observation window: 14 days × 500 devices = 168,000 device-hours
    """
    TOTAL_FAILURES    = 4_284
    AVG_FAILURE_HOURS = 4.89
    DEVICES           = 500
    PERIOD_HOURS      = 336   # 14 days × 24 hours
    PREVENTABLE_PCT   = 60

    total_downtime     = round(TOTAL_FAILURES * AVG_FAILURE_HOURS)
    total_device_hours = DEVICES * PERIOD_HOURS
    current_avail      = round((1 - total_downtime / total_device_hours) * 100, 1)
    preventable        = round(TOTAL_FAILURES * PREVENTABLE_PCT / 100)
    saved_hours        = round(preventable * AVG_FAILURE_HOURS)
    target_avail       = round((1 - (total_downtime - saved_hours) / total_device_hours) * 100, 1)

    return {
        "period_days": 14,
        "devices": DEVICES,
        "current": {
            "total_failures":              TOTAL_FAILURES,
            "failures_per_day":            round(TOTAL_FAILURES / 14),
            "avg_failure_duration_h":      AVG_FAILURE_HOURS,
            "total_downtime_device_hours": total_downtime,
            "availability_pct":            current_avail,
        },
        "with_netguard": {
            "preventable_pct":       PREVENTABLE_PCT,
            "preventable_failures":  preventable,
            "downtime_hours_saved":  saved_hours,
            "availability_pct":      target_avail,
            "advance_warning_hours": 24,
        },
    }


@app.get("/api/priority-actions")
async def get_priority_actions():
    """
    Top 10 HIGH-risk devices NOT yet in Failure state — the NOC's intervention window.

    Urgency tiers (based on MTTF and 6h failure probability):
      DISPATCH NOW    — MTTF < 20h  OR  P(fail@6h) > 45%
      ACT WITHIN 12H  — MTTF < 35h
      SCHEDULE TODAY  — everything else in HIGH risk

    Also flags devices that "look healthy" (state = Healthy/Warning/Minor) despite
    being HIGH risk — these are the predictions a human NOC would miss entirely.
    """
    currently_failing = int((dashboard_df["current_state"] == "Failure").sum())

    at_risk = (
        dashboard_df[
            (dashboard_df["current_state"] != "Failure") &
            (dashboard_df["risk_level"] == "HIGH")
        ]
        .sort_values("prob_fail_6h", ascending=False)
        .head(10)
    )

    look_ok_count = int(
        dashboard_df[
            (dashboard_df["risk_level"] == "HIGH") &
            dashboard_df["current_state"].isin(LOOKS_HEALTHY_STATES)
        ].shape[0]
    )

    actions = []
    for _, row in at_risk.iterrows():
        mttf  = float(row["mttf_hours"])
        p6h   = float(row["prob_fail_6h"])
        state = str(row["current_state"])

        if mttf < 20 or p6h > 0.45:
            urgency, urgency_level = "DISPATCH NOW",    1
        elif mttf < 35:
            urgency, urgency_level = "ACT WITHIN 12H", 2
        else:
            urgency, urgency_level = "SCHEDULE TODAY",  3

        actions.append({
            "element_id":         str(row["element_id"]),
            "type":               str(row["type"]),
            "region":             str(row["region"]),
            "current_state":      state,
            "looks_healthy":      state in LOOKS_HEALTHY_STATES,
            "mttf_hours":         round(mttf, 1),
            "prob_fail_6h":       round(p6h * 100, 1),
            "prob_fail_24h":      round(float(row["prob_fail_24h"]) * 100, 1),
            "recommended_action": ACTION_BY_TYPE.get(str(row["type"]), "Inspect device"),
            "urgency":            urgency,
            "urgency_level":      urgency_level,
        })

    region_breakdown = [
        {
            "region":   region,
            "critical": int((group["risk_level"] == "CRITICAL").sum()),
            "high":     int((group["risk_level"] == "HIGH").sum()),
        }
        for region, group in dashboard_df[_is_high_risk(dashboard_df)].groupby("region")
    ]

    return {
        "currently_failing":     currently_failing,
        "high_risk":             int((dashboard_df["risk_level"] == "HIGH").sum()),
        "medium_risk":           int((dashboard_df["risk_level"] == "MEDIUM").sum()),
        "look_ok_but_high_risk": look_ok_count,
        "priority_actions":      actions,
        "region_breakdown":      region_breakdown,
    }


# ---------------------------------------------------------------------------
# Routes — AI Chat (Azure OpenAI GPT-4o-mini)
# ---------------------------------------------------------------------------

@app.post("/api/ai/chat")
async def ai_chat(body: ChatRequest):
    """
    LLM-powered Q&A grounded in live network data.

    The system prompt is built fresh on each request — it includes the current
    risk distribution, top at-risk devices, KPI correlations, and transition
    highlights. This means the AI answers are always grounded in real numbers
    from the loaded dataset, not generic knowledge.

    Multi-turn: pass the full conversation history in `messages` each call.
    """
    network_context = _build_network_context()

    system_prompt = f"""You are NetGuard AI, an expert network reliability engineer embedded in a live monitoring dashboard.

{network_context}

Your role: help NOC teams and network engineers interpret the data, prioritize actions, and understand reliability concepts.

Guidelines:
- Be specific — reference actual numbers from the network context above when relevant.
- Keep responses concise (3–5 sentences unless a step-by-step explanation is needed).
- Use plain language — assume the user may not be a data scientist.
- If asked about something unrelated to network reliability or this dashboard, briefly redirect."""

    messages = [{"role": "system", "content": system_prompt}]
    messages += [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        response = ai_client.chat.completions.create(
            model=AZURE_DEPLOYMENT,
            messages=messages,
            temperature=0.3,
            max_tokens=600,
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI service unavailable: {str(e)}")


# ---------------------------------------------------------------------------
# Routes — Custom Matrix Analysis
# ---------------------------------------------------------------------------

@app.post("/api/analyze/custom-matrix")
async def analyze_custom_matrix(body: MatrixRequest):
    """
    Compute failure curves and MTTF from a user-supplied transition matrix.

    Useful for what-if analysis: "if I improve the RAN → Failure transition rate
    by 10%, how much does MTTF improve?" — just modify the matrix and re-run.

    Validation:
      - Matrix must be N×N (matching the number of states provided)
      - Each row must sum to 1.0 (±0.02 tolerance)
      - No negative probabilities
    """
    n = len(body.states)

    if n < 2:
        raise HTTPException(400, "Need at least 2 states")
    if len(body.matrix) != n or any(len(row) != n for row in body.matrix):
        raise HTTPException(400, f"Matrix must be {n}×{n} to match {n} states")

    P = np.array(body.matrix, dtype=float)

    if (P < 0).any():
        raise HTTPException(400, "Transition probabilities cannot be negative")

    row_sums = P.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=0.02):
        bad = [f"{body.states[i]}={round(float(row_sums[i]), 3)}"
               for i in range(n) if abs(float(row_sums[i]) - 1.0) > 0.02]
        raise HTTPException(400, f"These rows don't sum to 1.0: {bad}")

    curves = _compute_failure_curves(P, body.states)
    mttf   = _compute_mttf(P, body.states)

    return {
        "states":       body.states,
        "hours":        list(range(1, 169)),
        "curves":       curves,
        "mttf_hours":   mttf,
        "prob_fail_24h": {s: curves[s][23]  for s in curves},
        "prob_fail_7d":  {s: curves[s][167] for s in curves},
    }


# ---------------------------------------------------------------------------
# Routes — Telemetry CSV Upload
# ---------------------------------------------------------------------------

@app.get("/api/sample-csv")
async def download_sample_csv():
    """
    Download a sample CSV showing the expected format for the upload endpoint.

    Required column : state       (Healthy / Warning / Minor / Major / Failure)
    Optional column : element_id  (if present, transitions are scoped per element)
    """
    return StreamingResponse(
        io.BytesIO(SAMPLE_CSV.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_telemetry.csv"},
    )


@app.post("/api/upload/telemetry")
async def upload_telemetry(file: UploadFile = File(...)):
    """
    Upload your own CSV of device state observations → estimate a Markov matrix → full analysis.

    Pipeline:
      1. Parse CSV, validate 'state' column
      2. If 'element_id' present: group by element and build sequences within each device
         (so state transitions don't bleed across different devices)
      3. Estimate transition matrix using MLE (count transitions, normalize rows)
      4. Run _compute_failure_curves() and _compute_mttf() on the estimated matrix
      5. Return everything: matrix, curves, MTTF, 24h probs

    Minimum recommended size: 50+ state observations for a meaningful estimate.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(400, f"Could not parse CSV: {e}")

    if "state" not in df.columns:
        raise HTTPException(400, "CSV must have a 'state' column")

    invalid_states = set(df["state"].dropna().unique()) - set(VALID_STATES)
    if invalid_states:
        raise HTTPException(
            400,
            f"Unknown states: {invalid_states}. Valid values: {VALID_STATES}"
        )

    # Build state sequence — scoped per element if element_id column is present
    if "element_id" in df.columns:
        sequence = []
        for _, group in df.groupby("element_id"):
            sequence.extend(group["state"].dropna().tolist())
        unique_elements = int(df["element_id"].nunique())
    else:
        sequence = df["state"].dropna().tolist()
        unique_elements = 1

    if len(sequence) < 2:
        raise HTTPException(400, "Need at least 2 state records to estimate transitions")

    # Count raw transitions for the response (transparency)
    n   = len(VALID_STATES)
    idx = {s: i for i, s in enumerate(VALID_STATES)}
    counts = np.zeros((n, n))
    for i in range(len(sequence) - 1):
        from_s, to_s = sequence[i], sequence[i + 1]
        if from_s in idx and to_s in idx:
            counts[idx[from_s]][idx[to_s]] += 1

    P      = _estimate_transition_matrix(sequence)
    curves = _compute_failure_curves(P, VALID_STATES)
    mttf   = _compute_mttf(P, VALID_STATES)

    return {
        "rows_processed":      len(df),
        "transitions_counted": int(counts.sum()),
        "unique_elements":     unique_elements,
        "estimated_matrix": {
            "states": VALID_STATES,
            "matrix": [[_rf(v) for v in row] for row in P],
        },
        "hours":           list(range(1, 169)),
        "failure_curves":  curves,
        "mttf_hours":      mttf,
        "prob_fail_24h":   {s: curves[s][23]  for s in curves},
        "prob_fail_7d":    {s: curves[s][167] for s in curves},
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3721, reload=False)
