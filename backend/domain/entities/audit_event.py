"""
Domain Entity: AuditEvent

Immutable audit trail for all financial governance events.

Tamper-detection: each event stores a SHA-256 checksum of its payload.
Any modification to the stored payload will invalidate the checksum.

LGPD: AuditEvents survive the user deletion process for the legally
mandated retention period (5 years for financial records in Brazil).
Only PII is anonymized on deletion — financial amounts and event types
are preserved for regulatory compliance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class AuditEventType(str, Enum):
    # Budget / ZBB
    ENVELOPE_CREATED = "ENVELOPE_CREATED"
    ENVELOPE_ALLOCATION = "ENVELOPE_ALLOCATION"
    READY_TO_ASSIGN_RECEIPT = "READY_TO_ASSIGN_RECEIPT"

    # Credit Card Engine
    CREDIT_PURCHASE_FUNDED = "CREDIT_PURCHASE_FUNDED"
    CREDIT_PURCHASE_UNFUNDED = "CREDIT_PURCHASE_UNFUNDED"
    CREDIT_PURCHASE_POSITIVE = "CREDIT_PURCHASE_POSITIVE"
    CREDIT_INVOICE_PAYMENT = "CREDIT_INVOICE_PAYMENT"

    # Installments & Subscriptions
    INSTALLMENT_GROUP_CREATED = "INSTALLMENT_GROUP_CREATED"
    SUBSCRIPTION_BILLED = "SUBSCRIPTION_BILLED"
    SUBSCRIPTION_OVERDUE = "SUBSCRIPTION_OVERDUE"

    # Open Finance
    IDEMPOTENT_IMPORT = "IDEMPOTENT_IMPORT"
    DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"

    # LGPD / Security
    ACCOUNT_DELETION_REQUESTED = "ACCOUNT_DELETION_REQUESTED"
    ACCOUNT_DATA_ERASED = "ACCOUNT_DATA_ERASED"
    SENSITIVE_FIELD_ACCESSED = "SENSITIVE_FIELD_ACCESSED"

    # Generic
    BALANCE_ADJUSTMENT = "BALANCE_ADJUSTMENT"


def _compute_checksum(payload: dict[str, Any]) -> str:
    """SHA-256 checksum of the canonical JSON representation of payload."""
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class AuditEvent:
    """
    Immutable event record for financial governance audit trail.

    Rules:
      1. NEVER modify an existing AuditEvent — create a compensating one.
      2. checksum must equal SHA-256(json(payload)) — verified on read.
      3. PII fields (user_id) may be anonymized on LGPD deletion,
         but event_type, amount, and created_at must be preserved.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    event_type: AuditEventType = AuditEventType.BALANCE_ADJUSTMENT
    payload: dict = field(default_factory=dict)          # Structured event data
    checksum: str = ""                                    # SHA-256 of payload
    ip_address: str | None = None                         # Optional: for security events
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self) -> None:
        # Auto-compute checksum if not provided
        if not self.checksum:
            self.checksum = _compute_checksum(self.payload)

    def verify_integrity(self) -> bool:
        """Returns True if payload has not been tampered with."""
        return self.checksum == _compute_checksum(self.payload)

    def anonymize_pii(self) -> None:
        """LGPD: Remove user PII while preserving financial record."""
        self.user_id = "DELETED"
        # Recompute checksum after anonymization
        # Note: we don't recompute from payload since payload may contain PII
        # Instead we mark it as anonymized
        self.payload = {
            k: "[REDACTED]" if k in ("user_id", "email", "name", "cpf") else v
            for k, v in self.payload.items()
        }
        self.checksum = _compute_checksum(self.payload)

    @classmethod
    def create(
        cls,
        user_id: str,
        event_type: AuditEventType,
        payload: dict[str, Any],
        ip_address: str | None = None,
    ) -> "AuditEvent":
        """Factory method — ensures checksum is always computed."""
        checksum = _compute_checksum(payload)
        return cls(
            user_id=user_id,
            event_type=event_type,
            payload=payload,
            checksum=checksum,
            ip_address=ip_address,
        )

    def __repr__(self) -> str:
        return (
            f"AuditEvent(type={self.event_type.value!r}, "
            f"user={self.user_id!r}, "
            f"created_at={self.created_at.isoformat()}, "
            f"valid={self.verify_integrity()})"
        )
