"""
Infrastructure: SQLAlchemy Repository Implementation

Concrete implementation of TransactionRepository Protocol using SQLAlchemy.
This is the production-ready adapter for PostgreSQL (or SQLite in dev).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.transaction import Transaction, TransactionType, TransactionStatus, TransactionRole, FundingState, PaymentMethod
from application.protocols.transaction_repository import TransactionRepository
from infrastructure.db.models import TransactionModel


class SQLAlchemyTransactionRepository:
    """
    Concrete repository using SQLAlchemy async session.
    Injected into use cases via FastAPI's dependency injection.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: TransactionModel) -> Transaction:
        """Convert ORM model → domain entity."""
        return Transaction(
            id=model.id,
            user_id=model.user_id,
            account_id=model.account_id,
            amount=Decimal(str(model.amount)),
            currency=model.currency,
            description=model.description,
            category=model.category,
            date=model.date,
            transaction_type=TransactionType(model.transaction_type),
            status=TransactionStatus(model.status),
            payment_method=PaymentMethod(model.payment_method),
            envelope_id=model.envelope_id,
            funding_state=FundingState(model.funding_state),
            is_recurring=model.is_recurring,
            recurrence_rule=model.recurrence_rule,
            role=TransactionRole(model.role),
            parent_id=model.parent_id,
            installment_seq=model.installment_seq,
            installment_total=model.installment_total,
            idempotency_key=model.idempotency_key,
            fit_id=model.fit_id,
            memo=model.memo,
            payee=model.payee,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: Transaction) -> TransactionModel:
        """Convert domain entity → ORM model."""
        return TransactionModel(
            id=entity.id,
            user_id=entity.user_id,
            account_id=entity.account_id,
            amount=entity.amount,
            currency=entity.currency,
            description=entity.description,
            category=entity.category,
            date=entity.date,
            transaction_type=entity.transaction_type.value,
            status=entity.status.value,
            payment_method=entity.payment_method.value,
            envelope_id=entity.envelope_id,
            funding_state=entity.funding_state.value,
            is_recurring=entity.is_recurring,
            recurrence_rule=entity.recurrence_rule,
            role=entity.role.value,
            parent_id=entity.parent_id,
            installment_seq=entity.installment_seq,
            installment_total=entity.installment_total,
            idempotency_key=entity.idempotency_key,
            fit_id=entity.fit_id,
            memo=entity.memo,
            payee=entity.payee,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def save(self, transaction: Transaction) -> Transaction:
        model = self._to_model(transaction)
        self._session.add(model)
        await self._session.commit()
        await self._session.refresh(model)
        return self._to_entity(model)

    async def save_many(self, transactions: list[Transaction]) -> list[Transaction]:
        models = [self._to_model(t) for t in transactions]
        self._session.add_all(models)
        await self._session.commit()
        return [self._to_entity(m) for m in models]

    async def find_by_id(self, transaction_id: str) -> Optional[Transaction]:
        result = await self._session.get(TransactionModel, transaction_id)
        return self._to_entity(result) if result else None

    async def find_by_fit_id(self, fit_id: str, user_id: str) -> Optional[Transaction]:
        stmt = select(TransactionModel).where(
            and_(
                TransactionModel.fit_id == fit_id,
                TransactionModel.user_id == user_id,
            )
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

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
        conditions = [TransactionModel.user_id == user_id]
        if account_id:
            conditions.append(TransactionModel.account_id == account_id)
        if category:
            conditions.append(TransactionModel.category == category)
        if start_date:
            conditions.append(TransactionModel.date >= start_date)
        if end_date:
            conditions.append(TransactionModel.date <= end_date)

        stmt = (
            select(TransactionModel)
            .where(and_(*conditions))
            .order_by(TransactionModel.date.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def count_by_user(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> int:
        conditions = [TransactionModel.user_id == user_id]
        if account_id:
            conditions.append(TransactionModel.account_id == account_id)
        if start_date:
            conditions.append(TransactionModel.date >= start_date)
        if end_date:
            conditions.append(TransactionModel.date <= end_date)

        stmt = select(func.count(TransactionModel.id)).where(and_(*conditions))
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def delete(self, transaction_id: str) -> bool:
        model = await self._session.get(TransactionModel, transaction_id)
        if not model:
            return False
        await self._session.delete(model)
        await self._session.commit()
        return True

    async def delete_all_by_user(self, user_id: str) -> int:
        """LGPD: Delete all transactions for a user (right to be forgotten)."""
        stmt = delete(TransactionModel).where(TransactionModel.user_id == user_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount
