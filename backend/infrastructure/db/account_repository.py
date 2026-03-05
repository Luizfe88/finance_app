"""
Infrastructure: SQLAlchemy Account Repository Implementation
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.account import Account, AccountType
from infrastructure.db.models import AccountModel


class SQLAlchemyAccountRepository:
    """
    Concrete repository for Accounts using SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: AccountModel) -> Account:
        """Convert ORM model → domain entity."""
        return Account(
            id=model.id,
            user_id=model.user_id,
            bank_name=model.bank_name,
            bank_code=model.bank_code,
            masked_account_number=model.masked_account_number,
            account_type=AccountType(model.account_type),
            balance=Decimal(str(model.balance)),
            currency=model.currency,
            is_active=model.is_active,
            credit_limit=Decimal(str(model.credit_limit)) if model.credit_limit is not None else None,
            card_payment_envelope_id=model.card_payment_envelope_id,
            invoice_due_day=model.invoice_due_day,
            invoice_closing_day=model.invoice_closing_day,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Account) -> AccountModel:
        """Convert domain entity → ORM model."""
        return AccountModel(
            id=entity.id,
            user_id=entity.user_id,
            bank_name=entity.bank_name,
            bank_code=entity.bank_code,
            masked_account_number=entity.masked_account_number,
            account_type=entity.account_type.value,
            balance=entity.balance,
            currency=entity.currency,
            is_active=entity.is_active,
            credit_limit=entity.credit_limit,
            card_payment_envelope_id=entity.card_payment_envelope_id,
            invoice_due_day=entity.invoice_due_day,
            invoice_closing_day=entity.invoice_closing_day,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def save(self, account: Account) -> Account:
        model = self._to_model(account)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def find_by_id(self, account_id: str) -> Optional[Account]:
        result = await self._session.get(AccountModel, account_id)
        return self._to_entity(result) if result else None

    async def list_by_user(self, user_id: str, only_active: bool = True) -> list[Account]:
        stmt = select(AccountModel).where(AccountModel.user_id == user_id)
        if only_active:
            stmt = stmt.where(AccountModel.is_active == True)
        
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
