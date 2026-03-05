"""
Pydantic Schemas: Account API Models
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    bank_name: str
    bank_code: Optional[str] = None
    masked_account_number: str
    account_type: str
    balance: float
    currency: str
    is_active: bool
    created_at: datetime


class AccountCreate(BaseModel):
    bank_name: str
    bank_code: Optional[str] = None
    masked_account_number: str = "****"
    account_type: str = "CHECKING"
    balance: float = 0.0
    currency: str = "BRL"
