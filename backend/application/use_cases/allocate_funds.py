"""
Use Case: AllocateFundsUseCase

Zero-Based Budgeting (ZBB) — Envelope Allocation Engine.

Flow:
  1. Verify source envelope has sufficient available funds (PRA or any envelope)
  2. Move `amount` from source → target envelope
  3. Create a JournalEntry (double-entry)
  4. Write AuditEvent
  5. Return updated envelope states

This is the PRIMARY mechanism by which income becomes usable budget.
All money must flow through allocation before it can be spent.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from domain.entities.budget_envelope import BudgetEnvelope
from domain.entities.journal_entry import JournalEntry
from domain.entities.audit_event import AuditEvent, AuditEventType


class EnvelopeRepository(Protocol):
    async def find_by_id(self, envelope_id: str) -> BudgetEnvelope | None: ...
    async def save(self, envelope: BudgetEnvelope) -> BudgetEnvelope: ...


class JournalRepository(Protocol):
    async def save(self, entry: JournalEntry) -> JournalEntry: ...


class AuditRepository(Protocol):
    async def save(self, event: AuditEvent) -> AuditEvent: ...


@dataclass
class AllocateFundsInput:
    user_id: str
    source_envelope_id: str    # Usually "Pronto para Atribuir"
    target_envelope_id: str
    amount: Decimal
    note: str = ""


@dataclass
class AllocateFundsOutput:
    source_envelope: BudgetEnvelope
    target_envelope: BudgetEnvelope
    journal_entry: JournalEntry


class AllocateFundsUseCase:
    """
    Move money from a source envelope to a target envelope.
    Maintains double-entry integrity via JournalEntry.
    """

    def __init__(
        self,
        envelopes: EnvelopeRepository,
        journal: JournalRepository,
        audit: AuditRepository,
    ) -> None:
        self._envelopes = envelopes
        self._journal = journal
        self._audit = audit

    async def execute(self, inp: AllocateFundsInput) -> AllocateFundsOutput:
        if inp.amount <= Decimal("0"):
            raise ValueError("Allocation amount must be positive.")

        # Load envelopes
        source = await self._envelopes.find_by_id(inp.source_envelope_id)
        if not source:
            raise ValueError(f"Source envelope {inp.source_envelope_id!r} not found.")
        if source.user_id != inp.user_id:
            raise PermissionError("Access denied to source envelope.")

        target = await self._envelopes.find_by_id(inp.target_envelope_id)
        if not target:
            raise ValueError(f"Target envelope {inp.target_envelope_id!r} not found.")
        if target.user_id != inp.user_id:
            raise PermissionError("Access denied to target envelope.")

        # Validate available funds
        if source.available < inp.amount:
            raise ValueError(
                f"Insufficient funds in '{source.name}'. "
                f"Available: {source.available}, Requested: {inp.amount}"
            )

        # Transfer: debit source (reduce allocated), credit target (increase allocated)
        source.allocated -= inp.amount
        source.updated_at = __import__("datetime").datetime.utcnow()
        target.allocate(inp.amount)

        # Persist
        source = await self._envelopes.save(source)
        target = await self._envelopes.save(target)

        # Journal entry (double-entry)
        entry = JournalEntry(
            user_id=inp.user_id,
            debit_envelope_id=inp.source_envelope_id,
            credit_envelope_id=inp.target_envelope_id,
            amount=inp.amount,
            note=inp.note or f"Allocation: {source.name} → {target.name}",
            event_type="ALLOCATION",
        )
        entry = await self._journal.save(entry)

        # Audit trail
        event = AuditEvent.create(
            user_id=inp.user_id,
            event_type=AuditEventType.ENVELOPE_ALLOCATION,
            payload={
                "source_envelope_id": inp.source_envelope_id,
                "source_envelope_name": source.name,
                "target_envelope_id": inp.target_envelope_id,
                "target_envelope_name": target.name,
                "amount": str(inp.amount),
                "journal_entry_id": entry.id,
            },
        )
        await self._audit.save(event)

        return AllocateFundsOutput(
            source_envelope=source,
            target_envelope=target,
            journal_entry=entry,
        )
