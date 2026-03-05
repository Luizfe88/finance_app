"""
API Router: Audit Trail (Read-Only)

Endpoints:
  GET /audit/events   → paginated audit log with integrity verification
  GET /audit/verify   → verify checksum integrity for recent events
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.repositories_v2 import SQLAlchemyAuditRepository
from domain.entities.audit_event import AuditEvent

router = APIRouter(prefix="/audit", tags=["Audit Trail"])
from interfaces.api.dependencies.auth import get_current_user_id


class AuditEventResponse(BaseModel):
    id: str
    event_type: str
    payload: dict
    checksum: str
    integrity_valid: bool
    created_at: str


def _event_to_response(e: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=e.id,
        event_type=e.event_type.value,
        payload=e.payload,
        checksum=e.checksum,
        integrity_valid=e.verify_integrity(),
        created_at=e.created_at.isoformat(),
    )


@router.get("/events", response_model=list[AuditEventResponse])
async def list_audit_events(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    """Read-only audit trail with tamper-detection status per event."""
    repo = SQLAlchemyAuditRepository(session)
    events = await repo.list_by_user(
        user_id=user_id, limit=limit, offset=offset
    )
    return [_event_to_response(e) for e in events]


@router.get("/verify")
async def verify_audit_integrity(
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session),
):
    """Verify SHA-256 checksum integrity of the most recent 100 audit events."""
    repo = SQLAlchemyAuditRepository(session)
    events = await repo.list_by_user(user_id=user_id, limit=100)

    total = len(events)
    valid = sum(1 for e in events if e.verify_integrity())
    tampered = [e.id for e in events if not e.verify_integrity()]

    return {
        "total_checked": total,
        "valid_count": valid,
        "tampered_count": len(tampered),
        "tampered_ids": tampered,
        "integrity_status": "CLEAN" if not tampered else "COMPROMISED",
    }
