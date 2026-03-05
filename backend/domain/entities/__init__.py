"""
Domain Entities Package (v2 — Institutional Grade)

All domain entities exported here for clean imports.
"""

from domain.entities.account import Account, AccountType
from domain.entities.audit_event import AuditEvent, AuditEventType
from domain.entities.budget_envelope import BudgetEnvelope, SystemEnvelope
from domain.entities.category import Category
from domain.entities.installment_group import InstallmentGroup, InstallmentGroupStatus
from domain.entities.journal_entry import JournalEntry
from domain.entities.subscription import Subscription, PaymentMethod, SubscriptionStatus
from domain.entities.transaction import (
    Transaction,
    TransactionType,
    TransactionStatus,
    TransactionRole,
    FundingState,
    Money,
    compute_idempotency_key,
)
from domain.entities.user import User

__all__ = [
    # Account
    "Account", "AccountType",
    # Audit
    "AuditEvent", "AuditEventType",
    # Budget
    "BudgetEnvelope", "SystemEnvelope",
    # Category
    "Category",
    # Installments
    "InstallmentGroup", "InstallmentGroupStatus",
    # Journal
    "JournalEntry",
    # Subscription
    "Subscription", "PaymentMethod", "SubscriptionStatus",
    # Transaction
    "Transaction", "TransactionType", "TransactionStatus",
    "TransactionRole", "FundingState", "Money", "compute_idempotency_key",
    # User
    "User",
]
