"""
Infrastructure: SQLAlchemy Repositories for V2 Entities

Concrete implementations for:
  - BudgetEnvelopeRepository
  - JournalEntryRepository
  - InstallmentGroupRepository
  - SubscriptionRepository
  - AuditEventRepository
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.budget_envelope import BudgetEnvelope, SystemEnvelope
from domain.entities.journal_entry import JournalEntry
from domain.entities.installment_group import InstallmentGroup, InstallmentGroupStatus
from domain.entities.subscription import Subscription, PaymentMethod, SubscriptionStatus
from domain.entities.audit_event import AuditEvent, AuditEventType
from infrastructure.db.models import (
    BudgetEnvelopeModel, JournalEntryModel,
    InstallmentGroupModel, SubscriptionModel, AuditEventModel,
)


# ── BudgetEnvelope Repository ──────────────────────────────────────────────────
class SQLAlchemyEnvelopeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: BudgetEnvelopeModel) -> BudgetEnvelope:
        return BudgetEnvelope(
            id=m.id, user_id=m.user_id, name=m.name, icon=m.icon,
            color=m.color, month=m.month,
            allocated=Decimal(str(m.allocated)), spent=Decimal(str(m.spent)),
            is_system=m.is_system, category_id=m.category_id,
            created_at=m.created_at, updated_at=m.updated_at,
        )

    def _to_model(self, e: BudgetEnvelope) -> BudgetEnvelopeModel:
        return BudgetEnvelopeModel(
            id=e.id, user_id=e.user_id, name=e.name, icon=e.icon,
            color=e.color, month=e.month,
            allocated=e.allocated, spent=e.spent,
            is_system=e.is_system, category_id=e.category_id,
            created_at=e.created_at, updated_at=e.updated_at,
        )

    async def find_by_id(self, eid: str) -> Optional[BudgetEnvelope]:
        m = await self._session.get(BudgetEnvelopeModel, eid)
        return self._to_entity(m) if m else None

    async def find_by_name_and_month(
        self, user_id: str, name: str, month: str
    ) -> Optional[BudgetEnvelope]:
        stmt = select(BudgetEnvelopeModel).where(
            and_(
                BudgetEnvelopeModel.user_id == user_id,
                BudgetEnvelopeModel.name == name,
                BudgetEnvelopeModel.month == month,
            )
        )
        result = await self._session.execute(stmt)
        m = result.scalar_one_or_none()
        return self._to_entity(m) if m else None

    async def list_by_user_month(self, user_id: str, month: str) -> list[BudgetEnvelope]:
        stmt = select(BudgetEnvelopeModel).where(
            and_(
                BudgetEnvelopeModel.user_id == user_id,
                BudgetEnvelopeModel.month == month,
            )
        ).order_by(BudgetEnvelopeModel.is_system.desc(), BudgetEnvelopeModel.name)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def save(self, envelope: BudgetEnvelope) -> BudgetEnvelope:
        existing = await self._session.get(BudgetEnvelopeModel, envelope.id)
        if existing:
            existing.allocated = envelope.allocated
            existing.spent = envelope.spent
            existing.updated_at = datetime.utcnow()
        else:
            self._session.add(self._to_model(envelope))
        await self._session.commit()
        return envelope

    async def ensure_system_envelopes(self, user_id: str, month: str) -> list[BudgetEnvelope]:
        """Create system envelopes for a month if they don't exist yet."""
        system_defs = [
            (SystemEnvelope.READY_TO_ASSIGN, "📥", "#F59E0B"),
            (SystemEnvelope.CREDIT_CARD_PAYMENT, "💳", "#EF4444"),
            (SystemEnvelope.INVESTMENTS, "📈", "#10B981"),
        ]
        created = []
        for name, icon, color in system_defs:
            existing = await self.find_by_name_and_month(user_id, name, month)
            if not existing:
                env = BudgetEnvelope(
                    user_id=user_id, name=name, icon=icon, color=color,
                    month=month, is_system=True,
                )
                env = await self.save(env)
                created.append(env)
        return created

    async def delete_all_by_user(self, user_id: str) -> int:
        stmt = delete(BudgetEnvelopeModel).where(BudgetEnvelopeModel.user_id == user_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount


# ── JournalEntry Repository ────────────────────────────────────────────────────
class SQLAlchemyJournalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: JournalEntryModel) -> JournalEntry:
        return JournalEntry(
            id=m.id, user_id=m.user_id,
            debit_envelope_id=m.debit_envelope_id,
            credit_envelope_id=m.credit_envelope_id,
            amount=Decimal(str(m.amount)), note=m.note,
            event_type=m.event_type, transaction_id=m.transaction_id,
            created_at=m.created_at,
        )

    async def save(self, entry: JournalEntry) -> JournalEntry:
        model = JournalEntryModel(
            id=entry.id, user_id=entry.user_id,
            debit_envelope_id=entry.debit_envelope_id,
            credit_envelope_id=entry.credit_envelope_id,
            amount=entry.amount, note=entry.note,
            event_type=entry.event_type,
            transaction_id=entry.transaction_id,
            created_at=entry.created_at,
        )
        self._session.add(model)
        await self._session.commit()
        return entry

    async def list_by_user(self, user_id: str, limit: int = 100) -> list[JournalEntry]:
        stmt = select(JournalEntryModel).where(
            JournalEntryModel.user_id == user_id
        ).order_by(JournalEntryModel.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]


# ── InstallmentGroup Repository ────────────────────────────────────────────────
class SQLAlchemyInstallmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: InstallmentGroupModel) -> InstallmentGroup:
        return InstallmentGroup(
            id=m.id, user_id=m.user_id, account_id=m.account_id,
            envelope_id=m.envelope_id, description=m.description,
            merchant=m.merchant, total_amount=Decimal(str(m.total_amount)),
            installment_count=m.installment_count, start_date=m.start_date,
            status=InstallmentGroupStatus(m.status),
            created_at=m.created_at, updated_at=m.updated_at,
        )

    async def save(self, group: InstallmentGroup) -> InstallmentGroup:
        existing = await self._session.get(InstallmentGroupModel, group.id)
        if existing:
            existing.status = group.status
            existing.updated_at = datetime.utcnow()
        else:
            self._session.add(InstallmentGroupModel(
                id=group.id, user_id=group.user_id, account_id=group.account_id,
                envelope_id=group.envelope_id, description=group.description,
                merchant=group.merchant, total_amount=group.total_amount,
                installment_count=group.installment_count, start_date=group.start_date,
                status=group.status.value,
            ))
        await self._session.commit()
        return group

    async def list_active_by_user(self, user_id: str) -> list[InstallmentGroup]:
        stmt = select(InstallmentGroupModel).where(
            and_(
                InstallmentGroupModel.user_id == user_id,
                InstallmentGroupModel.status == InstallmentGroupStatus.ACTIVE.value,
            )
        ).order_by(InstallmentGroupModel.start_date)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_id(self, gid: str) -> Optional[InstallmentGroup]:
        m = await self._session.get(InstallmentGroupModel, gid)
        return self._to_entity(m) if m else None

    async def delete_all_by_user(self, user_id: str) -> int:
        stmt = delete(InstallmentGroupModel).where(InstallmentGroupModel.user_id == user_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount


# ── Subscription Repository ────────────────────────────────────────────────────
class SQLAlchemySubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: SubscriptionModel) -> Subscription:
        return Subscription(
            id=m.id, user_id=m.user_id, name=m.name, description=m.description,
            amount=Decimal(str(m.amount)), currency=m.currency,
            payment_method=PaymentMethod(m.payment_method),
            account_id=m.account_id, envelope_id=m.envelope_id,
            billing_day=m.billing_day, next_billing_date=m.next_billing_date,
            status=SubscriptionStatus(m.status),
            created_at=m.created_at, updated_at=m.updated_at,
        )

    async def save(self, sub: Subscription) -> Subscription:
        existing = await self._session.get(SubscriptionModel, sub.id)
        if existing:
            existing.status = sub.status.value
            existing.next_billing_date = sub.next_billing_date
            existing.amount = sub.amount
            existing.updated_at = datetime.utcnow()
        else:
            self._session.add(SubscriptionModel(
                id=sub.id, user_id=sub.user_id, name=sub.name,
                description=sub.description, amount=sub.amount,
                currency=sub.currency, payment_method=sub.payment_method.value,
                account_id=sub.account_id, envelope_id=sub.envelope_id,
                billing_day=sub.billing_day, next_billing_date=sub.next_billing_date,
                status=sub.status.value,
            ))
        await self._session.commit()
        return sub

    async def list_due(self, user_id: str, before: datetime) -> list[Subscription]:
        stmt = select(SubscriptionModel).where(
            and_(
                SubscriptionModel.user_id == user_id,
                SubscriptionModel.status == SubscriptionStatus.ACTIVE.value,
                SubscriptionModel.next_billing_date <= before,
            )
        ).order_by(SubscriptionModel.next_billing_date)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_user(self, user_id: str) -> list[Subscription]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.user_id == user_id
        ).order_by(SubscriptionModel.next_billing_date)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def find_by_id(self, sid: str) -> Optional[Subscription]:
        m = await self._session.get(SubscriptionModel, sid)
        return self._to_entity(m) if m else None

    async def delete_all_by_user(self, user_id: str) -> int:
        stmt = delete(SubscriptionModel).where(SubscriptionModel.user_id == user_id)
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount


# ── AuditEvent Repository ──────────────────────────────────────────────────────
class SQLAlchemyAuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, m: AuditEventModel) -> AuditEvent:
        return AuditEvent(
            id=m.id, user_id=m.user_id,
            event_type=AuditEventType(m.event_type),
            payload=m.payload or {},
            checksum=m.checksum,
            ip_address=m.ip_address,
            created_at=m.created_at,
        )

    async def save(self, event: AuditEvent) -> AuditEvent:
        self._session.add(AuditEventModel(
            id=event.id, user_id=event.user_id,
            event_type=event.event_type.value,
            payload=event.payload,
            checksum=event.checksum,
            ip_address=event.ip_address,
            created_at=event.created_at,
        ))
        await self._session.commit()
        return event

    async def list_by_user(
        self, user_id: str, limit: int = 100, offset: int = 0
    ) -> list[AuditEvent]:
        stmt = select(AuditEventModel).where(
            AuditEventModel.user_id == user_id
        ).order_by(AuditEventModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def anonymize_user(self, user_id: str) -> int:
        """LGPD: Anonymize user PII in audit events while retaining financial records."""
        from sqlalchemy import update
        stmt = (
            update(AuditEventModel)
            .where(AuditEventModel.user_id == user_id)
            .values(user_id="DELETED")
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount
