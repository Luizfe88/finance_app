"""
Domain Entity: JournalEntry

Implements the Double-Entry Bookkeeping principle:
  Assets = Liabilities + Equity

Every fund movement in the system MUST produce a balanced JournalEntry:
  - debit_envelope_id  : envelope that loses funds (e.g., "Pronto para Atribuir")
  - credit_envelope_id : envelope that gains funds (e.g., "Alimentação")
  - amount             : always positive; direction inferred from debit/credit

This guarantees accounting integrity — the sum of all envelope balances
always equals total income received (no money can be created or destroyed).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid


@dataclass
class JournalEntry:
    """
    Immutable double-entry journal record.

    Once created, a JournalEntry should NEVER be modified — only reversed
    via a compensating entry. This upholds audit trail integrity.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    debit_envelope_id: str = ""        # Envelope losing funds
    credit_envelope_id: str = ""       # Envelope gaining funds
    amount: Decimal = Decimal("0.00")
    note: str = ""                     # Human-readable explanation
    event_type: str = "ALLOCATION"     # ALLOCATION | CREDIT_RESERVE | REFUND | INVOICE_PAYMENT
    transaction_id: Optional[str] = None   # Linked transaction (if caused by one)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise ValueError("JournalEntry amount must be positive.")
        if self.debit_envelope_id == self.credit_envelope_id:
            raise ValueError("Debit and credit envelopes must differ.")

    @property
    def is_allocation(self) -> bool:
        return self.event_type == "ALLOCATION"

    @property
    def is_credit_reserve(self) -> bool:
        return self.event_type == "CREDIT_RESERVE"

    def __repr__(self) -> str:
        return (
            f"JournalEntry(debit={self.debit_envelope_id!r}, "
            f"credit={self.credit_envelope_id!r}, "
            f"amount={self.amount}, type={self.event_type!r})"
        )
