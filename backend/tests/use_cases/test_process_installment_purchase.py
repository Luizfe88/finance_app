import pytest
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, Optional

from domain.entities.account import Account, AccountType
from domain.entities.transaction import Transaction
from domain.entities.installment_group import InstallmentGroup
from application.use_cases.process_installment_purchase import (
    ProcessInstallmentPurchaseUseCase,
    InstallmentPurchaseInput,
    TransactionRepository,
    AccountRepository
)


class MockTransactionRepository(TransactionRepository):
    def __init__(self):
        self.saved_txns = []

    async def save(self, transaction: Transaction) -> Transaction:
        self.saved_txns.append(transaction)
        return transaction

    async def save_many(self, transactions: list[Transaction]) -> list[Transaction]:
        self.saved_txns.extend(transactions)
        return transactions

    async def find_by_id(self, transaction_id: str) -> Optional[Transaction]: return None
    async def find_by_user(self, user_id: str) -> list[Transaction]: return []
    async def find_by_fit_id(self, fit_id: str, user_id: str) -> Optional[Transaction]: return None
    async def delete(self, transaction_id: str) -> bool: return True


class MockAccountRepository(AccountRepository):
    def __init__(self, accounts: Dict[str, Account] = None):
        self.accounts = accounts or {}

    async def find_by_id(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)

    async def save(self, account: Account) -> Account: return account
    async def list_by_user(self, user_id: str) -> list[Account]: return []
    async def delete(self, account_id: str) -> bool: return True
    async def delete_all_by_user(self, user_id: str) -> int: return 0


@pytest.fixture
def cc_account():
    return Account(
        id="cc-123",
        user_id="user-1",
        bank_name="Nubank",
        account_type=AccountType.CREDIT_CARD,
        invoice_due_day=10,
        invoice_closing_day=3, # Closes on the 3rd, wins on the 10th
    )


@pytest.mark.asyncio
async def test_installment_before_closing_day(cc_account):
    """
    Scenario:
    Vence: 10. Fecha: 3.
    Compra: 20-Mar.
    20-Mar is BEFORE the closing of the 10-Apr invoice (which is 03-Apr).
    Expectation: 1st installment due 10-Apr.
    """
    txn_repo = MockTransactionRepository()
    acc_repo = MockAccountRepository({"cc-123": cc_account})
    use_case = ProcessInstallmentPurchaseUseCase(txn_repo, acc_repo)

    purchase_date = datetime(2026, 3, 20)
    inp = InstallmentPurchaseInput(
        user_id="user-1",
        account_id="cc-123",
        amount=Decimal("900.00"),
        description="Monitor Gamer",
        category="Eletrônicos",
        installment_count=3,
        purchase_date=purchase_date
    )

    output = await use_case.execute(inp)

    assert len(output.transactions) == 3
    # 1st installment: 10-April
    assert output.transactions[0].date.date() == date(2026, 4, 10)
    # 2nd installment: 10-May
    assert output.transactions[1].date.date() == date(2026, 5, 10)
    # 3rd installment: 10-June
    assert output.transactions[2].date.date() == date(2026, 6, 10)
    
    # Check amounts
    assert output.transactions[0].amount == Decimal("300.00")


@pytest.mark.asyncio
async def test_installment_after_closing_day(cc_account):
    """
    Scenario:
    Vence: 10. Fecha: 3.
    Compra: 04-Apr.
    04-Apr is AFTER the closing of the 10-Apr invoice (which was 03-Apr).
    Expectation: 1st installment due 10-May.
    """
    txn_repo = MockTransactionRepository()
    acc_repo = MockAccountRepository({"cc-123": cc_account})
    use_case = ProcessInstallmentPurchaseUseCase(txn_repo, acc_repo)

    purchase_date = datetime(2026, 4, 4)
    inp = InstallmentPurchaseInput(
        user_id="user-1",
        account_id="cc-123",
        amount=Decimal("300.00"),
        description="Jantar",
        category="Alimentação",
        installment_count=2,
        purchase_date=purchase_date
    )

    output = await use_case.execute(inp)

    assert len(output.transactions) == 2
    # 1st installment: 10-May
    assert output.transactions[0].date.date() == date(2026, 5, 10)
    # 2nd installment: 10-June
    assert output.transactions[1].date.date() == date(2026, 6, 10)


@pytest.mark.asyncio
async def test_rounding_on_last_installment(cc_account):
    """900.01 divided by 3 should be 300.00, 300.00, 300.01"""
    txn_repo = MockTransactionRepository()
    acc_repo = MockAccountRepository({"cc-123": cc_account})
    use_case = ProcessInstallmentPurchaseUseCase(txn_repo, acc_repo)

    inp = InstallmentPurchaseInput(
        user_id="user-1",
        account_id="cc-123",
        amount=Decimal("900.01"),
        description="Test Rounding",
        category="Test",
        installment_count=3,
        purchase_date=datetime(2026, 3, 20)
    )

    output = await use_case.execute(inp)

    assert output.transactions[0].amount == Decimal("300.00")
    assert output.transactions[1].amount == Decimal("300.00")
    assert output.transactions[2].amount == Decimal("300.01")
    assert sum(t.amount for t in output.transactions) == Decimal("900.01")
