"""
Repository Protocol: AccountRepository
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from domain.entities.account import Account


@runtime_checkable
class AccountRepository(Protocol):
    async def save(self, account: Account) -> Account: ...
    async def find_by_id(self, account_id: str) -> Optional[Account]: ...
    async def list_by_user(self, user_id: str) -> list[Account]: ...
    async def delete(self, account_id: str) -> bool: ...
    async def delete_all_by_user(self, user_id: str) -> int: ...
