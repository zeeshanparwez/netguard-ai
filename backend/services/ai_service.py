"""
AI service — wraps the Azure OpenAI client and builds the network context
string that gets injected into every chat system prompt.

Only this module touches the OpenAI SDK; API routes import from here.
"""

from typing import List

from openai import AzureOpenAI

from backend.config import (
    AZURE_API_KEY,
    AZURE_API_BASE,
    AZURE_API_VERSION,
    AZURE_DEPLOYMENT,
    HIGH_RISK_LEVELS,
    LOOKS_HEALTHY_STATES,
)

# Single shared client — created once at import time
_client = AzureOpenAI(
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION,
    azure_endpoint=AZURE_API_BASE,
)

SYSTEM_PROMPT_TEMPLATE = """You are NetGuard AI, an expert network reliability engineer embedded in a live monitoring dashboard.

{network_context}

Your role: help NOC teams and network engineers interpret the data, prioritise actions, and understand reliability concepts.

Guidelines:
- Be specific — reference actual numbers from the network context when relevant.
- Keep responses concise (3–5 sentences unless a step-by-step explanation is needed).
- Use plain language — assume the user may not be a data scientist.
- If asked about something unrelated to network reliability, politely redirect."""


def build_network_context() -> str:
    """
    Build a live snapshot of the network for the AI system prompt.
    Imported here (inside the function) to avoid a circular import at module load.
    """
    from backend.services.data import dashboard_df, valid_mttf

    rd = {k: int(v) for k, v in dashboard_df["risk_level"].value_counts().items()}
    sd = {k: int(v) for k, v in dashboard_df["current_state"].value_counts().items()}
    avg_mttf = round(float(valid_mttf(dashboard_df).mean()), 1)
    avg_24h  = round(float(dashboard_df["prob_fail_24h"].mean()) * 100, 1)

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

    return f"""\
LIVE NETWORK SNAPSHOT (Aug 1–14, 2025 | 500 elements | 168,000 telemetry records):
  Risk distribution  : {rd}
  State distribution : {sd}
  Average MTTF       : {avg_mttf}h (elements that actually fail)
  Avg 24h fail prob  : {avg_24h}%
  Model              : Markov Chain (5 states) + Monte Carlo (99.8% accuracy)
  Element types      : RAN, OPTICAL, EDGE, CORE
  Regions            : North, South, East, West, Central

TOP 5 HIGHEST-RISK PRE-FAILURE DEVICES:
{top5_lines}

KEY KPI CORRELATIONS:
  CPU % ↔ Signal Quality : −0.920  (high CPU degrades signal)
  Packet Drop ↔ Errors   : +0.976  (they fail together)
  All 6 KPIs co-degrade  : any single metric is a valid early-warning signal

MARKOV TRANSITION HIGHLIGHTS:
  Healthy stability  : 87.8% chance of staying Healthy each hour
  Failure absorption : 79.7% remain Failed, 20.3% self-recover per hour"""


def chat(messages: List[dict]) -> str:
    """
    Send a message list to Azure OpenAI and return the assistant reply.
    Raises the raw OpenAI exception — the caller (API layer) handles HTTP errors.
    """
    response = _client.chat.completions.create(
        model=AZURE_DEPLOYMENT,
        messages=messages,
        temperature=0.3,
        max_tokens=600,
    )
    return response.choices[0].message.content
