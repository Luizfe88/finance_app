"""
FastAPI Router: Transactions

CRUD endpoints for financial transactions.
User identity is simplified (passed as query param) for this demo.
In production, use JWT authentication middleware.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.transaction_repository import SQLAlchemyTransactionRepository
from application.use_cases.list_transactions import ListTransactionsUseCase, ListTransactionsInput
from domain.entities.transaction import Transaction, TransactionType
from interfaces.api.schemas.transaction_schemas import (
    TransactionOut,
    TransactionCreate,
    PaginatedTransactions,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Demo user ID (replace with JWT auth in production)
DEMO_USER_ID = "demo-user-001"


def _entity_to_out(t: Transaction) -> TransactionOut:
    return TransactionOut(
        id=t.id,
        user_id=t.user_id,
        account_id=t.account_id,
        amount=float(t.amount),
        currency=t.currency,
        description=t.description,
        category=t.category,
        date=t.date,
        transaction_type=t.transaction_type.value,
        status=t.status.value,
        memo=t.memo,
        payee=t.payee,
        created_at=t.created_at,
    )


@router.get("", response_model=PaginatedTransactions, summary="List transactions")
async def list_transactions(
    account_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """
    List transactions with filtering and pagination.
    Returns chart-ready metadata alongside items.
    """
    repo = SQLAlchemyTransactionRepository(session)
    use_case = ListTransactionsUseCase(repo)
    result = await use_case.execute(ListTransactionsInput(
        user_id=DEMO_USER_ID,
        account_id=account_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    ))
    return PaginatedTransactions(
        items=[_entity_to_out(t) for t in result.transactions],
        total=result.total,
        limit=result.limit,
        offset=result.offset,
        has_more=result.has_more,
    )


@router.post("", response_model=TransactionOut, status_code=201, summary="Create a transaction")
async def create_transaction(
    body: TransactionCreate,
    session: AsyncSession = Depends(get_session),
):
    """Manually create a single transaction."""
    repo = SQLAlchemyTransactionRepository(session)
    transaction = Transaction(
        user_id=DEMO_USER_ID,
        account_id=body.account_id,
        amount=Decimal(str(body.amount)),
        currency=body.currency,
        description=body.description,
        category=body.category,
        date=body.date,
        transaction_type=TransactionType(body.transaction_type),
        memo=body.memo,
        payee=body.payee,
    )
    saved = await repo.save(transaction)
    return _entity_to_out(saved)


@router.delete("/{transaction_id}", status_code=204, summary="Delete a transaction")
async def delete_transaction(
    transaction_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a transaction by ID."""
    repo = SQLAlchemyTransactionRepository(session)
    deleted = await repo.delete(transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
