"""
API Router: Installments

Endpoints:
  POST /installments              → create an installment group
  GET  /installments              → list active installment groups
  GET  /installments/{id}         → single group + children
  POST /installments/{id}/cancel  → cancel a group
  GET  /installments/projection   → 6-month cash flow impact
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.repositories_v2 import SQLAlchemyInstallmentRepository, SQLAlchemyAuditRepository
from infrastructure.db.transaction_repository import SQLAlchemyTransactionRepository
from domain.entities.installment_group import InstallmentGroup
from application.use_cases.create_installment_group import (
    CreateInstallmentGroupUseCase, CreateInstallmentInput,
)

router = APIRouter(prefix="/installments", tags=["Installments"])
from interfaces.api.dependencies.auth import get_current_user_id


class InstallmentCreateRequest(BaseModel):
    account_id: str
    envelope_id: str
    description: str
    total_amount: Decimal
    installment_count: int
    start_date: str   # ISO date string "YYYY-MM-DD"
    merchant: Optional[str] = None
    category: str = "Outros"


class InstallmentGroupResponse(BaseModel):
    id: str
    description: str
    merchant: Optional[str]
    total_amount: float
    installment_amount: float
    installment_count: int
    start_date: str
    status: str
    envelope_id: str
    account_id: str


def _group_to_response(g: InstallmentGroup) -> InstallmentGroupResponse:
    return InstallmentGroupResponse(
        id=g.id, description=g.description, merchant=g.merchant,
        total_amount=float(g.total_amount),
        installment_amount=float(g.installment_amount),
        installment_count=g.installment_count,
        start_date=g.start_date.strftime("%Y-%m-%d"),
        status=g.status.value, envelope_id=g.envelope_id, account_id=g.account_id,
    )


@router.post("", response_model=dict, status_code=201)
async def create_installment(
    body: InstallmentCreateRequest,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a normalized installment group with N child transactions."""
    txn_repo = SQLAlchemyTransactionRepository(session)
    inst_repo = SQLAlchemyInstallmentRepository(session)
    audit_repo = SQLAlchemyAuditRepository(session)

    use_case = CreateInstallmentGroupUseCase(
        transactions=txn_repo,
        installments=inst_repo,
        audit=audit_repo,
    )
    try:
        start_date = datetime.strptime(body.start_date, "%Y-%m-%d")
        result = await use_case.execute(CreateInstallmentInput(
            user_id=user_id,
            account_id=body.account_id,
            envelope_id=body.envelope_id,
            description=body.description,
            total_amount=body.total_amount,
            installment_count=body.installment_count,
            start_date=start_date,
            merchant=body.merchant,
            category=body.category,
        ))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "group": _group_to_response(result.group),
        "installments_created": len(result.installments),
        "installment_ids": [t.id for t in result.installments],
    }


@router.get("", response_model=list[InstallmentGroupResponse])
async def list_installments(user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)):
    """List all active installment groups for the current user."""
    repo = SQLAlchemyInstallmentRepository(session)
    groups = await repo.list_active_by_user(user_id=user_id)
    return [_group_to_response(g) for g in groups]


@router.get("/projection")
async def get_installment_projection(user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)):
    """Calculate monthly cash flow impact of all active installments (6 months forward)."""
    from dateutil.relativedelta import relativedelta
    from collections import defaultdict

    repo = SQLAlchemyInstallmentRepository(session)
    groups = await repo.list_active_by_user(user_id=user_id)

    now = datetime.utcnow()
    monthly_impact: dict[str, float] = defaultdict(float)

    for grp in groups:
        for seq in range(1, grp.installment_count + 1):
            due = grp.start_date + relativedelta(months=seq - 1)
            if due >= now:
                mk = due.strftime("%Y-%m")
                monthly_impact[mk] += float(grp.installment_amount)

    # Build 6-month projection table
    months = [(now + relativedelta(months=i)).strftime("%Y-%m") for i in range(7)]
    projection = [
        {
            "month": m,
            "committed_amount": monthly_impact.get(m, 0.0),
            "is_current_month": m == now.strftime("%Y-%m"),
        }
        for m in months
    ]
    return {
        "projection": projection,
        "total_active_groups": len(groups),
        "generated_at": now.isoformat(),
    }


@router.post("/{group_id}/cancel")
async def cancel_installment(
    group_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Cancel an installment group (marks it as CANCELLED)."""
    repo = SQLAlchemyInstallmentRepository(session)
    group = await repo.find_by_id(group_id)
    if not group or group.user_id != user_id:
        raise HTTPException(status_code=404, detail="Installment group not found.")
    group.cancel()
    await repo.save(group)
    return {"status": "cancelled", "group_id": group_id}
