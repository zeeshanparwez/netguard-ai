"""
Generates architecture.png (light theme) — run: python generate_arch.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

W, H = 22, 15
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
fig.patch.set_facecolor("#f6f8fa")
ax.set_facecolor("#f6f8fa")

# ── palette ──────────────────────────────────────────────────────────────────
BLACK   = "#0d1117"
GREY1   = "#24292f"
GREY2   = "#57606a"
GREY3   = "#d0d7de"
WHITE   = "#ffffff"
BG_PAGE = "#f6f8fa"

C_BROWSER  = "#dff0ff"
C_BROWSER_B= "#0969da"
C_FASTAPI  = "#dafbe1"
C_FASTAPI_B= "#1a7f37"
C_SERVICE  = "#f3effe"
C_SERVICE_B= "#8250df"
C_DATA     = "#fff0f0"
C_DATA_B   = "#cf222e"
C_AZURE    = "#fbefff"
C_AZURE_B  = "#8250df"
C_SCHEMA   = "#fff8c5"
C_SCHEMA_B = "#9a6700"

C_ANAL_B   = "#1a7f37"
C_ANAL_F   = "#e6ffec"
C_AI_B     = "#0969da"
C_AI_F     = "#dff0ff"
C_ANAL2_B  = "#8250df"
C_ANAL2_F  = "#fbefff"

# ── helpers ───────────────────────────────────────────────────────────────────
def rbox(x, y, w, h, fc, ec, lw=1.8, radius=0.25, zorder=3):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fc, edgecolor=ec, linewidth=lw, zorder=zorder))

def txt(x, y, s, size=11, color=BLACK, weight="normal",
        ha="center", va="center", zorder=6):
    ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
            ha=ha, va=va, zorder=zorder, fontfamily="DejaVu Sans")

def pill(x, y, s, fc, tc=WHITE, size=8.5, zorder=7):
    ax.text(x, y, s, fontsize=size, color=tc, fontweight="bold",
            ha="center", va="center", zorder=zorder,
            bbox=dict(boxstyle="round,pad=0.35", facecolor=fc,
                      edgecolor="none", alpha=0.92))

def arrow_v(x, y1, y2, color=GREY2):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=1.6, mutation_scale=13), zorder=2)

def divider(x, y, w, color=GREY3):
    ax.plot([x, x + w], [y, y], color=color, lw=1, zorder=4)

# ═══════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════
txt(W / 2, H - 0.45, "NetGuard AI — System Architecture",
    size=20, color=BLACK, weight="bold")
txt(W / 2, H - 0.95,
    "Markov Chain Failure Prediction  ·  GPT-4o-mini AI Chat  ·  Monte Carlo Validation",
    size=9.5, color=GREY2)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 1 — Browser
# ═══════════════════════════════════════════════════════════════════════════
BX, BY, BW, BH = 1.2, 11.8, W - 2.4, 1.5
rbox(BX, BY, BW, BH, C_BROWSER, C_BROWSER_B, lw=2.0)
txt(BX + 0.5, BY + 1.0, "Browser / Client", size=13,
    color=C_BROWSER_B, weight="bold", ha="left")
txt(BX + 0.5, BY + 0.55,
    "Vanilla JS  ·  Chart.js 4  ·  dashboard.html  ·  Single-page app",
    size=9.5, color=GREY2, ha="left")
pill(BX + BW - 2.0, BY + 0.95, "http://your-ip:3721", C_BROWSER_B, size=9)
pill(BX + BW - 2.0, BY + 0.48, "Port 3721", GREY2, size=8.5)

arrow_v(W / 2, BY, BY - 0.25, color=C_BROWSER_B)
txt(W / 2 + 0.3, BY - 0.12, "HTTP", size=8, color=GREY2, ha="left")

# ═══════════════════════════════════════════════════════════════════════════
# ROW 2 — FastAPI
# ═══════════════════════════════════════════════════════════════════════════
FX, FY, FW, FH = 1.2, 9.0, W - 2.4, 2.55
rbox(FX, FY, FW, FH, C_FASTAPI, C_FASTAPI_B, lw=2.0)
txt(FX + FW / 2, FY + FH - 0.38,
    "FastAPI Application  ·  backend/main.py  ·  Port 3721",
    size=12, color=C_FASTAPI_B, weight="bold")

api_data = [
    ("analytics.py",  C_ANAL_F,  C_ANAL_B,
     ["GET /api/*", "10 read-only routes", "Pre-computed data", "Serves dashboard HTML"]),
    ("ai.py",         C_AI_F,    C_AI_B,
     ["POST /api/ai/chat", "", "GPT-4o-mini chat", "with live context"]),
    ("analysis.py",   C_ANAL2_F, C_ANAL2_B,
     ["POST /api/analyze/", "custom-matrix", "POST /api/upload/", "telemetry"]),
]
api_w, api_gap = 5.6, 0.7
api_start = FX + (FW - 3 * api_w - 2 * api_gap) / 2
for i, (name, fc, ec, lines) in enumerate(api_data):
    ax_box = api_start + i * (api_w + api_gap)
    ay_box = FY + 0.22
    rbox(ax_box, ay_box, api_w, 1.75, fc, ec, lw=1.5, radius=0.2)
    txt(ax_box + api_w / 2, ay_box + 1.46, name, size=10.5,
        color=ec, weight="bold")
    divider(ax_box + 0.25, ay_box + 1.28, api_w - 0.5, color=ec)
    for j, line in enumerate(lines):
        txt(ax_box + api_w / 2, ay_box + 1.05 - j * 0.24,
            line, size=8.5, color=GREY1)

for i in range(3):
    cx = api_start + i * (api_w + api_gap) + api_w / 2
    arrow_v(cx, FY, FY - 0.25, color=C_FASTAPI_B)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 3 — Services
# ═══════════════════════════════════════════════════════════════════════════
SX, SY, SW, SH = 1.2, 6.1, W - 2.4, 2.65
rbox(SX, SY, SW, SH, C_SERVICE, C_SERVICE_B, lw=2.0)
txt(SX + SW / 2, SY + SH - 0.38,
    "Service Layer  ·  backend/services/",
    size=12, color=C_SERVICE_B, weight="bold")

svc_data = [
    ("data.py",       "#f3effe", "#8250df",
     ["Loads all 5 CSVs at startup", "dashboard_df · mttf_df · corr_df",
      "transition_df · mc_df", "rf() · valid_mttf() · is_high_risk()"]),
    ("markov.py",     C_AI_F,    C_AI_B,
     ["compute_failure_curves()", "compute_mttf()  →  N=(I−Q)⁻¹",
      "estimate_transition_matrix()", "validate_matrix()"]),
    ("ai_service.py", C_ANAL2_F, C_ANAL2_B,
     ["AzureOpenAI client (singleton)", "build_network_context()",
      "chat(messages: List[dict])", "Live snapshot → system prompt"]),
]
svc_w, svc_gap = 5.6, 0.7
svc_start = SX + (SW - 3 * svc_w - 2 * svc_gap) / 2
for i, (name, fc, ec, lines) in enumerate(svc_data):
    sx_box = svc_start + i * (svc_w + svc_gap)
    sy_box = SY + 0.22
    rbox(sx_box, sy_box, svc_w, 1.88, fc, ec, lw=1.5, radius=0.2)
    txt(sx_box + svc_w / 2, sy_box + 1.6, name, size=10.5,
        color=ec, weight="bold")
    divider(sx_box + 0.25, sy_box + 1.42, svc_w - 0.5, color=ec)
    for j, line in enumerate(lines):
        txt(sx_box + svc_w / 2, sy_box + 1.2 - j * 0.27,
            line, size=8.5, color=GREY1)

for i in range(3):
    cx = svc_start + i * (svc_w + svc_gap) + svc_w / 2
    arrow_v(cx, SY, SY - 0.25, color=C_SERVICE_B)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 4 — Data + Azure
# ═══════════════════════════════════════════════════════════════════════════
DX, DY, DW, DH = 1.2, 3.0, 11.8, 2.85
rbox(DX, DY, DW, DH, C_DATA, C_DATA_B, lw=2.0)
txt(DX + DW / 2, DY + DH - 0.4, "Data Layer  ·  data/",
    size=12, color=C_DATA_B, weight="bold")
divider(DX + 0.3, DY + DH - 0.72, DW - 0.6, color=C_DATA_B)

txt(DX + 0.5, DY + 2.0, "data/raw/", size=9.5,
    color=C_DATA_B, weight="bold", ha="left")
for j, f in enumerate(["failures.xlsx", "network_elements.xlsx",
                        "telemetry.xlsx", "transition_profiles.xlsx"]):
    txt(DX + 0.7, DY + 1.68 - j * 0.28, f"▸  {f}", size=8.5,
        color=GREY1, ha="left")

txt(DX + 6.3, DY + 2.0, "data/results/", size=9.5,
    color=C_DATA_B, weight="bold", ha="left")
for j, f in enumerate(["network_risk_dashboard.csv",
                        "element_mttf_analysis.csv",
                        "estimated_transition_matrix.csv",
                        "kpi_correlation_matrix.csv",
                        "monte_carlo_results.csv"]):
    txt(DX + 6.5, DY + 1.68 - j * 0.28, f"▸  {f}", size=8.5,
        color=GREY1, ha="left")

AX, AY, AW, AH = 13.4, 3.0, 7.4, 2.85
rbox(AX, AY, AW, AH, C_AZURE, C_AZURE_B, lw=2.0)
txt(AX + AW / 2, AY + AH - 0.4, "Azure OpenAI",
    size=12, color=C_AZURE_B, weight="bold")
divider(AX + 0.3, AY + AH - 0.72, AW - 0.6, color=C_AZURE_B)
pill(AX + AW / 2, AY + 1.92, "Model: GPT-4o-mini", C_AZURE_B, size=9)
for j, line in enumerate([
    "Network snapshot built on every request",
    "Injected as system prompt",
    "Answers grounded in live network data",
    "NOC-operator friendly plain English",
]):
    txt(AX + AW / 2, AY + 1.52 - j * 0.30, line, size=8.5, color=GREY1)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 5 — Schemas
# ═══════════════════════════════════════════════════════════════════════════
SCX, SCY, SCW, SCH = 1.2, 1.1, W - 2.4, 1.6
rbox(SCX, SCY, SCW, SCH, C_SCHEMA, C_SCHEMA_B, lw=1.6)
txt(SCX + SCW / 2, SCY + SCH - 0.32,
    "Schemas  ·  backend/schemas/requests.py",
    size=10.5, color=C_SCHEMA_B, weight="bold")
divider(SCX + 0.3, SCY + SCH - 0.58, SCW - 0.6, color=C_SCHEMA_B)

for i, (name, body) in enumerate([
    ("ChatMessage",   "{ role: str,  content: str }"),
    ("ChatRequest",   "{ messages: List[ChatMessage] }"),
    ("MatrixRequest", "{ states: List[str],  matrix: List[List[float]] }"),
]):
    x0 = SCX + 0.8 + i * (SCW / 3)
    txt(x0, SCY + 0.78, name, size=9.5, color=C_AI_B, weight="bold", ha="left")
    txt(x0, SCY + 0.42, body, size=8.0, color=GREY1, ha="left")

# ═══════════════════════════════════════════════════════════════════════════
# TECH STACK BADGES
# ═══════════════════════════════════════════════════════════════════════════
badges = [
    ("Python 3.11+", "#3b7bc8"), ("FastAPI", "#1a7f37"),
    ("NumPy",        "#4b5563"), ("Pandas",  "#150458"),
    ("Azure OpenAI", "#0078d4"), ("Chart.js","#c9303e"),
    ("Uvicorn",      "#2f9560"), ("python-dotenv", "#57606a"),
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
plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG_PAGE)
print(f"Saved → {out}")
