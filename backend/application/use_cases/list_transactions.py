"""
Use Case: ListTransactionsUseCase

Retrieves a paginated, filtered list of transactions for a user.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from domain.entities.transaction import Transaction
from application.protocols.transaction_repository import TransactionRepository


@dataclass
class ListTransactionsInput:
    user_id: str
    account_id: Optional[str] = None
    category: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50
    offset: int = 0


@dataclass
class ListTransactionsOutput:
    transactions: list[Transaction]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + self.limit < self.total


class ListTransactionsUseCase:
    """Use Case: List transactions with filtering and pagination."""

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    async def execute(self, input_data: ListTransactionsInput) -> ListTransactionsOutput:
        transactions = await self._repository.list_by_user(
            user_id=input_data.user_id,
            account_id=input_data.account_id,
            category=input_data.category,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
            limit=input_data.limit,
            offset=input_data.offset,
        )

        total = await self._repository.count_by_user(
            user_id=input_data.user_id,
            account_id=input_data.account_id,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
        )

        return ListTransactionsOutput(
            transactions=transactions,
            total=total,
            limit=input_data.limit,
            offset=input_data.offset,
        )
