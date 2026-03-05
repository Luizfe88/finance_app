"""
Domain Entity: Transaction (v2 — Institutional Grade)

Extended to support:
  - Double-Entry Bookkeeping: envelope_id links to BudgetEnvelope
  - ZBB Credit Card Engine: funding_state tracks reserve status
  - Installment Normalization: parent_id + installment_seq
  - Open Finance Idempotency: idempotency_key (SHA-256 hash)
  - Role classification: STANDALONE, INSTALLMENT_PARENT/CHILD, SUBSCRIPTION
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import hashlib
import uuid


class TransactionType(str, Enum):
    """Type of financial transaction."""
    CREDIT = "CREDIT"   # Money coming in
    DEBIT = "DEBIT"     # Money going out
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    """Processing status of a transaction."""
    POSTED = "POSTED"       # Settled/confirmed
    PENDING = "PENDING"     # Awaiting settlement
    CANCELLED = "CANCELLED"


class TransactionRole(str, Enum):
    """Structural role of this transaction in the system."""
    STANDALONE = "STANDALONE"               # Regular single transaction
    INSTALLMENT_PARENT = "INSTALLMENT_PARENT"   # Summary record (not a real debit)
    INSTALLMENT_CHILD = "INSTALLMENT_CHILD"     # Individual installment
    SUBSCRIPTION = "SUBSCRIPTION"           # Auto-generated from billing engine


class PaymentMethod(str, Enum):
    """Unified payment method for transactions and subscriptions."""
    CASH_PIX = "CASH_PIX"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    BOLETO_TRANSFER = "BOLETO_TRANSFER"
    OTHER = "OTHER"
    
    # Aliases for subscription backward compatibility if needed in logic
    PIX = "CASH_PIX"
    DEBIT = "DEBIT_CARD"
    BOLETO = "BOLETO_TRANSFER"


class FundingState(str, Enum):
    """
    Credit Card Liquidity Reserve State.

    FUNDED: envelope had budget → funds moved to CC Payment envelope.
    UNFUNDED: no budget in envelope → debt generated (alert triggered).
    POSITIVE: refund/credit → positive balance in CC Payment envelope.
    INVOICE_PAYMENT: user paid CC bill → debit checking, credit CC envelope.
    NOT_APPLICABLE: not a credit card transaction.
    """
    FUNDED = "FUNDED"
    UNFUNDED = "UNFUNDED"
    POSITIVE = "POSITIVE"
    INVOICE_PAYMENT = "INVOICE_PAYMENT"
    NOT_APPLICABLE = "NOT_APPLICABLE"


def compute_idempotency_key(date: datetime, amount: Decimal, payee: str) -> str:
    """
    Open Finance idempotency key — SHA-256 hash of (date, amount, payee).

    Ensures that importing the same bank statement twice produces exactly
    the same key, allowing safe deduplication without storing the full raw data.
    """
    raw = f"{date.strftime('%Y-%m-%d')}:{str(amount.quantize(Decimal('0.01')))}:{payee.strip().upper()}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Money:
    """Value object representing a monetary amount with currency."""
    amount: Decimal
    currency: str = "BRL"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            self.amount = Decimal(str(self.amount))


@dataclass
class Transaction:
    """
    Core domain entity representing a financial transaction (v2).

    Key additions vs v1:
      - envelope_id    : links this debit to a BudgetEnvelope (ZBB)
      - funding_state  : CC reserve engine state
      - parent_id      : InstallmentGroup.id for child installments
      - installment_seq / installment_total: e.g., 3 of 12
      - role           : structural classification
      - idempotency_key: SHA-256 for Open Finance deduplication

    LGPD: account_number is never stored — only masked/tokenized form.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    account_id: str = ""
    amount: Decimal = Decimal("0.00")
    currency: str = "BRL"
    description: str = ""
    category: str = "Outros"
    date: datetime = field(default_factory=datetime.utcnow)
    transaction_type: TransactionType = TransactionType.DEBIT
    status: TransactionStatus = TransactionStatus.POSTED
    payment_method: PaymentMethod = PaymentMethod.CASH_PIX

    # --- ZBB / Double-Entry ---
    envelope_id: Optional[str] = None         # Linked BudgetEnvelope
    funding_state: FundingState = FundingState.NOT_APPLICABLE

    # --- Recurrence ---
    is_recurring: bool = False
    recurrence_rule: Optional[str] = None     # e.g., "FREQ=MONTHLY;INTERVAL=1"

    # --- Installment Normalization ---
    role: TransactionRole = TransactionRole.STANDALONE
    parent_id: Optional[str] = None           # InstallmentGroup.id
    installment_seq: Optional[int] = None     # 1, 2, ..., N
    installment_total: Optional[int] = None   # N (total installments)

    # --- Open Finance Idempotency ---
    idempotency_key: Optional[str] = None     # SHA-256(date+amount+payee)
    fit_id: Optional[str] = None              # OFX Financial Institution Tx ID

    # --- Metadata ---
    memo: Optional[str] = None
    payee: Optional[str] = None               # Counterpart name (tokenized if needed)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def money(self) -> Money:
        return Money(amount=self.amount, currency=self.currency)

    @property
    def is_income(self) -> bool:
        return self.transaction_type == TransactionType.CREDIT

    @property
    def is_expense(self) -> bool:
        return self.transaction_type == TransactionType.DEBIT

    @property
    def signed_amount(self) -> Decimal:
        """Returns negative for DEBIT, positive for CREDIT."""
        if self.is_expense:
            return -abs(self.amount)
        return abs(self.amount)

    @property
    def is_installment_child(self) -> bool:
        return self.role == TransactionRole.INSTALLMENT_CHILD

    @property
    def installment_label(self) -> Optional[str]:
        """Human-readable label, e.g. '3/12'."""
        if self.installment_seq and self.installment_total:
            return f"{self.installment_seq}/{self.installment_total}"
        return None

    def categorize(self, category: str) -> None:
        """Assign a category to this transaction."""
        self.category = category
        self.updated_at = datetime.utcnow()

    def assign_envelope(self, envelope_id: str) -> None:
        """Link this transaction to a ZBB envelope."""
        self.envelope_id = envelope_id
        self.updated_at = datetime.utcnow()

    def set_funding_state(self, state: FundingState) -> None:
        """Update the credit card funding state."""
        self.funding_state = state
        self.updated_at = datetime.utcnow()

    def compute_and_set_idempotency_key(self) -> str:
        """Compute the Open Finance idempotency key and store it."""
        key = compute_idempotency_key(
            date=self.date,
            amount=self.amount,
            payee=self.payee or self.description or "",
        )
        self.idempotency_key = key
        return key

    def __repr__(self) -> str:
        parts = [
            f"Transaction(id={self.id!r}",
            f"date={self.date.date()}",
            f"amount={self.amount} {self.currency}",
            f"type={self.transaction_type.value}",
            f"description={self.description!r}",
        ]
        if self.installment_label:
            parts.append(f"installment={self.installment_label}")
        if self.funding_state != FundingState.NOT_APPLICABLE:
            parts.append(f"funding={self.funding_state.value}")
        return ", ".join(parts) + ")"
