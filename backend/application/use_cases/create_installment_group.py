"""
Use Case: CreateInstallmentGroupUseCase

Normalizes installment purchases from text into a parent-child model.

Input: total amount, N installments, start date, account, envelope
Output: InstallmentGroup parent + N Transaction children (future dates)

Each child transaction gets:
  - parent_id         → InstallmentGroup.id
  - role              → INSTALLMENT_CHILD
  - installment_seq   → 1..N
  - installment_total → N
  - date              → start_date + (seq-1) months
  - status            → PENDING (until due date passes)

Future income commitment: each month's envelope projected_deductions
allows the dashboard to show cash flow impact before bills close.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Protocol

from dateutil.relativedelta import relativedelta

from domain.entities.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionRole, FundingState,
)
from domain.entities.installment_group import InstallmentGroup, InstallmentGroupStatus
from domain.entities.audit_event import AuditEvent, AuditEventType


class TransactionRepo(Protocol):
    async def save_many(self, txns: list[Transaction]) -> list[Transaction]: ...


class InstallmentRepo(Protocol):
    async def save(self, group: InstallmentGroup) -> InstallmentGroup: ...


class AuditRepo(Protocol):
    async def save(self, event: AuditEvent) -> AuditEvent: ...


@dataclass
class CreateInstallmentInput:
    user_id: str
    account_id: str
    envelope_id: str
    description: str
    total_amount: Decimal
    installment_count: int
    start_date: datetime
    merchant: Optional[str] = None
    category: str = "Outros"


@dataclass
class CreateInstallmentOutput:
    group: InstallmentGroup
    installments: list[Transaction]


class CreateInstallmentGroupUseCase:
    """
    Creates an InstallmentGroup and generates all child Transaction records.
    """

    def __init__(
        self,
        transactions: TransactionRepo,
        installments: InstallmentRepo,
        audit: AuditRepo,
    ) -> None:
        self._transactions = transactions
        self._installments = installments
        self._audit = audit

    async def execute(self, inp: CreateInstallmentInput) -> CreateInstallmentOutput:
        if inp.installment_count < 1:
            raise ValueError("installment_count must be >= 1.")
        if inp.total_amount <= Decimal("0"):
            raise ValueError("total_amount must be positive.")

        # Create parent group
        group = InstallmentGroup(
            user_id=inp.user_id,
            account_id=inp.account_id,
            envelope_id=inp.envelope_id,
            description=inp.description,
            merchant=inp.merchant,
            total_amount=inp.total_amount,
            installment_count=inp.installment_count,
            start_date=inp.start_date,
            status=InstallmentGroupStatus.ACTIVE,
        )
        group = await self._installments.save(group)

        # Generate child transactions
        per_installment = (inp.total_amount / inp.installment_count).quantize(Decimal("0.01"))
        children: list[Transaction] = []
        for seq in range(1, inp.installment_count + 1):
            due_date = inp.start_date + relativedelta(months=seq - 1)
            is_last = seq == inp.installment_count
            # Last installment absorbs rounding difference
            amount = (
                inp.total_amount - per_installment * (inp.installment_count - 1)
                if is_last
                else per_installment
            )
            child = Transaction(
                user_id=inp.user_id,
                account_id=inp.account_id,
                amount=amount,
                description=f"{inp.description} ({seq}/{inp.installment_count})",
                category=inp.category,
                date=due_date,
                transaction_type=TransactionType.DEBIT,
                status=TransactionStatus.PENDING if due_date > datetime.utcnow() else TransactionStatus.POSTED,
                role=TransactionRole.INSTALLMENT_CHILD,
                parent_id=group.id,
                installment_seq=seq,
                installment_total=inp.installment_count,
                envelope_id=inp.envelope_id,
                funding_state=FundingState.NOT_APPLICABLE,
                payee=inp.merchant,
            )
            child.compute_and_set_idempotency_key()
            children.append(child)

        children = await self._transactions.save_many(children)

        # Audit trail
        await self._audit.save(AuditEvent.create(
            user_id=inp.user_id,
            event_type=AuditEventType.INSTALLMENT_GROUP_CREATED,
            payload={
                "group_id": group.id,
                "description": inp.description,
                "total_amount": str(inp.total_amount),
                "installment_count": inp.installment_count,
                "start_date": inp.start_date.isoformat(),
                "envelope_id": inp.envelope_id,
                "generated_transaction_ids": [c.id for c in children],
            },
        ))

        return CreateInstallmentOutput(group=group, installments=children)
