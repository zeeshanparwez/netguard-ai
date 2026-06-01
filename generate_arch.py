"""
Generates the NetGuard AI architecture diagram as architecture.png
Run: python generate_arch.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(16, 12))
ax.set_xlim(0, 16)
ax.set_ylim(0, 12)
ax.axis("off")
fig.patch.set_facecolor("#0f1117")
ax.set_facecolor("#0f1117")

# ── colour palette ───────────────────────────────────────────────────────────
C_BROWSER   = "#1a1f2e"
C_FASTAPI   = "#1a2a1f"
C_SERVICE   = "#1a1f2a"
C_DATA      = "#2a1a1f"
C_AI        = "#1f1a2a"
C_BORDER_B  = "#00d9ff"
C_BORDER_G  = "#00ff88"
C_BORDER_S  = "#7b68ee"
C_BORDER_D  = "#ff6b6b"
C_BORDER_AI = "#c792ea"
C_TEXT      = "#e8eaf0"
C_SUBTEXT   = "#9aa0b4"
C_ARROW     = "#4a5568"
C_BADGE     = "#2d3748"

def box(ax, x, y, w, h, fc, ec, lw=1.5, radius=0.25):
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle=f"round,pad=0,rounding_size={radius}",
                           facecolor=fc, edgecolor=ec, linewidth=lw, zorder=3)
    ax.add_patch(patch)

def label(ax, x, y, text, size=9, color=C_TEXT, weight="normal", ha="center", va="center"):
    ax.text(x, y, text, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=4, fontfamily="monospace")

def arrow(ax, x1, y1, x2, y2, color=C_ARROW):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.5,
                                mutation_scale=12), zorder=2)

def badge(ax, x, y, text, fc, tc="#ffffff"):
    ax.text(x, y, f" {text} ", fontsize=7, color=tc, fontweight="bold",
            ha="center", va="center", zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", facecolor=fc, edgecolor="none"))

# ── title ────────────────────────────────────────────────────────────────────
ax.text(8, 11.5, "NetGuard AI  —  System Architecture",
        fontsize=15, color=C_TEXT, fontweight="bold", ha="center", va="center",
        fontfamily="monospace", zorder=4)
ax.text(8, 11.1, "Markov Chain Failure Prediction · GPT-4o-mini AI Chat · Monte Carlo Validation",
        fontsize=8, color=C_SUBTEXT, ha="center", va="center", fontfamily="monospace", zorder=4)

# ═══════════════════════════════════════════════════════════════════════════
# LAYER 1 — Browser
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 4.5, 9.8, 7, 1.0, C_BROWSER, C_BORDER_B, lw=2)
label(ax, 6.2, 10.55, "Browser / Client", size=10, weight="bold", color=C_BORDER_B)
label(ax, 6.2, 10.15, "Chart.js · Vanilla JS · dashboard.html", size=8, color=C_SUBTEXT)
badge(ax, 10.2, 10.55, "http://your-ip:3721", "#1d4ed8")
badge(ax, 10.2, 10.15, "Single-page app", "#374151")

# ═══════════════════════════════════════════════════════════════════════════
# LAYER 2 — FastAPI
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 1.0, 7.8, 14, 1.6, C_FASTAPI, C_BORDER_G, lw=2)
label(ax, 8, 9.15, "FastAPI Application  ·  backend/main.py  ·  Port 3721", size=9.5, weight="bold", color=C_BORDER_G)

# Three API columns inside FastAPI box
for i, (cx, title, routes, color) in enumerate([
    (3.2,  "analytics.py",  "GET /api/*\n10 read-only routes\nPre-computed data\n+ dashboard HTML", "#4ade80"),
    (8.0,  "ai.py",         "POST /api/ai/chat\n\nLLM chat with\nlive context", "#60a5fa"),
    (12.8, "analysis.py",   "POST /api/analyze/\ncustom-matrix\nPOST /api/upload/\ntelemetry", "#f472b6"),
]):
    box(ax, cx - 1.6, 7.95, 3.2, 1.05, "#0d1117", color, lw=1.2, radius=0.15)
    label(ax, cx, 8.75, title, size=8.5, weight="bold", color=color)
    for j, line in enumerate(routes.split("\n")):
        label(ax, cx, 8.48 - j * 0.155, line, size=7, color=C_SUBTEXT)

# ═══════════════════════════════════════════════════════════════════════════
# LAYER 3 — Services
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 1.0, 5.4, 14, 2.0, C_SERVICE, C_BORDER_S, lw=2)
label(ax, 8, 7.15, "Service Layer  ·  backend/services/", size=9.5, weight="bold", color=C_BORDER_S)

for cx, title, lines, color in [
    (3.2,  "data.py",
     ["Loads all CSVs once", "at startup", "Shared DataFrames", "+ helper functions"],
     "#a78bfa"),
    (8.0,  "markov.py",
     ["compute_failure_curves()", "compute_mttf()", "estimate_transition_matrix()", "validate_matrix()"],
     "#818cf8"),
    (12.8, "ai_service.py",
     ["AzureOpenAI client", "build_network_context()", "chat(messages)", "Live snapshot injection"],
     "#c084fc"),
]:
    box(ax, cx - 1.6, 5.55, 3.2, 1.45, "#0d1117", color, lw=1.2, radius=0.15)
    label(ax, cx, 6.73, title, size=8.5, weight="bold", color=color)
    for j, line in enumerate(lines):
        label(ax, cx, 6.48 - j * 0.18, line, size=7, color=C_SUBTEXT)

# ═══════════════════════════════════════════════════════════════════════════
# LAYER 4 — Data + Azure (side by side)
# ═══════════════════════════════════════════════════════════════════════════
# Data box
box(ax, 1.0, 2.5, 8.5, 2.5, C_DATA, C_BORDER_D, lw=2)
label(ax, 5.25, 4.75, "Data Layer  ·  data/", size=9.5, weight="bold", color=C_BORDER_D)

for row, text in enumerate([
    ("data/raw/",      "failures.xlsx · network_elements.xlsx"),
    ("",               "telemetry.xlsx · transition_profiles.xlsx"),
    ("data/results/",  "network_risk_dashboard.csv · element_mttf_analysis.csv"),
    ("",               "estimated_transition_matrix.csv · kpi_correlation_matrix.csv"),
    ("",               "monte_carlo_results.csv · failure_probabilities.csv"),
]):
    folder, files = text
    y = 4.42 - row * 0.33
    if folder:
        label(ax, 2.2, y, folder, size=7.5, weight="bold", color=C_BORDER_D, ha="left")
    label(ax, 4.6, y, files, size=7, color=C_SUBTEXT, ha="left")

# Azure box
box(ax, 10.0, 2.5, 5.0, 2.5, C_AI, C_BORDER_AI, lw=2)
label(ax, 12.5, 4.75, "Azure OpenAI", size=9.5, weight="bold", color=C_BORDER_AI)
for row, line in enumerate([
    "Model: GPT-4o-mini",
    "Network snapshot built",
    "fresh on every request",
    "Injected as system prompt",
    "Grounded in real data",
]):
    label(ax, 12.5, 4.42 - row * 0.33, line, size=7.5, color=C_SUBTEXT)

# ═══════════════════════════════════════════════════════════════════════════
# Schemas box (bottom)
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 1.0, 0.5, 14, 1.65, "#111827", "#4b5563", lw=1.2)
label(ax, 8, 1.9, "Schemas  ·  backend/schemas/requests.py", size=8.5, weight="bold", color="#9ca3af")
label(ax, 4.0,  1.5, "ChatMessage  { role: str, content: str }", size=7.5, color=C_SUBTEXT)
label(ax, 4.0,  1.2, "ChatRequest  { messages: List[ChatMessage] }", size=7.5, color=C_SUBTEXT)
label(ax, 11.5, 1.5, "MatrixRequest", size=7.5, color=C_SUBTEXT)
label(ax, 11.5, 1.2, "{ states: List[str], matrix: List[List[float]] }", size=7.5, color=C_SUBTEXT)

# ═══════════════════════════════════════════════════════════════════════════
# Arrows between layers
# ═══════════════════════════════════════════════════════════════════════════
# Browser → FastAPI
arrow(ax, 8, 9.8, 8, 9.4, color=C_BORDER_B)
ax.text(8.15, 9.62, "HTTP", fontsize=7, color=C_SUBTEXT, zorder=4, fontfamily="monospace")

# FastAPI → Services
arrow(ax, 3.2, 7.95, 3.2, 7.4, color=C_BORDER_G)
arrow(ax, 8.0, 7.95, 8.0, 7.4, color=C_BORDER_G)
arrow(ax, 12.8, 7.95, 12.8, 7.4, color=C_BORDER_G)

# Services → Data/Azure
arrow(ax, 3.2, 5.55, 3.2, 5.0, color=C_BORDER_S)
arrow(ax, 8.0, 5.55, 5.5, 5.0, color=C_BORDER_S)
arrow(ax, 12.8, 5.55, 12.5, 5.0, color=C_BORDER_S)

# Services/Data → Schemas
arrow(ax, 5.0, 2.5, 5.0, 2.15, color="#4b5563")
arrow(ax, 11.5, 2.5, 11.5, 2.15, color="#4b5563")

# ═══════════════════════════════════════════════════════════════════════════
# Tech-stack badges along the bottom edge
# ═══════════════════════════════════════════════════════════════════════════
for bx, text, color in [
    (1.5,  "Python 3.11+",    "#3b7bc8"),
    (3.3,  "FastAPI",         "#009688"),
    (5.1,  "NumPy",           "#013243"),
    (6.9,  "Pandas",          "#150458"),
    (8.7,  "Azure OpenAI",    "#0078d4"),
    (10.5, "Chart.js",        "#ff6384"),
    (12.3, "Uvicorn",         "#2f9560"),
    (14.1, "python-dotenv",   "#555555"),
]:
    badge(ax, bx, 0.22, text, color)

plt.tight_layout(pad=0)
out = "/home/support/zee_workspace/zee/health_device/architecture.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved → {out}")
