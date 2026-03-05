"""
Domain Entity: BudgetEnvelope

Implements Zero-Based Budgeting (ZBB) envelope methodology.
Every real (BRL) must be assigned a 'mission'/category before being spent.

System envelopes (is_system=True):
  - "Pronto para Atribuir"    : Unallocated income — must be zeroed out
  - "Pagamento Cartão de Crédito" : Credit card payment reserve
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid


@dataclass
class BudgetEnvelope:
    """
    A named budget envelope for a specific month.

    Double-entry invariant:
      allocated = sum of all JournalEntry credits into this envelope
      spent     = sum of all Transaction debits against this envelope
      available = allocated - spent   (can be negative → overspent)
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""
    icon: str = "📦"
    color: str = "#6366F1"
    month: str = ""                   # "YYYY-MM" e.g. "2026-03"
    allocated: Decimal = Decimal("0.00")    # Budget assigned this month
    spent: Decimal = Decimal("0.00")        # Actual debits charged
    is_system: bool = False               # System envelopes cannot be deleted
    category_id: Optional[str] = None     # Linked category (optional)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def available(self) -> Decimal:
        """Funds remaining in this envelope. Negative = overspent."""
        return self.allocated - self.spent

    @property
    def utilization_pct(self) -> float:
        """0–100+ (can exceed 100 if overspent)."""
        if self.allocated == Decimal("0"):
            return 0.0
        return float(self.spent / self.allocated * 100)

    @property
    def is_overspent(self) -> bool:
        return self.available < Decimal("0")

    def allocate(self, amount: Decimal) -> None:
        """Add funds to this envelope (from Pronto para Atribuir)."""
        if amount <= Decimal("0"):
            raise ValueError("Allocation amount must be positive.")
        self.allocated += amount
        self.updated_at = datetime.utcnow()

    def charge(self, amount: Decimal) -> None:
        """Deduct from spent (ZBB: records actual consumption)."""
        if amount <= Decimal("0"):
            raise ValueError("Charge amount must be positive.")
        self.spent += amount
        self.updated_at = datetime.utcnow()

    def refund(self, amount: Decimal) -> None:
        """Reverse a charge (e.g., store credit or cancelled purchase)."""
        if amount <= Decimal("0"):
            raise ValueError("Refund amount must be positive.")
        self.spent = max(Decimal("0"), self.spent - amount)
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"BudgetEnvelope(name={self.name!r}, month={self.month}, "
            f"allocated={self.allocated}, spent={self.spent}, "
            f"available={self.available})"
        )


# ── System Envelope Names (canonical) ──────────────────────────────────────────
class SystemEnvelope:
    READY_TO_ASSIGN = "Pronto para Atribuir"
    CREDIT_CARD_PAYMENT = "Pagamento Cartão de Crédito"
    INVESTMENTS = "Investimentos"
