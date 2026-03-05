"""
Repository Protocol: TransactionRepository

Defines the abstract interface (contract) for transaction persistence.
Following the Dependency Inversion Principle: use cases depend ONLY on
this Protocol, never on concrete implementations (SQLAlchemy, memory, etc.)

This design allows:
  - InMemoryTransactionRepository for tests
  - SQLAlchemyTransactionRepository for production
  - Future: PluggyTransactionRepository (Open Finance)
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable
from datetime import datetime

from domain.entities.transaction import Transaction


@runtime_checkable
class TransactionRepository(Protocol):
    """
    Abstract contract for transaction data access.
    All methods are async for non-blocking I/O.
    """

    async def save(self, transaction: Transaction) -> Transaction:
        """Persist a transaction. Returns the saved entity (with DB-generated fields)."""
        ...

    async def save_many(self, transactions: list[Transaction]) -> list[Transaction]:
        """Bulk insert — uses upsert logic based on fit_id for deduplication."""
        ...

    async def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Retrieve a single transaction by its UUID."""
        ...

    async def find_by_fit_id(self, fit_id: str, user_id: str) -> Optional[Transaction]:
        """Find transaction by OFX fit_id for deduplication."""
        ...

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
        """List transactions with filtering and pagination."""
        ...

    async def count_by_user(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        """Count total transactions (for pagination metadata)."""
        ...

    async def delete(self, transaction_id: str) -> bool:
        """Delete a single transaction. Returns True if found and deleted."""
        ...

    async def delete_all_by_user(self, user_id: str) -> int:
        """
        LGPD: Right to be forgotten.
        Deletes ALL transactions for a user. Returns count of deleted records.
        """
        ...
