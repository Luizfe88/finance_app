"""
Domain Entity: Subscription

Models recurring charges (assinaturas) with full billing engine support.

Design Patterns:
  - Observer: BillingObserver is notified on upcoming/overdue events
  - Strategy: PaymentStrategy is polymorphic (Pix, CreditCard, Debit)

This entity is intentionally thin — business logic lives in the
BillingEngineService (application layer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class PaymentMethod(str, Enum):
    PIX = "PIX"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT = "DEBIT"
    BOLETO = "BOLETO"


class SubscriptionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


@dataclass
class Subscription:
    """
    Recurring charge definition.

    billing_day: day of month (1–28) when charge occurs
    next_billing_date: computed and stored for efficient querying
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    name: str = ""                             # e.g., "Netflix", "Spotify"
    description: Optional[str] = None
    amount: Decimal = Decimal("0.00")
    currency: str = "BRL"
    payment_method: PaymentMethod = PaymentMethod.CREDIT_CARD
    account_id: Optional[str] = None           # Account to charge
    envelope_id: str = ""                      # Budget envelope (category)
    billing_day: int = 1                       # 1–28
    next_billing_date: datetime = field(default_factory=datetime.utcnow)
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_upcoming(self) -> bool:
        """True if billing is within 7 days."""
        from datetime import timedelta
        return (
            self.is_active
            and self.next_billing_date <= datetime.utcnow() + timedelta(days=7)
        )

    @property
    def is_overdue(self) -> bool:
        """True if billing date has passed and not yet processed."""
        return self.is_active and self.next_billing_date < datetime.utcnow()

    def pause(self) -> None:
        self.status = SubscriptionStatus.PAUSED
        self.updated_at = datetime.utcnow()

    def cancel(self) -> None:
        self.status = SubscriptionStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def advance_billing_date(self) -> None:
        """Advance next_billing_date by 1 month after successful billing."""
        from dateutil.relativedelta import relativedelta
        self.next_billing_date = self.next_billing_date + relativedelta(months=1)
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"Subscription(name={self.name!r}, amount={self.amount}, "
            f"method={self.payment_method.value}, "
            f"next={self.next_billing_date.date()}, "
            f"status={self.status.value})"
        )
