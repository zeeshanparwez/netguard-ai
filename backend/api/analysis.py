"""
Analysis router — interactive POST endpoints that accept user-supplied data
and run live Markov computations (no pre-computed CSVs involved).

  POST /api/analyze/custom-matrix  — what-if analysis on any user matrix
  POST /api/upload/telemetry       — upload CSV → estimate matrix → full analysis
  GET  /api/sample-csv             — download the CSV template
"""

import io

import numpy as np
import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.config import SAMPLE_CSV, VALID_STATES
from backend.schemas.requests import MatrixRequest
from backend.services.markov import (
    compute_failure_curves,
    compute_mttf,
    estimate_transition_matrix,
    validate_matrix,
)
from backend.services.data import rf

router = APIRouter()


# ---------------------------------------------------------------------------
# Sample CSV download
# ---------------------------------------------------------------------------

@router.get("/api/sample-csv")
async def download_sample_csv():
    """
    Download a CSV template showing the expected format for the upload endpoint.

    Required column : state       (Healthy / Warning / Minor / Major / Failure)
    Optional column : element_id  (transitions scoped per device if present)
    """
    return StreamingResponse(
        io.BytesIO(SAMPLE_CSV.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=sample_telemetry.csv"},
    )


# ---------------------------------------------------------------------------
# Custom matrix what-if analysis
# ---------------------------------------------------------------------------

@router.post("/api/analyze/custom-matrix")
async def analyze_custom_matrix(body: MatrixRequest):
    """
    Compute failure curves and MTTF from a user-supplied transition matrix.

    Useful for scenario modelling: "if I reduce the RAN failure rate by 15%,
    how does MTTF change?" — just modify the matrix and re-submit.

    Validates:
      - Matrix is N×N (matching the states list)
      - Each row sums to 1.0  (±0.02 tolerance)
      - No negative probabilities
    """
    if len(body.states) < 2:
        raise HTTPException(400, "Need at least 2 states")

    error = validate_matrix(body.matrix, body.states)
    if error:
        raise HTTPException(400, error)

    matrix = np.array(body.matrix, dtype=float)
    curves = compute_failure_curves(matrix, body.states)
    mttf   = compute_mttf(matrix, body.states)

    return {
        "states":        body.states,
        "hours":         list(range(1, 169)),
        "curves":        curves,
        "mttf_hours":    mttf,
        "prob_fail_24h": {s: curves[s][23]  for s in curves},
        "prob_fail_7d":  {s: curves[s][167] for s in curves},
    }


# ---------------------------------------------------------------------------
# Telemetry CSV upload → train your own Markov model
# ---------------------------------------------------------------------------

@router.post("/api/upload/telemetry")
async def upload_telemetry(file: UploadFile = File(...)):
    """
    Upload your own CSV of device state observations → estimate a Markov
    transition matrix using MLE → return the full failure analysis.

    Pipeline:
      1. Parse CSV, validate the 'state' column values
      2. If 'element_id' present: build state sequences within each device
         (avoids bleeding transitions across device boundaries)
      3. Estimate transition matrix (count pairs, normalise rows)
      4. Compute failure curves and MTTF on the estimated matrix
      5. Return everything for display in the dashboard

    Minimum recommended size: ~50 state observations for a stable estimate.
    """
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only .csv files are accepted")

    try:
        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
    except Exception as exc:
        raise HTTPException(400, f"Could not parse CSV: {exc}")

    if "state" not in df.columns:
        raise HTTPException(400, "CSV must contain a 'state' column")

    unknown = set(df["state"].dropna().unique()) - set(VALID_STATES)
    if unknown:
        raise HTTPException(400, f"Unknown states: {unknown}. Valid: {VALID_STATES}")

    # Build state sequence — scoped per device when element_id column exists
    if "element_id" in df.columns:
        sequence: list = []
        for _, grp in df.groupby("element_id"):
            sequence.extend(grp["state"].dropna().tolist())
        unique_elements = int(df["element_id"].nunique())
    else:
        sequence        = df["state"].dropna().tolist()
        unique_elements = 1

    if len(sequence) < 2:
        raise HTTPException(400, "Need at least 2 state records to estimate transitions")

    # Count raw transitions (returned for transparency)
    n   = len(VALID_STATES)
    idx = {s: i for i, s in enumerate(VALID_STATES)}
    counts = np.zeros((n, n))
    for i in range(len(sequence) - 1):
        from_s, to_s = sequence[i], sequence[i + 1]
        if from_s in idx and to_s in idx:
            counts[idx[from_s]][idx[to_s]] += 1

    matrix = estimate_transition_matrix(sequence)
    curves = compute_failure_curves(matrix, VALID_STATES)
    mttf   = compute_mttf(matrix, VALID_STATES)

    return {
        "rows_processed":      len(df),
        "transitions_counted": int(counts.sum()),
        "unique_elements":     unique_elements,
        "estimated_matrix": {
            "states": VALID_STATES,
            "matrix": [[rf(v) for v in row] for row in matrix],
        },
        "hours":          list(range(1, 169)),
        "failure_curves": curves,
        "mttf_hours":     mttf,
        "prob_fail_24h":  {s: curves[s][23]  for s in curves},
        "prob_fail_7d":   {s: curves[s][167] for s in curves},
    }
