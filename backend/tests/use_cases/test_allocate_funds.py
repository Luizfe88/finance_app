import pytest
from decimal import Decimal
from typing import Dict

from domain.entities.budget_envelope import BudgetEnvelope
from domain.entities.journal_entry import JournalEntry
from domain.entities.audit_event import AuditEvent
from application.use_cases.allocate_funds import (
    AllocateFundsUseCase,
    AllocateFundsInput,
    EnvelopeRepository,
    JournalRepository,
    AuditRepository
)

class MockEnvelopeRepository(EnvelopeRepository):
    def __init__(self, envelopes: Dict[str, BudgetEnvelope] = None):
        self.envelopes = envelopes or {}
        self.saved_calls = []

    async def find_by_id(self, envelope_id: str) -> BudgetEnvelope | None:
        return self.envelopes.get(envelope_id)

    async def save(self, envelope: BudgetEnvelope) -> BudgetEnvelope:
        self.saved_calls.append(envelope)
        self.envelopes[envelope.id] = envelope
        return envelope


class MockJournalRepository(JournalRepository):
    def __init__(self):
        self.saved_calls = []

    async def save(self, entry: JournalEntry) -> JournalEntry:
        self.saved_calls.append(entry)
        # Simulate DB returning with ID
        if not entry.id:
            entry.id = "mock-id"
        return entry


class MockAuditRepository(AuditRepository):
    def __init__(self):
        self.saved_calls = []

    async def save(self, event: AuditEvent) -> AuditEvent:
        self.saved_calls.append(event)
        return event


@pytest.fixture
def source_envelope():
    return BudgetEnvelope(
        id="source-123",
        user_id="user-1",
        name="Pronto para Atribuir",
        allocated=Decimal("1000.00"),
        spent=Decimal("200.00")
    )


@pytest.fixture
def target_envelope():
    return BudgetEnvelope(
        id="target-123",
        user_id="user-1",
        name="Mercado",
        allocated=Decimal("50.00"),
        spent=Decimal("0.00")
    )


@pytest.mark.asyncio
async def test_allocate_funds_success(source_envelope, target_envelope):
    repo_env = MockEnvelopeRepository({"source-123": source_envelope, "target-123": target_envelope})
    repo_jour = MockJournalRepository()
    repo_audit = MockAuditRepository()

    use_case = AllocateFundsUseCase(repo_env, repo_jour, repo_audit)
    input_dto = AllocateFundsInput(
        user_id="user-1",
        source_envelope_id="source-123",
        target_envelope_id="target-123",
        amount=Decimal("300.00"),
        note="Allocation Test"
    )

    output = await use_case.execute(input_dto)

    # 1. Check returned envelopes updated successfully
    assert output.source_envelope.allocated == Decimal("700.00")
    assert output.target_envelope.allocated == Decimal("350.00")

    # 2. Check repositories were called
    assert len(repo_env.saved_calls) == 2
    assert len(repo_jour.saved_calls) == 1
    assert len(repo_audit.saved_calls) == 1

    # 3. Check Journal Entry Correctness
    journal = repo_jour.saved_calls[0]
    assert journal.debit_envelope_id == "source-123"
    assert journal.credit_envelope_id == "target-123"
    assert journal.amount == Decimal("300.00")
    assert journal.user_id == "user-1"


@pytest.mark.asyncio
async def test_allocate_funds_insufficient_funds(source_envelope, target_envelope):
    repo_env = MockEnvelopeRepository({"source-123": source_envelope, "target-123": target_envelope})
    use_case = AllocateFundsUseCase(repo_env, MockJournalRepository(), MockAuditRepository())
    
    # Available in source_envelope is 1000 - 200 = 800
    input_dto = AllocateFundsInput(
        user_id="user-1",
        source_envelope_id="source-123",
        target_envelope_id="target-123",
        amount=Decimal("801.00"), # 1 over available
    )

    with pytest.raises(ValueError, match="Insufficient funds"):
        await use_case.execute(input_dto)


@pytest.mark.asyncio
async def test_allocate_funds_wrong_user(source_envelope, target_envelope):
    repo_env = MockEnvelopeRepository({"source-123": source_envelope, "target-123": target_envelope})
    use_case = AllocateFundsUseCase(repo_env, MockJournalRepository(), MockAuditRepository())
    
    input_dto = AllocateFundsInput(
        user_id="user-hacker",
        source_envelope_id="source-123",
        target_envelope_id="target-123",
        amount=Decimal("100.00"),
    )

    with pytest.raises(PermissionError, match="Access denied"):
        await use_case.execute(input_dto)


@pytest.mark.asyncio
async def test_allocate_negative_amount(source_envelope, target_envelope):
    repo_env = MockEnvelopeRepository({"source-123": source_envelope, "target-123": target_envelope})
    use_case = AllocateFundsUseCase(repo_env, MockJournalRepository(), MockAuditRepository())
    
    input_dto = AllocateFundsInput(
        user_id="user-1",
        source_envelope_id="source-123",
        target_envelope_id="target-123",
        amount=Decimal("-10.00"),
    )

    with pytest.raises(ValueError, match="must be positive"):
        await use_case.execute(input_dto)
