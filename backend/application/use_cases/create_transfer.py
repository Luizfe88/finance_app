"""
Use Case: CreateTransferUseCase

Creates two linked transactions: a DEBIT from source and a CREDIT to destination.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from domain.entities.transaction import Transaction, TransactionType, TransactionStatus, PaymentMethod
from application.protocols.transaction_repository import TransactionRepository


@dataclass
class CreateTransferInput:
    user_id: str
    from_account_id: str
    to_account_id: str
    amount: Decimal
    date: datetime
    description: str = "Transferência"
    category: str = "Outros"
    memo: Optional[str] = None


@dataclass
class CreateTransferOutput:
    transactions: List[Transaction]


class CreateTransferUseCase:
    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    async def execute(self, inp: CreateTransferInput) -> CreateTransferOutput:
        # 1. Create Debit Transaction
        debit_txn = Transaction(
            user_id=inp.user_id,
            account_id=inp.from_account_id,
            amount=inp.amount,
            description=f"{inp.description} (Saída)",
            category=inp.category,
            date=inp.date,
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.POSTED,
            payment_method=PaymentMethod.CASH_PIX,
            memo=inp.memo
        )
        
        # 2. Create Credit Transaction
        credit_txn = Transaction(
            user_id=inp.user_id,
            account_id=inp.to_account_id,
            amount=inp.amount,
            description=f"{inp.description} (Entrada)",
            category=inp.category,
            date=inp.date,
            transaction_type=TransactionType.CREDIT,
            status=TransactionStatus.POSTED,
            payment_method=PaymentMethod.CASH_PIX,
            memo=inp.memo
        )
        
        # Save both
        saved_debit = await self._repository.save(debit_txn)
        saved_credit = await self._repository.save(credit_txn)
        
        return CreateTransferOutput(transactions=[saved_debit, saved_credit])
