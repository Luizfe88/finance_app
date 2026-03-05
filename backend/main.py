"""
FastAPI Application Factory (v2 — Institutional Grade)

Clean Architecture entry point:
- Creates and configures the FastAPI app
- Registers all routers (v1 + v2)
- Injects dependencies
- Creates database tables on startup
- Configures CORS for frontend consumption
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

from infrastructure.db.database import create_all_tables
from interfaces.api.routers import transactions, import_data, accounts
from interfaces.api.routers.dashboard import router as dashboard_router
from interfaces.api.routers.budget import router as budget_router
from interfaces.api.routers.installments import router as installments_router
from interfaces.api.routers.subscriptions import router as subscriptions_router
from interfaces.api.routers.audit import router as audit_router

# ── CORS origins ──────────────────────────────────────────────────────────────
_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
)
CORS_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (idempotent — safe in development)."""
    await create_all_tables()
    yield


# ── App factory ───────────────────────────────────────────────────────────────
def create_app() -> FastAPI:
    app = FastAPI(
        title="Finance App API — Institutional Grade",
        description=(
            "Personal Finance Management API — Grau Institucional\n\n"
            "**Features v2:**\n"
            "- Zero-Based Budgeting (ZBB) with envelope allocation engine\n"
            "- Double-Entry Bookkeeping (double-entry journal)\n"
            "- Credit Card Liquidity Reserve (FUNDED/UNFUNDED state machine)\n"
            "- Normalized installment groups (parent/child transactions)\n"
            "- Subscription billing engine (Observer + Strategy patterns)\n"
            "- Idempotent Open Finance import (SHA-256 deduplication)\n"
            "- Immutable tamper-evident audit trail (SHA-256 checksums)\n"
            "- LGPD compliance: right to erasure, field-level AES-256 encryption\n"
            "- Institutional dashboard with contextual benchmarks + projections\n"
        ),
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API prefix ────────────────────────────────────────────────────────────
    prefix = os.getenv("API_PREFIX", "/api/v1")

    # ── V1 Routers (backward compatible) ─────────────────────────────────────
    app.include_router(transactions.router, prefix=prefix)
    app.include_router(import_data.router, prefix=prefix)
    app.include_router(accounts.router, prefix=prefix)

    # ── V2 Routers (Institutional Grade) ─────────────────────────────────────
    app.include_router(dashboard_router, prefix=prefix)         # /dashboard + /dashboard/v2
    app.include_router(budget_router, prefix=prefix)            # /budget/*
    app.include_router(installments_router, prefix=prefix)      # /installments/*
    app.include_router(subscriptions_router, prefix=prefix)     # /subscriptions/*
    app.include_router(audit_router, prefix=prefix)             # /audit/*

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"])
    async def health():
        return {
            "status": "ok",
            "version": "2.0.0",
            "features": ["zbb", "double-entry", "installments", "subscriptions", "audit", "lgpd"],
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
