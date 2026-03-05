"""
Infrastructure: SQLAlchemy ORM Models (v2 — Institutional Grade)

Maps domain entities to database tables.
Uses PostgreSQL-compatible types (also works with SQLite for dev).

New tables (v2):
  - budget_envelopes    : ZBB envelope model
  - journal_entries     : Double-entry bookkeeping ledger
  - installment_groups  : Parent for normalized installment transactions
  - subscriptions       : Recurring charge definitions (billing engine)
  - audit_events        : Immutable tamper-evident audit trail

Extended tables (v2):
  - transactions        : + envelope_id, funding_state, role, parent_id,
                            installment_seq/total, idempotency_key
  - accounts            : + credit_limit, card_payment_envelope_id
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column, String, Numeric, DateTime, Boolean, Text, Integer,
    ForeignKey, UniqueConstraint, JSON,
    Enum as SAEnum,
)
import sqlalchemy as sa

from infrastructure.db.database import Base
from domain.entities.transaction import (
    TransactionType, TransactionStatus, TransactionRole, FundingState,
)
from domain.entities.account import AccountType
from domain.entities.audit_event import AuditEventType
from domain.entities.installment_group import InstallmentGroupStatus
from domain.entities.subscription import PaymentMethod, SubscriptionStatus


# ── Transactions ───────────────────────────────────────────────────────────────
class TransactionModel(Base):
    """ORM model for the transactions table (v2)."""
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    account_id = Column(String(36), nullable=False, index=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    description = Column(Text, nullable=False, default="")
    category = Column(String(100), nullable=False, default="Outros")
    date = Column(DateTime, nullable=False, index=True)
    transaction_type = Column(
        SAEnum(TransactionType, name="transactiontype"),
        nullable=False
    )
    status = Column(
        SAEnum(TransactionStatus, name="transactionstatus"),
        nullable=False,
        default=TransactionStatus.POSTED
    )

    # ── ZBB / Double-Entry (v2) ────────────────────────────────────────────────
    envelope_id = Column(String(36), nullable=True, index=True)          # → budget_envelopes.id
    funding_state = Column(
        SAEnum(FundingState, name="fundingstate"),
        nullable=False,
        default=FundingState.NOT_APPLICABLE,
    )

    # ── Installment Normalization (v2) ─────────────────────────────────────────
    role = Column(
        SAEnum(TransactionRole, name="transactionrole"),
        nullable=False,
        default=TransactionRole.STANDALONE,
    )
    parent_id = Column(String(36), nullable=True, index=True)            # → installment_groups.id
    installment_seq = Column(Integer, nullable=True)
    installment_total = Column(Integer, nullable=True)

    # ── Open Finance Idempotency (v2) ──────────────────────────────────────────
    idempotency_key = Column(String(64), nullable=True)                  # SHA-256 hex digest
    fit_id = Column(String(255), nullable=True, index=True)              # OFX dedup key

    # ── Metadata ───────────────────────────────────────────────────────────────
    memo = Column(Text, nullable=True)
    payee = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_transactions_user_fitid", "user_id", "fit_id"),
        sa.Index("ix_transactions_user_date", "user_id", "date"),
        sa.Index("ix_transactions_user_envelope", "user_id", "envelope_id"),
        sa.Index("ix_transactions_parent", "parent_id"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_transactions_idempotency"),
    )


# ── Accounts ───────────────────────────────────────────────────────────────────
class AccountModel(Base):
    """ORM model for the accounts table (v2)."""
    __tablename__ = "accounts"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    bank_name = Column(String(255), nullable=False)
    bank_code = Column(String(10), nullable=True)
    masked_account_number = Column(String(20), nullable=False, default="****")
    account_type = Column(
        SAEnum(AccountType, name="accounttype"),
        nullable=False,
        default=AccountType.CHECKING
    )
    balance = Column(Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00"))
    currency = Column(String(3), nullable=False, default="BRL")
    is_active = Column(Boolean, nullable=False, default=True)

    # ── Credit Card specific (v2) ──────────────────────────────────────────────
    credit_limit = Column(Numeric(precision=15, scale=2), nullable=True)
    card_payment_envelope_id = Column(String(36), nullable=True)         # → budget_envelopes.id

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Users ──────────────────────────────────────────────────────────────────────
class UserModel(Base):
    """ORM model for the users table."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    data_minimization_level = Column(String(20), nullable=False, default="STANDARD")
    consent_given_at = Column(DateTime, nullable=True)
    deletion_requested_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── Budget Envelopes (v2 NEW) ──────────────────────────────────────────────────
class BudgetEnvelopeModel(Base):
    """ZBB budget envelope — one per (user, category, month)."""
    __tablename__ = "budget_envelopes"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    icon = Column(String(10), nullable=False, default="📦")
    color = Column(String(7), nullable=False, default="#6366F1")
    month = Column(String(7), nullable=False, index=True)           # "YYYY-MM"
    allocated = Column(Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00"))
    spent = Column(Numeric(precision=15, scale=2), nullable=False, default=Decimal("0.00"))
    is_system = Column(Boolean, nullable=False, default=False)
    category_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_envelopes_user_month", "user_id", "month"),
        UniqueConstraint("user_id", "name", "month", name="uq_envelope_user_name_month"),
    )


# ── Journal Entries (v2 NEW) ───────────────────────────────────────────────────
class JournalEntryModel(Base):
    """Double-entry bookkeeping ledger — every fund move creates one row."""
    __tablename__ = "journal_entries"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    debit_envelope_id = Column(String(36), nullable=False, index=True)
    credit_envelope_id = Column(String(36), nullable=False, index=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    note = Column(Text, nullable=False, default="")
    event_type = Column(String(50), nullable=False, default="ALLOCATION")
    transaction_id = Column(String(36), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ── Installment Groups (v2 NEW) ────────────────────────────────────────────────
class InstallmentGroupModel(Base):
    """Parent record for installment purchases."""
    __tablename__ = "installment_groups"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    account_id = Column(String(36), nullable=False)
    envelope_id = Column(String(36), nullable=False)
    description = Column(Text, nullable=False, default="")
    merchant = Column(String(255), nullable=True)
    total_amount = Column(Numeric(precision=15, scale=2), nullable=False)
    installment_count = Column(Integer, nullable=False, default=1)
    start_date = Column(DateTime, nullable=False)
    status = Column(
        SAEnum(InstallmentGroupStatus, name="installmentgroupstatus"),
        nullable=False,
        default=InstallmentGroupStatus.ACTIVE,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_installment_groups_user", "user_id"),
    )


# ── Subscriptions (v2 NEW) ────────────────────────────────────────────────────
class SubscriptionModel(Base):
    """Recurring charge — drives the billing engine."""
    __tablename__ = "subscriptions"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    amount = Column(Numeric(precision=15, scale=2), nullable=False)
    currency = Column(String(3), nullable=False, default="BRL")
    payment_method = Column(
        SAEnum(PaymentMethod, name="paymentmethod"),
        nullable=False,
        default=PaymentMethod.CREDIT_CARD,
    )
    account_id = Column(String(36), nullable=True)
    envelope_id = Column(String(36), nullable=False)
    billing_day = Column(Integer, nullable=False, default=1)
    next_billing_date = Column(DateTime, nullable=False, index=True)
    status = Column(
        SAEnum(SubscriptionStatus, name="subscriptionstatus"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        sa.Index("ix_subscriptions_user_next_billing", "user_id", "next_billing_date"),
    )


# ── Audit Events (v2 NEW) ─────────────────────────────────────────────────────
class AuditEventModel(Base):
    """
    Immutable tamper-evident audit trail.
    Rows are NEVER updated — only inserted or anonymized on LGPD deletion.
    """
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), nullable=False, index=True)    # Set to "DELETED" on LGPD erasure
    event_type = Column(
        SAEnum(AuditEventType, name="auditeventtype"),
        nullable=False,
    )
    payload = Column(JSON, nullable=False, default=dict)
    checksum = Column(String(64), nullable=False)               # SHA-256 of payload
    ip_address = Column(String(45), nullable=True)              # IPv4 or IPv6
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    __table_args__ = (
        sa.Index("ix_audit_events_user_type", "user_id", "event_type"),
        sa.Index("ix_audit_events_created", "created_at"),
    )
