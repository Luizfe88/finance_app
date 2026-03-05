"""
API Router: Budget / Envelopes (ZBB)

Endpoints:
  GET  /budget/envelopes           → list envelopes for a month
  POST /budget/envelopes           → create envelope
  POST /budget/allocate            → move funds between envelopes
  GET  /budget/ready-to-assign     → current PRA balance
  POST /budget/ensure-system       → bootstrap system envelopes for a month
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.repositories_v2 import SQLAlchemyEnvelopeRepository, SQLAlchemyJournalRepository, SQLAlchemyAuditRepository
from domain.entities.budget_envelope import BudgetEnvelope, SystemEnvelope
from application.use_cases.allocate_funds import AllocateFundsUseCase, AllocateFundsInput

router = APIRouter(prefix="/budget", tags=["Budget (ZBB)"])

# ── Temporary auth stub (replace with JWT in production) ──────────────────────
from interfaces.api.dependencies.auth import get_current_user_id


# ── Pydantic Schemas ───────────────────────────────────────────────────────────
class EnvelopeCreate(BaseModel):
    name: str
    icon: str = "📦"
    color: str = "#6366F1"
    month: str = Field(default_factory=lambda: datetime.utcnow().strftime("%Y-%m"))
    allocated: Decimal = Decimal("0.00")


class EnvelopeResponse(BaseModel):
    id: str
    name: str
    icon: str
    color: str
    month: str
    allocated: float
    spent: float
    available: float
    utilization_pct: float
    is_overspent: bool
    is_system: bool


class AllocateRequest(BaseModel):
    source_envelope_id: str
    target_envelope_id: str
    amount: Decimal
    note: str = ""


class AllocateResponse(BaseModel):
    source_envelope: EnvelopeResponse
    target_envelope: EnvelopeResponse
    journal_entry_id: str


def _env_to_response(e: BudgetEnvelope) -> EnvelopeResponse:
    return EnvelopeResponse(
        id=e.id, name=e.name, icon=e.icon, color=e.color, month=e.month,
        allocated=float(e.allocated), spent=float(e.spent),
        available=float(e.available),
        utilization_pct=round(e.utilization_pct, 1),
        is_overspent=e.is_overspent, is_system=e.is_system,
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("/envelopes", response_model=list[EnvelopeResponse])
async def list_envelopes(
    month: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """List all budget envelopes for a given month (YYYY-MM). Defaults to current month."""
    month = month or datetime.utcnow().strftime("%Y-%m")
    repo = SQLAlchemyEnvelopeRepository(session)
    envelopes = await repo.list_by_user_month(user_id=user_id, month=month)
    return [_env_to_response(e) for e in envelopes]


@router.post("/envelopes", response_model=EnvelopeResponse, status_code=201)
async def create_envelope(
    body: EnvelopeCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a new budget envelope for a month."""
    repo = SQLAlchemyEnvelopeRepository(session)
    env = BudgetEnvelope(
        user_id=user_id,
        name=body.name, icon=body.icon, color=body.color,
        month=body.month, allocated=body.allocated,
    )
    saved = await repo.save(env)
    return _env_to_response(saved)


@router.post("/allocate", response_model=AllocateResponse)
async def allocate_funds(
    body: AllocateRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Move funds from one envelope to another (e.g., Pronto para Atribuir → Alimentação)."""
    envelope_repo = SQLAlchemyEnvelopeRepository(session)
    journal_repo = SQLAlchemyJournalRepository(session)
    audit_repo = SQLAlchemyAuditRepository(session)

    use_case = AllocateFundsUseCase(
        envelopes=envelope_repo,
        journal=journal_repo,
        audit=audit_repo,
    )
    try:
        result = await use_case.execute(AllocateFundsInput(
            user_id=user_id,
            source_envelope_id=body.source_envelope_id,
            target_envelope_id=body.target_envelope_id,
            amount=body.amount,
            note=body.note,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AllocateResponse(
        source_envelope=_env_to_response(result.source_envelope),
        target_envelope=_env_to_response(result.target_envelope),
        journal_entry_id=result.journal_entry.id,
    )


@router.get("/ready-to-assign")
async def get_ready_to_assign(
    month: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Get the current Pronto para Atribuir balance — the ZBB control metric."""
    month = month or datetime.utcnow().strftime("%Y-%m")
    repo = SQLAlchemyEnvelopeRepository(session)
    env = await repo.find_by_name_and_month(
        user_id=user_id,
        name=SystemEnvelope.READY_TO_ASSIGN,
        month=month,
    )
    if not env:
        return {"month": month, "available": 0.0, "needs_action": False}
    return {
        "month": month,
        "available": float(env.available),
        "needs_action": env.available > Decimal("0"),
        "message": "Você tem fundos não alocados — atribua-os a categorias!" if env.available > 0 else "Todos os fundos foram alocados. ✓",
    }


@router.post("/ensure-system")
async def ensure_system_envelopes(
    month: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Bootstrap system envelopes (Pronto para Atribuir, Pagamento CC) for a month."""
    month = month or datetime.utcnow().strftime("%Y-%m")
    repo = SQLAlchemyEnvelopeRepository(session)
    created = await repo.ensure_system_envelopes(user_id=user_id, month=month)
    return {
        "month": month,
        "created_count": len(created),
        "created": [_env_to_response(e) for e in created],
    }
