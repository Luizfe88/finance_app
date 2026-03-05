"""
Use Case: ExecutePaymentUseCase

Transitions a PENDING transaction to POSTED.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from domain.entities.transaction import Transaction, TransactionStatus
from application.protocols.transaction_repository import TransactionRepository


class ExecutePaymentUseCase:
    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    async def execute(self, transaction_id: str, payment_date: Optional[datetime] = None) -> Transaction:
        txn = await self._repository.find_by_id(transaction_id)
        if not txn:
            raise ValueError("Transaction not found")
        
        if txn.status == TransactionStatus.POSTED:
            return txn
            
        txn.status = TransactionStatus.POSTED
        if payment_date:
            txn.date = payment_date
        else:
            txn.date = datetime.utcnow()
            
        txn.updated_at = datetime.utcnow()
        return await self._repository.save(txn)
