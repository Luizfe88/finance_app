"""
Use Case: CreateTransactionUseCase

A unified entry point for creating any type of transaction:
- Simple Expense (DEBIT)
- Simple Revenue (CREDIT)
- Installment Purchase (delegates to ProcessInstallmentPurchaseUseCase)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from domain.entities.transaction import Transaction, TransactionType, TransactionStatus, PaymentMethod
from application.protocols.transaction_repository import TransactionRepository
from application.use_cases.process_installment_purchase import (
    ProcessInstallmentPurchaseUseCase,
    InstallmentPurchaseInput
)


@dataclass
class CreateTransactionInput:
    user_id: str
    account_id: str
    amount: Decimal
    description: str
    category: str
    date: datetime
    transaction_type: TransactionType
    payment_method: PaymentMethod = PaymentMethod.CASH_PIX
    envelope_id: Optional[str] = None
    memo: Optional[str] = None
    is_recurring: bool = False
    is_paid: bool = True
    recurrence_rule: Optional[str] = None
    installment_count: int = 1  # If > 1, triggers installment logic


@dataclass
class CreateTransactionOutput:
    transactions: List[Transaction]


class CreateTransactionUseCase:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        installment_use_case: ProcessInstallmentPurchaseUseCase
    ) -> None:
        self._transaction_repo = transaction_repo
        self._installment_use_case = installment_use_case

    async def execute(self, inp: CreateTransactionInput) -> CreateTransactionOutput:
        # If it's a credit card installment purchase
        if inp.installment_count > 1 and inp.payment_method == PaymentMethod.CREDIT_CARD:
            res = await self._installment_use_case.execute(
                InstallmentPurchaseInput(
                    user_id=inp.user_id,
                    account_id=inp.account_id,
                    amount=inp.amount,
                    description=inp.description,
                    category=inp.category,
                    installment_count=inp.installment_count,
                    purchase_date=inp.date,
                    payment_method=inp.payment_method,
                    envelope_id=inp.envelope_id,
                    memo=inp.memo
                )
            )
            return CreateTransactionOutput(transactions=res.transactions)

        # Otherwise, it's a standalone transaction
        txn = Transaction(
            user_id=inp.user_id,
            account_id=inp.account_id,
            amount=inp.amount,
            description=inp.description,
            category=inp.category,
            date=inp.date,
            transaction_type=inp.transaction_type,
            status=TransactionStatus.POSTED if inp.is_paid else TransactionStatus.PENDING,
            payment_method=inp.payment_method,
            envelope_id=inp.envelope_id,
            memo=inp.memo,
            is_recurring=inp.is_recurring,
            recurrence_rule=inp.recurrence_rule
        )

        saved = await self._transaction_repo.save(txn)
        return CreateTransactionOutput(transactions=[saved])
