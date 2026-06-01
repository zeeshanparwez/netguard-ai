"""
Generates architecture.png — run: python generate_arch.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np

W, H = 22, 15
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#0d1117")

# ── helpers ──────────────────────────────────────────────────────────────────
def rbox(x, y, w, h, fc, ec, lw=2.0, alpha=1.0, radius=0.3, zorder=3):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={radius}",
                       facecolor=fc, edgecolor=ec, linewidth=lw,
                       alpha=alpha, zorder=zorder)
    ax.add_patch(p)

def txt(x, y, s, size=11, color="#e6edf3", weight="normal",
        ha="center", va="center", zorder=6, alpha=1.0):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=zorder, alpha=alpha,
            fontfamily="DejaVu Sans")

def pill(x, y, s, fc, tc="#ffffff", size=8.5, zorder=7):
    ax.text(x, y, s, fontsize=size, color=tc, fontweight="bold",
            ha="center", va="center", zorder=zorder,
            bbox=dict(boxstyle="round,pad=0.35", facecolor=fc,
                      edgecolor="none", alpha=0.9))

def arrow_v(x, y1, y2, color="#4b5563", lw=1.8):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=14),
                zorder=2)

def arrow_h(x1, x2, y, color="#4b5563", lw=1.8):
    ax.annotate("", xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=14),
                zorder=2)

def divider(x, y, w, color="#2d333b"):
    ax.plot([x, x + w], [y, y], color=color, lw=1, zorder=4)

# ═══════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════
txt(W / 2, H - 0.5, "NetGuard AI — System Architecture",
    size=20, color="#e6edf3", weight="bold")
txt(W / 2, H - 1.0,
    "Markov Chain Failure Prediction  ·  GPT-4o-mini AI Chat  ·  Monte Carlo Validation",
    size=10, color="#8b949e", alpha=0.85)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 1 — Browser (full width)
# ═══════════════════════════════════════════════════════════════════════════
BX, BY, BW, BH = 1.2, 11.8, W - 2.4, 1.5
rbox(BX, BY, BW, BH, "#161b22", "#58a6ff", lw=2.2)
txt(BX + 0.5, BY + 1.0, "Browser / Client", size=13, color="#58a6ff",
    weight="bold", ha="left")
txt(BX + 0.5, BY + 0.55, "Vanilla JS  ·  Chart.js 4  ·  dashboard.html  ·  Single-page app",
    size=9.5, color="#8b949e", ha="left")
pill(BX + BW - 2.0, BY + 0.95, "http://your-ip:3721", "#1d4ed8", size=9)
pill(BX + BW - 2.0, BY + 0.48, "Port 3721", "#374151", size=8.5)

# ── arrow down ────────────────────────────────────────────────────────────
arrow_v(W / 2, BY, BY - 0.25, color="#58a6ff")
txt(W / 2 + 0.35, BY - 0.12, "HTTP", size=8, color="#8b949e", ha="left")

# ═══════════════════════════════════════════════════════════════════════════
# ROW 2 — FastAPI (full width, with 3 sub-boxes)
# ═══════════════════════════════════════════════════════════════════════════
FX, FY, FW, FH = 1.2, 9.0, W - 2.4, 2.55
rbox(FX, FY, FW, FH, "#0f1e14", "#3fb950", lw=2.2)
txt(FX + FW / 2, FY + FH - 0.38,
    "FastAPI Application  ·  backend/main.py  ·  Port 3721",
    size=12, color="#3fb950", weight="bold")

# Three API boxes
api_data = [
    ("analytics.py",  "#238636", "#56d364",
     ["GET /api/*", "10 read-only routes", "Pre-computed data", "Serves dashboard HTML"]),
    ("ai.py",         "#1d3a5c", "#79c0ff",
     ["POST /api/ai/chat", "", "GPT-4o-mini chat", "with live context"]),
    ("analysis.py",   "#3a1d4a", "#d2a8ff",
     ["POST /api/analyze/", "custom-matrix", "POST /api/upload/", "telemetry"]),
]
api_w, api_gap = 5.6, 0.7
api_start = FX + (FW - 3 * api_w - 2 * api_gap) / 2
for i, (name, fc, ec, lines) in enumerate(api_data):
    ax_box = api_start + i * (api_w + api_gap)
    ay_box = FY + 0.22
    rbox(ax_box, ay_box, api_w, 1.75, fc, ec, lw=1.6, radius=0.2)
    txt(ax_box + api_w / 2, ay_box + 1.46, name, size=10.5, color=ec,
        weight="bold")
    divider(ax_box + 0.25, ay_box + 1.28, api_w - 0.5, color=ec)
    for j, line in enumerate(lines):
        txt(ax_box + api_w / 2, ay_box + 1.05 - j * 0.24,
            line, size=8.5, color="#8b949e")

# ── arrows down ───────────────────────────────────────────────────────────
for i in range(3):
    cx = api_start + i * (api_w + api_gap) + api_w / 2
    arrow_v(cx, FY, FY - 0.25, color="#3fb950")

# ═══════════════════════════════════════════════════════════════════════════
# ROW 3 — Services (full width, 3 sub-boxes)
# ═══════════════════════════════════════════════════════════════════════════
SX, SY, SW, SH = 1.2, 6.1, W - 2.4, 2.65
rbox(SX, SY, SW, SH, "#161022", "#8957e5", lw=2.2)
txt(SX + SW / 2, SY + SH - 0.38,
    "Service Layer  ·  backend/services/",
    size=12, color="#8957e5", weight="bold")

svc_data = [
    ("data.py",        "#1f1535", "#a371f7",
     ["Loads all 5 CSVs at startup", "dashboard_df · mttf_df · corr_df",
      "transition_df · mc_df", "rf() · valid_mttf() · is_high_risk()"]),
    ("markov.py",      "#132236", "#79c0ff",
     ["compute_failure_curves()", "compute_mttf()  →  N=(I−Q)⁻¹",
      "estimate_transition_matrix()", "validate_matrix()"]),
    ("ai_service.py",  "#241535", "#c792ea",
     ["AzureOpenAI client (singleton)", "build_network_context()",
      "chat(messages: List[dict])", "Live snapshot → system prompt"]),
]
svc_w, svc_gap = 5.6, 0.7
svc_start = SX + (SW - 3 * svc_w - 2 * svc_gap) / 2
for i, (name, fc, ec, lines) in enumerate(svc_data):
    sx_box = svc_start + i * (svc_w + svc_gap)
    sy_box = SY + 0.22
    rbox(sx_box, sy_box, svc_w, 1.88, fc, ec, lw=1.6, radius=0.2)
    txt(sx_box + svc_w / 2, sy_box + 1.6, name, size=10.5, color=ec, weight="bold")
    divider(sx_box + 0.25, sy_box + 1.42, svc_w - 0.5, color=ec)
    for j, line in enumerate(lines):
        txt(sx_box + svc_w / 2, sy_box + 1.2 - j * 0.27,
            line, size=8.5, color="#8b949e")

# ── arrows down ───────────────────────────────────────────────────────────
arrow_v(svc_start + svc_w / 2, SY, SY - 0.25, color="#8957e5")
arrow_v(svc_start + svc_w / 2 + svc_w + svc_gap, SY, SY - 0.25, color="#8957e5")
arrow_v(svc_start + 2 * (svc_w + svc_gap) + svc_w / 2, SY, SY - 0.25, color="#8957e5")

# ═══════════════════════════════════════════════════════════════════════════
# ROW 4 — Data + Azure (side by side)
# ═══════════════════════════════════════════════════════════════════════════
# Data box
DX, DY, DW, DH = 1.2, 3.0, 11.8, 2.85
rbox(DX, DY, DW, DH, "#1c0f0f", "#f85149", lw=2.2)
txt(DX + DW / 2, DY + DH - 0.4, "Data Layer  ·  data/",
    size=12, color="#f85149", weight="bold")
divider(DX + 0.3, DY + DH - 0.72, DW - 0.6, color="#f85149")

# raw folder
txt(DX + 0.5, DY + 2.0, "data/raw/", size=9.5, color="#f85149",
    weight="bold", ha="left")
for j, f in enumerate(["failures.xlsx", "network_elements.xlsx",
                        "telemetry.xlsx", "transition_profiles.xlsx"]):
    txt(DX + 0.7, DY + 1.68 - j * 0.28, f"▸  {f}", size=8.5,
        color="#8b949e", ha="left")

# results folder
txt(DX + 6.3, DY + 2.0, "data/results/", size=9.5, color="#f85149",
    weight="bold", ha="left")
for j, f in enumerate(["network_risk_dashboard.csv",
                        "element_mttf_analysis.csv",
                        "estimated_transition_matrix.csv",
                        "kpi_correlation_matrix.csv",
                        "monte_carlo_results.csv"]):
    txt(DX + 6.5, DY + 1.68 - j * 0.28, f"▸  {f}", size=8.5,
        color="#8b949e", ha="left")

# Azure box
AX, AY, AW, AH = 13.4, 3.0, 7.4, 2.85
rbox(AX, AY, AW, AH, "#160f22", "#c792ea", lw=2.2)
txt(AX + AW / 2, AY + AH - 0.4, "Azure OpenAI",
    size=12, color="#c792ea", weight="bold")
divider(AX + 0.3, AY + AH - 0.72, AW - 0.6, color="#c792ea")
pill(AX + AW / 2, AY + 1.92, "Model: GPT-4o-mini", "#4c1d95", tc="#c792ea", size=9)
for j, line in enumerate([
    "Network snapshot built on every request",
    "Injected as system prompt",
    "Answers grounded in live network data",
    "NOC-operator friendly plain English",
]):
    txt(AX + AW / 2, AY + 1.52 - j * 0.30, line, size=8.5, color="#8b949e")

# ═══════════════════════════════════════════════════════════════════════════
# ROW 5 — Schemas (bottom strip)
# ═══════════════════════════════════════════════════════════════════════════
SCX, SCY, SCW, SCH = 1.2, 1.1, W - 2.4, 1.6
rbox(SCX, SCY, SCW, SCH, "#161b22", "#30363d", lw=1.6)
txt(SCX + SCW / 2, SCY + SCH - 0.32,
    "Schemas  ·  backend/schemas/requests.py",
    size=10.5, color="#8b949e", weight="bold")
divider(SCX + 0.3, SCY + SCH - 0.58, SCW - 0.6, color="#30363d")

schema_items = [
    ("ChatMessage",   "{ role: str,  content: str }"),
    ("ChatRequest",   "{ messages: List[ChatMessage] }"),
    ("MatrixRequest", "{ states: List[str],  matrix: List[List[float]] }"),
]
for i, (name, body) in enumerate(schema_items):
    x0 = SCX + 0.8 + i * (SCW / 3)
    txt(x0, SCY + 0.78, name, size=9.5, color="#79c0ff", weight="bold", ha="left")
    txt(x0, SCY + 0.42, body, size=8.0, color="#8b949e", ha="left")

# ═══════════════════════════════════════════════════════════════════════════
# TECH STACK BADGES (very bottom)
# ═══════════════════════════════════════════════════════════════════════════
badges = [
    ("Python 3.11+", "#3b7bc8"), ("FastAPI", "#009688"),
    ("NumPy", "#013243"),        ("Pandas", "#150458"),
    ("Azure OpenAI", "#0078d4"), ("Chart.js", "#ff6384"),
    ("Uvicorn", "#2f9560"),      ("python-dotenv", "#555"),
]
total_w = len(badges) * 2.3
start_x = (W - total_w) / 2 + 1.15
for i, (name, fc) in enumerate(badges):
    pill(start_x + i * 2.3, 0.55, name, fc, size=8)

# ═══════════════════════════════════════════════════════════════════════════
# Save
# ═══════════════════════════════════════════════════════════════════════════
plt.tight_layout(pad=0)
out = "/home/support/zee_workspace/zee/health_device/architecture.png"
plt.savefig(out, dpi=160, bbox_inches="tight", facecolor="#0d1117")
print(f"Saved → {out}")
