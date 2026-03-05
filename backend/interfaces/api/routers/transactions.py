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
from infrastructure.db.account_repository import SQLAlchemyAccountRepository
from application.use_cases.list_transactions import ListTransactionsUseCase, ListTransactionsInput
from application.use_cases.create_transaction import CreateTransactionUseCase, CreateTransactionInput
from application.use_cases.process_installment_purchase import ProcessInstallmentPurchaseUseCase
from application.use_cases.execute_payment import ExecutePaymentUseCase
from application.use_cases.create_transfer import CreateTransferUseCase, CreateTransferInput
from domain.entities.transaction import Transaction, TransactionType, PaymentMethod
from interfaces.api.schemas.transaction_schemas import (
    TransactionOut,
    TransactionCreate,
    TransferCreate,
    PaginatedTransactions,
)

router = APIRouter(prefix="/transactions", tags=["Transactions"])

# Demo user ID (replace with JWT auth in production)
from interfaces.api.dependencies.auth import get_current_user_id


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
        payment_method=t.payment_method.value,
        is_recurring=t.is_recurring,
        role=t.role.value,
        installment_seq=t.installment_seq,
        installment_total=t.installment_total,
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
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
) :
    """
    List transactions with filtering and pagination.
    Returns chart-ready metadata alongside items.
    """
    repo = SQLAlchemyTransactionRepository(session)
    use_case = ListTransactionsUseCase(repo)
    result = await use_case.execute(ListTransactionsInput(
        user_id=user_id,
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
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Manually create a single transaction or installments."""
    txn_repo = SQLAlchemyTransactionRepository(session)
    acc_repo = SQLAlchemyAccountRepository(session)
    
    # Setup use cases
    installment_use_case = ProcessInstallmentPurchaseUseCase(txn_repo, acc_repo)
    create_use_case = CreateTransactionUseCase(txn_repo, installment_use_case)
    
    # Execute
    result = await create_use_case.execute(CreateTransactionInput(
        user_id=user_id,
        account_id=body.account_id,
        amount=Decimal(str(body.amount)),
        description=body.description,
        category=body.category,
        date=body.date,
        transaction_type=TransactionType(body.transaction_type),
        payment_method=PaymentMethod(body.payment_method),
        envelope_id=body.envelope_id,
        memo=body.memo,
        is_recurring=body.is_recurring,
        is_paid=body.is_paid,
        recurrence_rule=body.recurrence_rule,
        installment_count=body.installment_count
    ))
    
    # Return the first transaction
    return _entity_to_out(result.transactions[0])


@router.delete("/{transaction_id}", status_code=204, summary="Delete a transaction")
async def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Delete a transaction by ID."""
    repo = SQLAlchemyTransactionRepository(session)
    deleted = await repo.delete(transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")


@router.post("/{transaction_id}/execute", response_model=TransactionOut, summary="Execute a pending payment")
async def execute_payment(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Transition a PENDING transaction to POSTED."""
    repo = SQLAlchemyTransactionRepository(session)
    use_case = ExecutePaymentUseCase(repo)
    try:
        result = await use_case.execute(transaction_id)
        return _entity_to_out(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/transfer", response_model=list[TransactionOut], summary="Create a transfer between accounts")
async def create_transfer(
    body: TransferCreate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Create a linked debit and credit for inter-account transfer."""
    repo = SQLAlchemyTransactionRepository(session)
    use_case = CreateTransferUseCase(repo)
    result = await use_case.execute(CreateTransferInput(
        user_id=user_id,
        from_account_id=body.from_account_id,
        to_account_id=body.to_account_id,
        amount=Decimal(str(body.amount)),
        date=body.date,
        description=body.description,
        category=body.category,
        memo=body.memo
    ))
    return [_entity_to_out(t) for t in result.transactions]
