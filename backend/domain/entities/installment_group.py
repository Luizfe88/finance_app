"""
Domain Entity: InstallmentGroup

Normalizes installment purchases from text descriptions ("Parcela 3/12")
into a proper parent-child relational model.

Parent: InstallmentGroup — describes the full purchase
Children: N Transaction records, each with installment_seq and due_date

This enables:
  - Accurate cash flow projections (future installment commits)
  - Per-installment status tracking (PENDING, PAID, OVERDUE)
  - Category persistence across all installments
  - Early income-commitment alerts before bills close
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class InstallmentGroupStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


@dataclass
class InstallmentGroup:
    """
    Parent record for a split/installment purchase.

    total_amount  = sum of all child installment amounts
    installment_count = number of installments (N)
    Children are Transaction entities with parent_id = this id.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    account_id: str = ""       # Credit card or account used
    envelope_id: str = ""      # Budget envelope (category) charged
    description: str = ""
    merchant: Optional[str] = None
    total_amount: Decimal = Decimal("0.00")
    installment_count: int = 1
    start_date: datetime = field(default_factory=datetime.utcnow)
    status: InstallmentGroupStatus = InstallmentGroupStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def installment_amount(self) -> Decimal:
        """Per-installment amount (rounded to 2 decimal places)."""
        if self.installment_count <= 0:
            return Decimal("0.00")
        return (self.total_amount / self.installment_count).quantize(Decimal("0.01"))

    @property
    def is_active(self) -> bool:
        return self.status == InstallmentGroupStatus.ACTIVE

    def cancel(self) -> None:
        self.status = InstallmentGroupStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        self.status = InstallmentGroupStatus.COMPLETED
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"InstallmentGroup(description={self.description!r}, "
            f"total={self.total_amount}, "
            f"installments={self.installment_count}, "
            f"status={self.status.value})"
        )
