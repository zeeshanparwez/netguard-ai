"""
Central configuration — loaded once at import time.
All other modules import from here; nothing reads os.getenv() directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Directory layout (relative to this file's location)
# ---------------------------------------------------------------------------

ROOT_DIR     = Path(__file__).parent.parent   # health_device/
DATA_DIR     = ROOT_DIR / "data"
RAW_DIR      = DATA_DIR / "raw"               # source Excel files
RESULTS_DIR  = DATA_DIR / "results"           # pre-computed CSV outputs
FRONTEND_DIR = ROOT_DIR / "frontend"          # dashboard.html

# ---------------------------------------------------------------------------
# Azure OpenAI credentials (from .env)
# ---------------------------------------------------------------------------

AZURE_API_KEY     = os.getenv("AZURE_API_KEY")
AZURE_API_BASE    = os.getenv("AZURE_API_BASE")
AZURE_API_VERSION = os.getenv("AZURE_API_VERSION", "2024-10-21")
AZURE_DEPLOYMENT  = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini")

# ---------------------------------------------------------------------------
# Markov model domain constants
# ---------------------------------------------------------------------------

# Ordered state list — must match the CSV column/row order exactly
VALID_STATES = ["Healthy", "Warning", "Minor", "Major", "Failure"]

HIGH_RISK_LEVELS     = {"HIGH", "CRITICAL"}
LOOKS_HEALTHY_STATES = {"Healthy", "Warning", "Minor"}   # states that look fine but may be at risk

# Recommended NOC action per element type
ACTION_BY_TYPE = {
    "RAN":     "Dispatch field engineer — radio access network tower",
    "EDGE":    "NOC remote restart + on-site inspection team",
    "CORE":    "Alert NOC team — core switch intervention required",
    "OPTICAL": "Schedule fiber inspection and splice team",
}

# ---------------------------------------------------------------------------
# Business-impact constants (dataset-specific, Aug 1-14 2025)
# ---------------------------------------------------------------------------

DATASET_TOTAL_FAILURES    = 4_284
DATASET_AVG_FAILURE_HOURS = 4.89
DATASET_DEVICES           = 500
DATASET_PERIOD_HOURS      = 336   # 14 days × 24 h
DATASET_PREVENTABLE_PCT   = 60    # % of failures preventable with 24h advance warning

# ---------------------------------------------------------------------------
# Sample CSV template (served as a downloadable file)
# ---------------------------------------------------------------------------

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
