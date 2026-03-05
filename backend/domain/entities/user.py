"""
Domain Entity: User

Includes LGPD-specific flags for data minimization and right-to-erasure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class DataMinimizationLevel(str, Enum):
    """Controls how much data is collected about the user (LGPD)."""
    MINIMAL = "MINIMAL"     # Only email + hashed password
    STANDARD = "STANDARD"   # + name, preferences
    FULL = "FULL"           # + profile picture, detailed demographics


@dataclass
class User:
    """
    Application user entity.

    LGPD fields:
        - data_minimization_level: controls what personal data is stored
        - deletion_requested_at: when set, account deletion was requested
        - consent_given_at: timestamp of explicit data processing consent
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    hashed_password: str = ""  # Never store plaintext passwords
    name: Optional[str] = None
    is_active: bool = True
    data_minimization_level: DataMinimizationLevel = DataMinimizationLevel.STANDARD
    consent_given_at: Optional[datetime] = None
    deletion_requested_at: Optional[datetime] = None   # LGPD: right to be forgotten
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_deletion_request(self) -> bool:
        return self.deletion_requested_at is not None

    def request_deletion(self) -> None:
        """LGPD: register a data deletion request."""
        self.deletion_requested_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
