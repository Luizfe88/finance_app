"""
Infrastructure: In-Memory Transaction Repository

For testing and development — no database required.
Implements the same TransactionRepository protocol.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from domain.entities.transaction import Transaction
from application.protocols.transaction_repository import TransactionRepository


class InMemoryTransactionRepository:
    """Thread-unsafe in-memory store. Use only in tests or for demos."""

    def __init__(self) -> None:
        self._store: dict[str, Transaction] = {}

    async def save(self, transaction: Transaction) -> Transaction:
        self._store[transaction.id] = transaction
        return transaction

    async def save_many(self, transactions: list[Transaction]) -> list[Transaction]:
        for t in transactions:
            self._store[t.id] = t
        return transactions

    async def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        return self._store.get(transaction_id)

    async def find_by_fit_id(self, fit_id: str, user_id: str) -> Optional[Transaction]:
        return next(
            (t for t in self._store.values() if t.fit_id == fit_id and t.user_id == user_id),
            None,
        )

    async def list_by_user(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        results = [t for t in self._store.values() if t.user_id == user_id]
        if account_id:
            results = [t for t in results if t.account_id == account_id]
        if category:
            results = [t for t in results if t.category == category]
        if start_date:
            results = [t for t in results if t.date >= start_date]
        if end_date:
            results = [t for t in results if t.date <= end_date]
        results.sort(key=lambda t: t.date, reverse=True)
        return results[offset: offset + limit]

    async def count_by_user(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        results = [t for t in self._store.values() if t.user_id == user_id]
        if account_id:
            results = [t for t in results if t.account_id == account_id]
        if start_date:
            results = [t for t in results if t.date >= start_date]
        if end_date:
            results = [t for t in results if t.date <= end_date]
        return len(results)

    async def delete(self, transaction_id: str) -> bool:
        if transaction_id in self._store:
            del self._store[transaction_id]
            return True
        return False

    async def delete_all_by_user(self, user_id: str) -> int:
        keys = [k for k, t in self._store.items() if t.user_id == user_id]
        for k in keys:
            del self._store[k]
        return len(keys)

    def seed(self, transactions: list[Transaction]) -> None:
        """Helper for tests: directly populate the store."""
        for t in transactions:
            self._store[t.id] = t
