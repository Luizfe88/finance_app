"""
Use Case: ProcessInstallmentPurchaseUseCase

Handles the creation of a purchase split into N installments on a credit card.
Implements 'Smart Invoice Recognition':
- Based on the account's closing and due days, determines the correct due date for the first installment.
- Generates N child transactions linked by an InstallmentGroup.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from dateutil.relativedelta import relativedelta

from domain.entities.transaction import Transaction, TransactionType, TransactionRole, FundingState, PaymentMethod
from domain.entities.installment_group import InstallmentGroup
from application.protocols.transaction_repository import TransactionRepository
from application.protocols.account_repository import AccountRepository


@dataclass
class InstallmentPurchaseInput:
    user_id: str
    account_id: str
    amount: Decimal
    description: str
    category: str
    installment_count: int
    purchase_date: datetime
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    envelope_id: Optional[str] = None
    memo: Optional[str] = None


@dataclass
class InstallmentPurchaseOutput:
    installment_group: InstallmentGroup
    transactions: List[Transaction]


class ProcessInstallmentPurchaseUseCase:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        account_repo: AccountRepository,
    ) -> None:
        self._transaction_repo = transaction_repo
        self._account_repo = account_repo

    async def execute(self, inp: InstallmentPurchaseInput) -> InstallmentPurchaseOutput:
        if inp.installment_count < 1:
            raise ValueError("Installment count must be at least 1.")

        # 1. Verify Account
        account = await self._account_repo.find_by_id(inp.account_id)
        if not account:
            raise ValueError(f"Account {inp.account_id} not found.")

        # 2. Determine first installment due date (Smart Invoice Logic)
        first_due_date = self._calculate_first_due_date(
            purchase_date=inp.purchase_date.date(),
            due_day=account.invoice_due_day or 10,  # Default to 10 if not set
            closing_day=account.invoice_closing_day or 3,  # Default to 3 if not set
        )

        # 3. Create InstallmentGroup
        group = InstallmentGroup(
            user_id=inp.user_id,
            account_id=inp.account_id,
            envelope_id=inp.envelope_id or "",
            description=inp.description,
            total_amount=inp.amount,
            installment_count=inp.installment_count,
            start_date=inp.purchase_date,
        )

        # 4. Generate Transactions
        transactions: List[Transaction] = []
        per_installment = group.installment_amount
        
        # Handle rounding diff on last installment
        total_sum = Decimal("0.00")

        for i in range(1, inp.installment_count + 1):
            installment_date = first_due_date + relativedelta(months=i-1)
            
            # For the last installment, adjust for rounding
            if i == inp.installment_count:
                current_amount = inp.amount - total_sum
            else:
                current_amount = per_installment
                total_sum += current_amount

            txn = Transaction(
                user_id=inp.user_id,
                account_id=inp.account_id,
                amount=current_amount,
                description=f"{inp.description} ({i}/{inp.installment_count})",
                category=inp.category,
                date=datetime.combine(installment_date, datetime.min.time()),
                transaction_type=TransactionType.DEBIT,
                payment_method=inp.payment_method,
                envelope_id=inp.envelope_id,
                role=TransactionRole.INSTALLMENT_CHILD,
                parent_id=group.id,
                installment_seq=i,
                installment_total=inp.installment_count,
                memo=inp.memo,
                funding_state=FundingState.NOT_APPLICABLE, # Will be set by ZBB engine if applicable
            )
            transactions.append(txn)

        # 5. Save all (simplified: saving group and then txns)
        # In a real repository, this might be a single transaction
        await self._transaction_repo.save_many(transactions)
        
        return InstallmentPurchaseOutput(
            installment_group=group,
            transactions=transactions
        )

    def _calculate_first_due_date(self, purchase_date: date, due_day: int, closing_day: int) -> date:
        """
        Logic:
        Ex: Due 10th. Closing 3rd.
        Purchase 20-Mar:
          Next potential due is 10-Apr.
          Closing for 10-Apr is 03-Apr.
          20-Mar < 03-Apr -> 1st due is 10-Apr.
        Purchase 05-Apr:
          Next potential due is 10-May. (10-Apr already closed).
          Closing for 10-May is 03-May.
          05-Apr < 03-May -> 1st due is 10-May.
        """
        # Find next due date (approx)
        if purchase_date.day < due_day:
            potential_due = date(purchase_date.year, purchase_date.month, due_day)
        else:
            potential_due = date(purchase_date.year, purchase_date.month, due_day) + relativedelta(months=1)
            
        # Closing is usually some days BEFORE the due date
        # If closing_day > due_day, it means it's in the previous month relative to due date
        # Ex: Due 10. Closing 3 -> Closing is 7 days before.
        # Ex: Due 2. Closing 25 -> Closing is 7-8 days before (previous month).
        
        if closing_day < due_day:
            closing_date = date(potential_due.year, potential_due.month, closing_day)
        else:
            closing_date = date(potential_due.year, potential_due.month, closing_day) - relativedelta(months=1)
            
        if purchase_date > closing_date:
            # Already closed, move to next due date
            potential_due += relativedelta(months=1)
            
        return potential_due
