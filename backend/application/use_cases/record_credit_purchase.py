"""
Use Case: RecordCreditCardPurchaseUseCase

ZBB Credit Card Liquidity Reserve Engine.

The credit card is NOT treated as "free money".
Each purchase triggers a fund reservation to ensure the bill can be paid.

State Machine (FundingState):
  FUNDED        → envelope had budget; funds moved to "Pagamento CC" envelope
  UNFUNDED      → no budget in envelope; debt created; alert logged
  POSITIVE      → refund/credit applied; CC payment envelope reduced
  INVOICE_PAYMENT → user paid bill; checking → CC payment envelope transfer

Double-Entry on FUNDED purchase (R$150 "Alimentação"):
  DEBIT  Alimentação envelope   -R$150  (budget consumed)
  CREDIT Pagamento CC envelope  +R$150  (reserve for future bill)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Protocol

from domain.entities.transaction import Transaction, TransactionType, FundingState, TransactionRole
from domain.entities.budget_envelope import BudgetEnvelope
from domain.entities.journal_entry import JournalEntry
from domain.entities.audit_event import AuditEvent, AuditEventType


class TransactionRepo(Protocol):
    async def save(self, txn: Transaction) -> Transaction: ...


class EnvelopeRepo(Protocol):
    async def find_by_id(self, eid: str) -> BudgetEnvelope | None: ...
    async def find_by_name_and_month(self, user_id: str, name: str, month: str) -> BudgetEnvelope | None: ...
    async def save(self, envelope: BudgetEnvelope) -> BudgetEnvelope: ...


class JournalRepo(Protocol):
    async def save(self, entry: JournalEntry) -> JournalEntry: ...


class AuditRepo(Protocol):
    async def save(self, event: AuditEvent) -> AuditEvent: ...


@dataclass
class CreditPurchaseInput:
    user_id: str
    account_id: str                # Credit card account
    amount: Decimal
    description: str
    date: datetime
    category: str
    envelope_id: Optional[str] = None      # Budget envelope for category
    cc_payment_envelope_id: Optional[str] = None  # "Pagamento CC" envelope
    payee: Optional[str] = None
    memo: Optional[str] = None
    fit_id: Optional[str] = None           # OFX import key


@dataclass
class CreditPurchaseOutput:
    transaction: Transaction
    funding_state: FundingState
    envelope_after: Optional[BudgetEnvelope]
    cc_payment_envelope_after: Optional[BudgetEnvelope]
    is_debt_generated: bool


class RecordCreditCardPurchaseUseCase:
    """
    Records a credit card purchase and manages the ZBB liquidity reserve.
    """

    def __init__(
        self,
        transactions: TransactionRepo,
        envelopes: EnvelopeRepo,
        journal: JournalRepo,
        audit: AuditRepo,
    ) -> None:
        self._transactions = transactions
        self._envelopes = envelopes
        self._journal = journal
        self._audit = audit

    async def execute(self, inp: CreditPurchaseInput) -> CreditPurchaseOutput:
        month = inp.date.strftime("%Y-%m")

        # Load spending envelope (e.g., "Alimentação")
        spending_envelope: Optional[BudgetEnvelope] = None
        if inp.envelope_id:
            spending_envelope = await self._envelopes.find_by_id(inp.envelope_id)

        # Load CC payment envelope
        cc_payment_envelope: Optional[BudgetEnvelope] = None
        if inp.cc_payment_envelope_id:
            cc_payment_envelope = await self._envelopes.find_by_id(inp.cc_payment_envelope_id)

        # Determine funding state
        if spending_envelope and spending_envelope.available >= inp.amount:
            funding_state = FundingState.FUNDED
        elif spending_envelope:
            funding_state = FundingState.UNFUNDED
        else:
            funding_state = FundingState.UNFUNDED

        # Build transaction
        txn = Transaction(
            user_id=inp.user_id,
            account_id=inp.account_id,
            amount=inp.amount,
            description=inp.description,
            category=inp.category,
            date=inp.date,
            transaction_type=TransactionType.DEBIT,
            role=TransactionRole.STANDALONE,
            envelope_id=inp.envelope_id,
            funding_state=funding_state,
            payee=inp.payee,
            memo=inp.memo,
            fit_id=inp.fit_id,
        )
        txn.compute_and_set_idempotency_key()
        txn = await self._transactions.save(txn)

        # If FUNDED: move money from spending envelope → CC payment envelope
        if funding_state == FundingState.FUNDED and spending_envelope and cc_payment_envelope:
            spending_envelope.charge(inp.amount)
            cc_payment_envelope.allocated += inp.amount
            spending_envelope = await self._envelopes.save(spending_envelope)
            cc_payment_envelope = await self._envelopes.save(cc_payment_envelope)

            # Double-entry journal
            entry = JournalEntry(
                user_id=inp.user_id,
                debit_envelope_id=spending_envelope.id,
                credit_envelope_id=cc_payment_envelope.id,
                amount=inp.amount,
                note=f"CC reserve: {inp.description}",
                event_type="CREDIT_RESERVE",
                transaction_id=txn.id,
            )
            await self._journal.save(entry)

        # Audit event
        event_type = (
            AuditEventType.CREDIT_PURCHASE_FUNDED
            if funding_state == FundingState.FUNDED
            else AuditEventType.CREDIT_PURCHASE_UNFUNDED
        )
        await self._audit.save(AuditEvent.create(
            user_id=inp.user_id,
            event_type=event_type,
            payload={
                "transaction_id": txn.id,
                "amount": str(inp.amount),
                "category": inp.category,
                "description": inp.description,
                "envelope_id": inp.envelope_id,
                "funding_state": funding_state.value,
                "debt_generated": funding_state == FundingState.UNFUNDED,
            },
        ))

        return CreditPurchaseOutput(
            transaction=txn,
            funding_state=funding_state,
            envelope_after=spending_envelope,
            cc_payment_envelope_after=cc_payment_envelope,
            is_debt_generated=(funding_state == FundingState.UNFUNDED),
        )
