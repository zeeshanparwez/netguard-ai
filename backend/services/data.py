"""
Data layer — loads all pre-computed CSVs once at startup and exposes
shared DataFrames + small helper functions used across API routes.
"""

import pandas as pd

from backend.config import HIGH_RISK_LEVELS, RESULTS_DIR

# ---------------------------------------------------------------------------
# Load DataFrames at module import (server startup)
# These are shared across all request handlers — no per-request I/O.
# ---------------------------------------------------------------------------

dashboard_df  = pd.read_csv(RESULTS_DIR / "network_risk_dashboard.csv")
mttf_df       = pd.read_csv(RESULTS_DIR / "element_mttf_analysis.csv")
corr_df       = pd.read_csv(RESULTS_DIR / "kpi_correlation_matrix.csv",      index_col=0)
transition_df = pd.read_csv(RESULTS_DIR / "estimated_transition_matrix.csv", index_col=0)
mc_df         = pd.read_csv(RESULTS_DIR / "monte_carlo_results.csv")

print(f"[data] Loaded {len(dashboard_df)} elements | {len(mttf_df)} MTTF records")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def valid_mttf(df: pd.DataFrame) -> pd.Series:
    """Exclude the 99999 sentinel used for elements that never failed."""
    return df[df["mttf_hours"] < 99_999]["mttf_hours"]


def is_high_risk(df: pd.DataFrame) -> pd.Series:
    """Boolean mask for HIGH or CRITICAL risk rows."""
    return df["risk_level"].isin(HIGH_RISK_LEVELS)


def rf(value, decimals: int = 4) -> float:
    """Round a value to N decimal places and return as float."""
    return round(float(value), decimals)
