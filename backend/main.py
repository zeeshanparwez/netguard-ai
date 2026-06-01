"""
Application factory — creates the FastAPI app, wires up middleware,
and registers all routers.

Nothing domain-specific lives here; this file is pure assembly.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import ai, analytics, analysis

app = FastAPI(
    title="NetGuard AI API",
    description="Predictive Network Intelligence Platform — Markov Chain + LLM Analytics",
    version="2.0.0",
)

# Allow any origin during development; tighten this to specific domains in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — order matters for OpenAPI docs grouping
app.include_router(analytics.router)   # GET  / + /api/*  (pre-computed data)
app.include_router(ai.router)          # POST /api/ai/chat
app.include_router(analysis.router)    # POST /api/analyze/* + /api/upload/*
