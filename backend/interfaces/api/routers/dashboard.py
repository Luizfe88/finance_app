"""
API Router: Dashboard V2 (Institutional Grade)

GET /dashboard/v2 → Full institutional payload (inverted pyramid)

The response is structured for direct consumption by the React frontend
with no additional transformation needed:
  - KPI cards with contextual benchmarks (vs historical avg)
  - Cash flow projection (3 historical + 3 projected months)
  - Envelope health (ZBB status)
  - Upcoming commitments (installments + subscriptions)
  - Recent transactions

Also exposes the original v1 endpoint for backward compatibility.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.get_dashboard import GetDashboardUseCase
from application.use_cases.get_dashboard_v2 import GetDashboardV2UseCase
from infrastructure.db.database import get_session
from infrastructure.db.transaction_repository import SQLAlchemyTransactionRepository
from infrastructure.db.repositories_v2 import (
    SQLAlchemyEnvelopeRepository,
    SQLAlchemySubscriptionRepository,
    SQLAlchemyInstallmentRepository,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
from interfaces.api.dependencies.auth import get_current_user_id


@router.get("")
async def get_dashboard(
    months_back: int = Query(default=6, ge=1, le=24),
    account_id: Optional[str] = Query(default=None),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Dashboard v1 — backward compatible (reactive tracking)."""
    repo = SQLAlchemyTransactionRepository(session)
    use_case = GetDashboardUseCase(repository=repo)
    result = await use_case.execute(
        user_id=user_id,
        account_id=account_id,
        months_back=months_back,
    )
    return {
        "summary": {
            "total_balance": result.summary.total_balance,
            "total_income": result.summary.total_income,
            "total_expenses": result.summary.total_expenses,
            "savings_rate": result.summary.savings_rate,
        },
        "transaction_count": result.summary.transaction_count,
        "monthly_cash_flow": [
            {"month": m.month, "income": m.income, "expenses": m.expenses, "balance": m.balance}
            for m in result.monthly_cash_flow
        ],
        "category_breakdown": [
            {"category": c.category, "amount": c.amount, "percentage": c.percentage, "color": c.color}
            for c in result.category_breakdown
        ],
        "recent_transactions": [
            {
                "id": t.id, "description": t.description, "amount": float(t.amount),
                "date": t.date.isoformat(), "category": t.category,
                "transaction_type": t.transaction_type.value,
            }
            for t in result.recent_transactions
        ],
        "period_start": result.period_start,
        "period_end": result.period_end,
    }


@router.get("/v2")
async def get_dashboard_v2(
    month: Optional[str] = Query(
        default=None,
        description="Target month (YYYY-MM). Defaults to current month.",
        regex=r"^\d{4}-\d{2}$"
    ),
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """
    Dashboard v2 — Institutional grade, inverted pyramid layout.

    Returns:
      - KPI cards with contextual benchmarks (vs 6-month avg)
      - 9-point cash flow projection (6 historical + 3 projected)
      - Envelope health (ZBB status per budget category)
      - Upcoming commitments (installments + subscriptions, 30 days)
      - Recent 10 transactions
    """
    txn_repo = SQLAlchemyTransactionRepository(session)
    env_repo = SQLAlchemyEnvelopeRepository(session)
    sub_repo = SQLAlchemySubscriptionRepository(session)
    inst_repo = SQLAlchemyInstallmentRepository(session)

    use_case = GetDashboardV2UseCase(
        transactions=txn_repo,
        envelopes=env_repo,
        subscriptions=sub_repo,
        installments=inst_repo,
    )
    result = await use_case.execute(
        user_id=user_id,
        target_month=month,
    )

    def kpi_to_dict(k):
        return {
            "label": k.label, "value": k.value, "formatted": k.formatted,
            "vs_avg_pct": k.vs_avg_pct, "trend": k.trend,
            "alert": k.alert, "alert_message": k.alert_message,
        }

    return {
        "kpis": {
            "ready_to_assign": kpi_to_dict(result.ready_to_assign),
            "net_worth": kpi_to_dict(result.net_worth),
            "savings_rate": kpi_to_dict(result.savings_rate),
            "total_income": kpi_to_dict(result.total_income),
            "total_expenses": kpi_to_dict(result.total_expenses),
        },
        "cash_flow_projection": [
            {
                "month": d.month, "income": d.income, "expenses": d.expenses,
                "balance": d.balance, "is_projected": d.is_projected,
            }
            for d in result.cash_flow_projection
        ],
        "envelope_health": [
            {
                "id": e.id, "name": e.name, "icon": e.icon, "color": e.color,
                "allocated": e.allocated, "spent": e.spent, "available": e.available,
                "utilization_pct": e.utilization_pct,
                "is_overspent": e.is_overspent, "is_system": e.is_system,
            }
            for e in result.envelope_health
        ],
        "upcoming_commitments": [
            {
                "id": c.id, "label": c.label, "amount": c.amount,
                "due_date": c.due_date, "commitment_type": c.commitment_type,
                "is_overdue": c.is_overdue,
            }
            for c in result.upcoming_commitments
        ],
        "recent_transactions": [
            {
                "id": t.id, "description": t.description, "amount": float(t.amount),
                "date": t.date.isoformat(), "category": t.category,
                "transaction_type": t.transaction_type.value,
                "funding_state": t.funding_state.value,
                "installment_label": t.installment_label,
            }
            for t in result.recent_transactions
        ],
        "meta": {
            "period_month": result.period_month,
            "generated_at": result.generated_at,
        },
    }
