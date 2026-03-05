"""
Use Case: BillingEngineService

Observer + Strategy pattern implementation for subscription billing.

Observer Pattern:
  - BillingObserver (abstract interface)
  - UpcomingBillingObserver : notifies on subscriptions due in 7 days
  - OverdueBillingObserver  : notifies on past-due subscriptions

Strategy Pattern:
  - PaymentStrategy (abstract)
  - PixStrategy        : processes Pix payments
  - CreditCardStrategy : processes credit card debits (uses CC reserve engine)
  - DebitStrategy      : processes direct debit

Usage:
    engine = BillingEngineService(subscriptions_repo, transaction_repo, audit_repo)
    engine.add_observer(UpcomingBillingObserver(notification_service))
    results = await engine.run(user_id="...")
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from domain.entities.subscription import Subscription, PaymentMethod, SubscriptionStatus
from domain.entities.transaction import Transaction, TransactionType, TransactionRole, FundingState, TransactionStatus
from domain.entities.audit_event import AuditEvent, AuditEventType


# ── Repository Protocols ───────────────────────────────────────────────────────
class SubscriptionRepo(Protocol):
    async def list_due(self, user_id: str, before: datetime) -> list[Subscription]: ...
    async def save(self, sub: Subscription) -> Subscription: ...


class TransactionRepo(Protocol):
    async def save(self, txn: Transaction) -> Transaction: ...


class AuditRepo(Protocol):
    async def save(self, event: AuditEvent) -> AuditEvent: ...


# ── Observer Interface ─────────────────────────────────────────────────────────
class BillingObserver(abc.ABC):
    """Observer notified on billing lifecycle events."""

    @abc.abstractmethod
    async def on_upcoming(self, subscription: Subscription) -> None:
        """Called when a subscription is due within the notification window."""
        ...

    @abc.abstractmethod
    async def on_overdue(self, subscription: Subscription) -> None:
        """Called when a subscription is past its billing date."""
        ...

    @abc.abstractmethod
    async def on_billed(self, subscription: Subscription, transaction: Transaction) -> None:
        """Called after successful billing."""
        ...


class LoggingBillingObserver(BillingObserver):
    """Default observer — logs events. Replace with notification service in prod."""

    async def on_upcoming(self, subscription: Subscription) -> None:
        print(f"[BILLING] Upcoming: {subscription.name} R${subscription.amount} on {subscription.next_billing_date.date()}")

    async def on_overdue(self, subscription: Subscription) -> None:
        print(f"[BILLING] OVERDUE: {subscription.name} R${subscription.amount} (was due {subscription.next_billing_date.date()})")

    async def on_billed(self, subscription: Subscription, transaction: Transaction) -> None:
        print(f"[BILLING] Billed: {subscription.name} R${subscription.amount} → txn {transaction.id}")


# ── Payment Strategy Interface ─────────────────────────────────────────────────
class PaymentStrategy(abc.ABC):
    """Strategy for processing subscription payments polymorphically."""

    @abc.abstractmethod
    async def process(
        self,
        subscription: Subscription,
        transaction_repo: TransactionRepo,
    ) -> Transaction:
        ...


class PixStrategy(PaymentStrategy):
    async def process(
        self,
        subscription: Subscription,
        transaction_repo: TransactionRepo,
    ) -> Transaction:
        txn = Transaction(
            user_id=subscription.user_id,
            account_id=subscription.account_id or "",
            amount=subscription.amount,
            description=f"[PIX] {subscription.name}",
            category=subscription.name,
            date=datetime.utcnow(),
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.POSTED,
            role=TransactionRole.SUBSCRIPTION,
            envelope_id=subscription.envelope_id,
            funding_state=FundingState.NOT_APPLICABLE,
        )
        txn.compute_and_set_idempotency_key()
        return await transaction_repo.save(txn)


class CreditCardStrategy(PaymentStrategy):
    async def process(
        self,
        subscription: Subscription,
        transaction_repo: TransactionRepo,
    ) -> Transaction:
        txn = Transaction(
            user_id=subscription.user_id,
            account_id=subscription.account_id or "",
            amount=subscription.amount,
            description=f"[CC] {subscription.name}",
            category=subscription.name,
            date=datetime.utcnow(),
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.POSTED,
            role=TransactionRole.SUBSCRIPTION,
            envelope_id=subscription.envelope_id,
            funding_state=FundingState.FUNDED,  # Assume funded; full engine in RecordCreditPurchase
        )
        txn.compute_and_set_idempotency_key()
        return await transaction_repo.save(txn)


class DebitStrategy(PaymentStrategy):
    async def process(
        self,
        subscription: Subscription,
        transaction_repo: TransactionRepo,
    ) -> Transaction:
        txn = Transaction(
            user_id=subscription.user_id,
            account_id=subscription.account_id or "",
            amount=subscription.amount,
            description=f"[DÉBITO] {subscription.name}",
            category=subscription.name,
            date=datetime.utcnow(),
            transaction_type=TransactionType.DEBIT,
            status=TransactionStatus.POSTED,
            role=TransactionRole.SUBSCRIPTION,
            envelope_id=subscription.envelope_id,
            funding_state=FundingState.NOT_APPLICABLE,
        )
        txn.compute_and_set_idempotency_key()
        return await transaction_repo.save(txn)


# ── Strategy Factory ───────────────────────────────────────────────────────────
def get_payment_strategy(method: PaymentMethod) -> PaymentStrategy:
    strategies = {
        PaymentMethod.PIX: PixStrategy(),
        PaymentMethod.CREDIT_CARD: CreditCardStrategy(),
        PaymentMethod.DEBIT: DebitStrategy(),
        PaymentMethod.BOLETO: PixStrategy(),  # Boleto treated as Pix for now
    }
    return strategies.get(method, PixStrategy())


# ── Billing Engine ─────────────────────────────────────────────────────────────
@dataclass
class BillingResult:
    processed: list[tuple[Subscription, Transaction]]
    skipped_upcoming: list[Subscription]
    skipped_overdue: list[Subscription]


class BillingEngineService:
    """
    Orchestrates subscription billing for a user.

    1. Loads subscriptions due within `window_days`
    2. Notifies observers (upcoming, overdue)
    3. Processes payments via polymorphic strategy
    4. Advances next_billing_date
    5. Writes audit events
    """

    UPCOMING_WINDOW_DAYS = 7

    def __init__(
        self,
        subscriptions: SubscriptionRepo,
        transactions: TransactionRepo,
        audit: AuditRepo,
    ) -> None:
        self._subscriptions = subscriptions
        self._transactions = transactions
        self._audit = audit
        self._observers: list[BillingObserver] = [LoggingBillingObserver()]

    def add_observer(self, observer: BillingObserver) -> None:
        self._observers.append(observer)

    async def run(self, user_id: str, process_due: bool = True) -> BillingResult:
        """
        Run the billing engine for a user.
        process_due=True: actually processes payments for overdue subscriptions
        process_due=False: only notify (dry-run / preview mode)
        """
        now = datetime.utcnow()
        window = now + timedelta(days=self.UPCOMING_WINDOW_DAYS)

        due_subs = await self._subscriptions.list_due(user_id=user_id, before=window)

        processed: list[tuple[Subscription, Transaction]] = []
        upcoming: list[Subscription] = []
        overdue: list[Subscription] = []

        for sub in due_subs:
            if sub.next_billing_date > now:
                # Upcoming — only notify
                upcoming.append(sub)
                for obs in self._observers:
                    await obs.on_upcoming(sub)
            else:
                # Overdue — notify + optionally process
                overdue.append(sub)
                for obs in self._observers:
                    await obs.on_overdue(sub)

                if process_due:
                    strategy = get_payment_strategy(sub.payment_method)
                    txn = await strategy.process(sub, self._transactions)
                    sub.advance_billing_date()
                    await self._subscriptions.save(sub)

                    for obs in self._observers:
                        await obs.on_billed(sub, txn)

                    await self._audit.save(AuditEvent.create(
                        user_id=user_id,
                        event_type=AuditEventType.SUBSCRIPTION_BILLED,
                        payload={
                            "subscription_id": sub.id,
                            "subscription_name": sub.name,
                            "amount": str(sub.amount),
                            "payment_method": sub.payment_method.value,
                            "transaction_id": txn.id,
                            "next_billing_date": sub.next_billing_date.isoformat(),
                        },
                    ))
                    processed.append((sub, txn))

        return BillingResult(
            processed=processed,
            skipped_upcoming=upcoming,
            skipped_overdue=overdue if not process_due else [],
        )
