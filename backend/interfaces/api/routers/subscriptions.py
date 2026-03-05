"""
API Router: Subscriptions (Billing Engine)

Endpoints:
  GET  /subscriptions             → list all subscriptions
  POST /subscriptions             → create subscription
  PATCH /subscriptions/{id}       → update subscription
  DELETE /subscriptions/{id}      → cancel subscription
  POST /subscriptions/run-billing → trigger billing engine (for cron/manual run)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.repositories_v2 import (
    SQLAlchemySubscriptionRepository, SQLAlchemyAuditRepository,
)
from infrastructure.db.transaction_repository import SQLAlchemyTransactionRepository
from domain.entities.subscription import Subscription, PaymentMethod, SubscriptionStatus
from application.use_cases.billing_engine import BillingEngineService

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
DEFAULT_USER_ID = "demo-user"


class SubscriptionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    amount: Decimal
    payment_method: str = "CREDIT_CARD"
    account_id: Optional[str] = None
    envelope_id: str
    billing_day: int = 1


class SubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[str] = None
    envelope_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    amount: float
    payment_method: str
    envelope_id: str
    billing_day: int
    next_billing_date: str
    status: str
    is_upcoming: bool
    is_overdue: bool


def _sub_to_response(s: Subscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        id=s.id, name=s.name, description=s.description,
        amount=float(s.amount), payment_method=s.payment_method.value,
        envelope_id=s.envelope_id, billing_day=s.billing_day,
        next_billing_date=s.next_billing_date.strftime("%Y-%m-%d"),
        status=s.status.value, is_upcoming=s.is_upcoming, is_overdue=s.is_overdue,
    )


def _compute_next_billing(billing_day: int) -> datetime:
    """Compute next billing date from billing day of month."""
    now = datetime.utcnow()
    try:
        candidate = now.replace(day=billing_day)
    except ValueError:
        candidate = now.replace(day=28)  # Clamp for shorter months
    if candidate <= now:
        from dateutil.relativedelta import relativedelta
        candidate = candidate + relativedelta(months=1)
    return candidate


@router.get("", response_model=list[SubscriptionResponse])
async def list_subscriptions(session: AsyncSession = Depends(get_session)):
    repo = SQLAlchemySubscriptionRepository(session)
    subs = await repo.list_by_user(user_id=DEFAULT_USER_ID)
    return [_sub_to_response(s) for s in subs]


@router.post("", response_model=SubscriptionResponse, status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    session: AsyncSession = Depends(get_session),
):
    try:
        method = PaymentMethod(body.payment_method)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid payment_method: {body.payment_method}")

    sub = Subscription(
        user_id=DEFAULT_USER_ID,
        name=body.name, description=body.description,
        amount=body.amount, payment_method=method,
        account_id=body.account_id, envelope_id=body.envelope_id,
        billing_day=body.billing_day,
        next_billing_date=_compute_next_billing(body.billing_day),
    )
    repo = SQLAlchemySubscriptionRepository(session)
    saved = await repo.save(sub)
    return _sub_to_response(saved)


@router.patch("/{sub_id}", response_model=SubscriptionResponse)
async def update_subscription(
    sub_id: str,
    body: SubscriptionUpdate,
    session: AsyncSession = Depends(get_session),
):
    repo = SQLAlchemySubscriptionRepository(session)
    sub = await repo.find_by_id(sub_id)
    if not sub or sub.user_id != DEFAULT_USER_ID:
        raise HTTPException(status_code=404, detail="Subscription not found.")

    if body.name:
        sub.name = body.name
    if body.amount:
        sub.amount = body.amount
    if body.envelope_id:
        sub.envelope_id = body.envelope_id
    if body.status:
        try:
            sub.status = SubscriptionStatus(body.status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {body.status}")

    saved = await repo.save(sub)
    return _sub_to_response(saved)


@router.delete("/{sub_id}", status_code=204)
async def cancel_subscription(
    sub_id: str,
    session: AsyncSession = Depends(get_session),
):
    repo = SQLAlchemySubscriptionRepository(session)
    sub = await repo.find_by_id(sub_id)
    if not sub or sub.user_id != DEFAULT_USER_ID:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    sub.cancel()
    await repo.save(sub)


@router.post("/run-billing")
async def run_billing_engine(
    dry_run: bool = False,
    session: AsyncSession = Depends(get_session),
):
    """
    Trigger the billing engine for the current user.
    dry_run=true: only returns upcoming/overdue, does not process.
    """
    sub_repo = SQLAlchemySubscriptionRepository(session)
    txn_repo = SQLAlchemyTransactionRepository(session)
    audit_repo = SQLAlchemyAuditRepository(session)

    engine = BillingEngineService(
        subscriptions=sub_repo,
        transactions=txn_repo,
        audit=audit_repo,
    )
    result = await engine.run(user_id=DEFAULT_USER_ID, process_due=not dry_run)

    return {
        "dry_run": dry_run,
        "processed_count": len(result.processed),
        "upcoming_count": len(result.skipped_upcoming),
        "overdue_count": len(result.skipped_overdue),
        "processed": [
            {"subscription_name": s.name, "amount": float(s.amount), "transaction_id": t.id}
            for s, t in result.processed
        ],
        "upcoming": [_sub_to_response(s) for s in result.skipped_upcoming],
    }
