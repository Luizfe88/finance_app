"""
Pydantic Schemas: Transaction API Models

Separates API representation from domain entities.
Structures data for direct Recharts/ECharts consumption.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TransactionOut(BaseModel):
    """Transaction response schema — what the API returns."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    account_id: str
    amount: float
    currency: str
    description: str
    category: str
    date: datetime
    transaction_type: str
    status: str
    payment_method: str
    is_recurring: bool = False
    role: str = "STANDALONE"
    installment_seq: Optional[int] = None
    installment_total: Optional[int] = None
    memo: Optional[str] = None
    payee: Optional[str] = None
    created_at: datetime


class TransactionCreate(BaseModel):
    """Transaction creation request schema."""
    account_id: str
    amount: float = Field(gt=0, description="Absolute value, positive number")
    currency: str = "BRL"
    description: str = Field(min_length=1, max_length=500)
    category: str = "Outros"
    date: datetime
    transaction_type: str = Field(pattern="^(CREDIT|DEBIT|TRANSFER)$")
    payment_method: str = "CASH_PIX"
    installment_count: int = 1
    is_recurring: bool = False
    is_paid: bool = True  # Default to True for backward compatibility
    recurrence_rule: Optional[str] = None
    envelope_id: Optional[str] = None
    memo: Optional[str] = None
    payee: Optional[str] = None


class PaginatedTransactions(BaseModel):
    """Paginated list of transactions with metadata."""
    items: list[TransactionOut]
    total: int
    limit: int
    offset: int
    has_more: bool


class TransferCreate(BaseModel):
    """Schema for account-to-account transfers."""
    from_account_id: str
    to_account_id: str
    amount: float = Field(gt=0)
    date: datetime
    description: str = "Transferência"
    category: str = "Outros"
    memo: Optional[str] = None


# ---- Dashboard Schemas (Recharts/ECharts ready) ----

class MonthlyCashFlowPoint(BaseModel):
    """Data point for Area/Line chart — one data point per month."""
    month: str          # "2025-01"
    income: float
    expenses: float
    balance: float


class CategoryBreakdownPoint(BaseModel):
    """Data point for Pie/Radial chart — one segment per category."""
    category: str
    amount: float
    percentage: float
    color: str          # Hex color assigned by server


class DashboardSummaryOut(BaseModel):
    total_balance: float
    total_income: float
    total_expenses: float
    savings_rate: float


class DashboardOut(BaseModel):
    """
    Complete dashboard payload pre-structured for frontend chart components.

    monthly_cash_flow → feed directly into <AreaChart data={monthly_cash_flow}>
    category_breakdown → feed directly into <PieChart data={category_breakdown}>
    """
    summary: DashboardSummaryOut
    monthly_cash_flow: list[MonthlyCashFlowPoint]
    category_breakdown: list[CategoryBreakdownPoint]
    recent_transactions: list[TransactionOut]
    period_start: str
    period_end: str
    transaction_count: int


# ---- Import Schemas ----

class ImportResultOut(BaseModel):
    imported_count: int
    skipped_count: int
    message: str
