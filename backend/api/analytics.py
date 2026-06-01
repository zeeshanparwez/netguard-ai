"""
Analytics router — read-only GET endpoints that serve pre-computed data.

All heavy computation (Markov math, DataFrame operations) is already done
offline; these routes just query in-memory DataFrames and return JSON.
"""

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.config import (
    ACTION_BY_TYPE,
    DATASET_AVG_FAILURE_HOURS,
    DATASET_DEVICES,
    DATASET_PERIOD_HOURS,
    DATASET_PREVENTABLE_PCT,
    DATASET_TOTAL_FAILURES,
    FRONTEND_DIR,
    HIGH_RISK_LEVELS,
    LOOKS_HEALTHY_STATES,
)
from backend.services.data import (
    corr_df,
    dashboard_df,
    is_high_risk,
    mc_df,
    mttf_df,
    rf,
    transition_df,
    valid_mttf,
)
from backend.services.markov import compute_failure_curves

router = APIRouter()


# ---------------------------------------------------------------------------
# Dashboard HTML
# ---------------------------------------------------------------------------

@router.get("/")
async def serve_dashboard():
    """Serve the single-page analytics dashboard."""
    return FileResponse(FRONTEND_DIR / "dashboard.html")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@router.get("/api/summary")
async def get_summary():
    """
    Top-level health overview: risk & state distributions, average MTTF,
    24h failure probability, and breakdowns by device type and region.
    """
    risk_dist  = {k: int(v) for k, v in dashboard_df["risk_level"].value_counts().items()}
    state_dist = {k: int(v) for k, v in dashboard_df["current_state"].value_counts().items()}
    vmttf      = valid_mttf(dashboard_df)

    by_type = []
    for device_type, grp in dashboard_df.groupby("type"):
        tmttf = valid_mttf(grp)
        by_type.append({
            "type":          device_type,
            "avg_fail_24h":  rf(grp["prob_fail_24h"].mean()),
            "avg_mttf":      rf(tmttf.mean(), 2) if len(tmttf) > 0 else 0,
            "critical_high": int(is_high_risk(grp).sum()),
            "total":         int(len(grp)),
        })

    by_region = [
        {
            "region":        region,
            "avg_fail_24h":  rf(grp["prob_fail_24h"].mean()),
            "critical_high": int(is_high_risk(grp).sum()),
            "total":         int(len(grp)),
        }
        for region, grp in dashboard_df.groupby("region")
    ]

    return {
        "total_elements":          len(dashboard_df),
        "risk_distribution":       risk_dist,
        "state_distribution":      state_dist,
        "avg_mttf_hours":          rf(vmttf.mean(), 2),
        "avg_fail_prob_24h":       rf(dashboard_df["prob_fail_24h"].mean()),
        "pct_healthy":             round(state_dist.get("Healthy", 0) / len(dashboard_df) * 100, 1),
        "by_type":                 by_type,
        "by_region":               by_region,
        "data_period":             "August 1–14, 2025",
        "total_elements_analyzed": 500,
        "total_telemetry_records": 168_000,
        "total_failure_events":    4_284,
    }


# ---------------------------------------------------------------------------
# Markov model data
# ---------------------------------------------------------------------------

@router.get("/api/transition-matrix")
async def get_transition_matrix():
    """
    Hourly Markov state-transition matrix (5×5), estimated from 167,500 transitions.
    Rows = from-state, Columns = to-state.
    """
    states = transition_df.index.tolist()
    matrix = [[rf(v) for v in row] for row in transition_df.values]
    return {"states": states, "matrix": matrix}


@router.get("/api/kpi-correlation")
async def get_kpi_correlation():
    """
    Pearson correlation matrix (6×6) across 168,000 telemetry readings.
    KPIs: cpu_pct, memory_pct, temperature_c, pkt_drop_pct, error_count, signal_quality.
    """
    return {
        "labels": corr_df.index.tolist(),
        "matrix": [[rf(v, 3) for v in row] for row in corr_df.values],
    }


@router.get("/api/failure-curves")
async def get_failure_curves():
    """
    Cumulative failure probability per starting state over 168 hours.
    Computed live by iterating the Markov transition matrix.
    """
    states = transition_df.index.tolist()
    P      = transition_df.values.astype(float)
    curves = compute_failure_curves(P, states)
    return {"hours": list(range(1, 169)), "curves": curves}


@router.get("/api/monte-carlo")
async def get_monte_carlo():
    """
    Cross-validation: Markov analytical model vs Monte Carlo simulation (5,000 runs).
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


# ---------------------------------------------------------------------------
# MTTF breakdown
# ---------------------------------------------------------------------------

@router.get("/api/mttf-breakdown")
async def get_mttf_breakdown():
    """
    MTTF (mean/min/max) by device type and region.
    Excludes elements with mttf_hours = 99999 (never failed during the period).
    """
    valid = mttf_df[mttf_df["mttf_hours"] < 99_999]

    by_type   = [{"type":   t, "mean": rf(g["mttf_hours"].mean(), 2),
                  "min": rf(g["mttf_hours"].min(), 2), "max": rf(g["mttf_hours"].max(), 2)}
                 for t, g in valid.groupby("type")]
    by_region = [{"region": r, "mean": rf(g["mttf_hours"].mean(), 2),
                  "min": rf(g["mttf_hours"].min(), 2), "max": rf(g["mttf_hours"].max(), 2)}
                 for r, g in valid.groupby("region")]

    return {"by_type": by_type, "by_region": by_region}


# ---------------------------------------------------------------------------
# Elements table (paginated + filtered)
# ---------------------------------------------------------------------------

@router.get("/api/elements")
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
    Paginated, filterable, sortable table of all 500 elements.

    Filters:
      risk_filter — CRITICAL / HIGH / MEDIUM / LOW / NORMAL / ALL
      type_filter — RAN / OPTICAL / EDGE / CORE / ALL
      search      — substring match on element_id (case-insensitive)
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


# ---------------------------------------------------------------------------
# Business impact
# ---------------------------------------------------------------------------

@router.get("/api/business-impact")
async def get_business_impact():
    """
    ROI comparison: reactive (status quo) vs predictive (NetGuard AI) maintenance.
    """
    total_downtime     = round(DATASET_TOTAL_FAILURES * DATASET_AVG_FAILURE_HOURS)
    total_device_hours = DATASET_DEVICES * DATASET_PERIOD_HOURS
    current_avail      = round((1 - total_downtime / total_device_hours) * 100, 1)

    preventable  = round(DATASET_TOTAL_FAILURES * DATASET_PREVENTABLE_PCT / 100)
    saved_hours  = round(preventable * DATASET_AVG_FAILURE_HOURS)
    target_avail = round((1 - (total_downtime - saved_hours) / total_device_hours) * 100, 1)

    return {
        "period_days": 14,
        "devices":     DATASET_DEVICES,
        "current": {
            "total_failures":              DATASET_TOTAL_FAILURES,
            "failures_per_day":            round(DATASET_TOTAL_FAILURES / 14),
            "avg_failure_duration_h":      DATASET_AVG_FAILURE_HOURS,
            "total_downtime_device_hours": total_downtime,
            "availability_pct":            current_avail,
        },
        "with_netguard": {
            "preventable_pct":       DATASET_PREVENTABLE_PCT,
            "preventable_failures":  preventable,
            "downtime_hours_saved":  saved_hours,
            "availability_pct":      target_avail,
            "advance_warning_hours": 24,
        },
    }


# ---------------------------------------------------------------------------
# Priority action board
# ---------------------------------------------------------------------------

@router.get("/api/priority-actions")
async def get_priority_actions():
    """
    Top 10 HIGH-risk devices NOT yet in Failure state.

    Urgency tiers:
      DISPATCH NOW    — MTTF < 20h  or  P(fail@6h) > 45%
      ACT WITHIN 12H  — MTTF < 35h
      SCHEDULE TODAY  — all other HIGH-risk
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
            "critical": int((grp["risk_level"] == "CRITICAL").sum()),
            "high":     int((grp["risk_level"] == "HIGH").sum()),
        }
        for region, grp in dashboard_df[is_high_risk(dashboard_df)].groupby("region")
    ]

    return {
        "currently_failing":     currently_failing,
        "high_risk":             int((dashboard_df["risk_level"] == "HIGH").sum()),
        "medium_risk":           int((dashboard_df["risk_level"] == "MEDIUM").sum()),
        "look_ok_but_high_risk": look_ok_count,
        "priority_actions":      actions,
        "region_breakdown":      region_breakdown,
    }
