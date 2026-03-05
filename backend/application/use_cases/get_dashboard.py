"""
Use Case: GetDashboardUseCase

Aggregates transactions into chart-ready structures for the frontend.
Returns data pre-formatted for Recharts (React) or ECharts.

Output includes:
  - Monthly cash flow (income vs expenses per month) → AreaChart
  - Spending by category → PieChart / RadialChart
  - Summary cards (total balance, income, expenses, savings rate)
  - Top 5 expense categories
  - Recent transactions (last 5)
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from domain.entities.transaction import Transaction, TransactionType
from application.protocols.transaction_repository import TransactionRepository


@dataclass
class MonthlyCashFlow:
    """Data point for monthly income/expense chart (Recharts AreaChart)."""
    month: str          # "2025-01", "2025-02", etc.
    income: float
    expenses: float
    balance: float      # income - expenses


@dataclass
class CategoryBreakdown:
    """Data point for category pie chart."""
    category: str
    amount: float
    percentage: float
    color: str          # Hex color for frontend


@dataclass
class DashboardSummary:
    total_balance: float
    total_income: float
    total_expenses: float
    savings_rate: float         # (income - expenses) / income * 100
    transaction_count: int


@dataclass
class DashboardOutput:
    """
    Chart-ready dashboard payload.
    Structured to directly feed Recharts components in the frontend.
    """
    summary: DashboardSummary
    monthly_cash_flow: list[MonthlyCashFlow]     # AreaChart data
    category_breakdown: list[CategoryBreakdown]   # PieChart data
    recent_transactions: list[Transaction]        # Last 5 transactions
    period_start: str
    period_end: str


# Color palette for categories (calm, fintech-appropriate)
CATEGORY_COLORS = {
    "Alimentação": "#6366F1",
    "Transporte": "#8B5CF6",
    "Moradia": "#EC4899",
    "Saúde": "#14B8A6",
    "Educação": "#F59E0B",
    "Lazer": "#10B981",
    "Roupas": "#F97316",
    "Serviços": "#3B82F6",
    "Outros": "#6B7280",
}


class GetDashboardUseCase:
    """
    Use Case: Build a complete dashboard data payload for the frontend.

    Default period: last 6 months.
    """

    def __init__(self, repository: TransactionRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        account_id: Optional[str] = None,
        months_back: int = 6,
    ) -> DashboardOutput:
        # Define period
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30 * months_back)

        # Fetch all transactions for period
        transactions = await self._repository.list_by_user(
            user_id=user_id,
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Large limit to get all for aggregation
            offset=0,
        )

        # --- Aggregate summary ---
        total_income = sum(
            t.amount for t in transactions if t.transaction_type == TransactionType.CREDIT
        )
        total_expenses = sum(
            t.amount for t in transactions if t.transaction_type == TransactionType.DEBIT
        )
        savings_rate = (
            float((total_income - total_expenses) / total_income * 100)
            if total_income > 0
            else 0.0
        )

        summary = DashboardSummary(
            total_balance=float(total_income - total_expenses),
            total_income=float(total_income),
            total_expenses=float(total_expenses),
            savings_rate=round(savings_rate, 1),
            transaction_count=len(transactions),
        )

        # --- Monthly cash flow ---
        monthly_income: dict[str, Decimal] = defaultdict(Decimal)
        monthly_expenses: dict[str, Decimal] = defaultdict(Decimal)

        for txn in transactions:
            month_key = txn.date.strftime("%Y-%m")
            if txn.transaction_type == TransactionType.CREDIT:
                monthly_income[month_key] += txn.amount
            else:
                monthly_expenses[month_key] += txn.amount

        # Generate all months in range (even empty ones)
        all_months = []
        current = start_date.replace(day=1)
        while current <= end_date:
            all_months.append(current.strftime("%Y-%m"))
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        monthly_flow = [
            MonthlyCashFlow(
                month=m,
                income=float(monthly_income.get(m, Decimal("0"))),
                expenses=float(monthly_expenses.get(m, Decimal("0"))),
                balance=float(monthly_income.get(m, Decimal("0")) - monthly_expenses.get(m, Decimal("0"))),
            )
            for m in all_months
        ]

        # --- Category breakdown ---
        category_totals: dict[str, Decimal] = defaultdict(Decimal)
        for txn in transactions:
            if txn.transaction_type == TransactionType.DEBIT:
                category_totals[txn.category] += txn.amount

        total_for_categories = sum(category_totals.values()) or Decimal("1")
        category_breakdown = sorted(
            [
                CategoryBreakdown(
                    category=cat,
                    amount=float(amount),
                    percentage=round(float(amount / total_for_categories * 100), 1),
                    color=CATEGORY_COLORS.get(cat, "#6B7280"),
                )
                for cat, amount in category_totals.items()
            ],
            key=lambda x: x.amount,
            reverse=True,
        )

        # --- Recent transactions (last 5) ---
        recent = sorted(transactions, key=lambda t: t.date, reverse=True)[:5]

        return DashboardOutput(
            summary=summary,
            monthly_cash_flow=monthly_flow,
            category_breakdown=category_breakdown,
            recent_transactions=recent,
            period_start=start_date.strftime("%Y-%m-%d"),
            period_end=end_date.strftime("%Y-%m-%d"),
        )
