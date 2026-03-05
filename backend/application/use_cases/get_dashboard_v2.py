"""
Use Case: GetDashboardV2UseCase

Institutional-grade proactive dashboard payload.

Layout: Inverted Pyramid (answers "Como estou hoje?" in < 5 seconds)
  TOP    : KPIs — ready_to_assign, net_worth, alerts, savings_rate
  MIDDLE : cash_flow_projection (historical + 3-month forward)
  BOTTOM : envelope_health, credit_card_states, upcoming_commitments

Contextual Benchmarks:
  Every KPI includes vs_avg_pct (comparison to 6-month rolling average)
  to generate genuine insights rather than isolated numbers.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Protocol

from dateutil.relativedelta import relativedelta

from domain.entities.transaction import (
    Transaction, TransactionType, TransactionStatus, TransactionRole, FundingState
)
from domain.entities.budget_envelope import BudgetEnvelope
from domain.entities.subscription import Subscription
from domain.entities.installment_group import InstallmentGroup


# ── Repository Protocols ───────────────────────────────────────────────────────
class TransactionRepo(Protocol):
    async def list_by_user(
        self, user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 10000,
        offset: int = 0,
    ) -> list[Transaction]: ...


class EnvelopeRepo(Protocol):
    async def list_by_user_month(self, user_id: str, month: str) -> list[BudgetEnvelope]: ...
    async def find_by_name_and_month(self, user_id: str, name: str, month: str) -> Optional[BudgetEnvelope]: ...


class SubscriptionRepo(Protocol):
    async def list_due(self, user_id: str, before: datetime) -> list[Subscription]: ...


class InstallmentRepo(Protocol):
    async def list_active_by_user(self, user_id: str) -> list[InstallmentGroup]: ...


class AccountRepo(Protocol):
    async def list_by_user(self, user_id: str, only_active: bool = True) -> list[Account]: ...


# ── Output Schemas ─────────────────────────────────────────────────────────────
@dataclass
class KPICard:
    label: str
    value: float
    formatted: str          # Pre-formatted (R$1.234,56 or 23.4%)
    vs_avg_pct: float       # +10.0 means 10% above historical avg
    trend: str              # "UP" | "DOWN" | "STABLE"
    alert: bool = False
    alert_message: str = ""


@dataclass
class EnvelopeHealth:
    id: str
    name: str
    icon: str
    color: str
    allocated: float
    spent: float
    available: float
    utilization_pct: float
    is_overspent: bool
    is_system: bool


@dataclass
class CashFlowDataPoint:
    month: str              # "YYYY-MM"
    income: float
    expenses: float
    balance: float
    is_projected: bool      # True for future months


@dataclass
class CreditCardState:
    account_id: str
    account_name: str
    funded_amount: float        # Total in CC payment envelope
    unfunded_amount: float      # Total unfunded purchases this month
    credit_utilization_pct: float
    state_label: str            # "HEALTHY" | "AT_RISK" | "OVERSPENT"


@dataclass
class UpcomingCommitment:
    id: str
    label: str
    amount: float
    due_date: str
    commitment_type: str    # "INSTALLMENT" | "SUBSCRIPTION"
    is_overdue: bool


@dataclass
class DashboardV2Output:
    # KPI Strip (top)
    ready_to_assign: KPICard
    net_worth: KPICard
    savings_rate: KPICard
    total_income: KPICard
    total_expenses: KPICard

    # Charts (middle)
    cash_flow_projection: list[CashFlowDataPoint]   # 3 historical + 3 projected

    # Envelopes (middle-lower)
    envelope_health: list[EnvelopeHealth]
    credit_card_states: list[CreditCardState]

    # Detail (bottom)
    upcoming_commitments: list[UpcomingCommitment]
    recent_transactions: list[Transaction]

    # Meta
    period_month: str           # "YYYY-MM"
    generated_at: str


def _fmt_brl(value: float) -> str:
    """Format a float as BRL currency string."""
    import locale
    try:
        locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
        return locale.currency(value, grouping=True)
    except Exception:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _trend(current: float, avg: float) -> str:
    diff_pct = ((current - avg) / abs(avg)) * 100 if avg != 0 else 0
    if diff_pct > 5:
        return "UP"
    elif diff_pct < -5:
        return "DOWN"
    return "STABLE"


class GetDashboardV2UseCase:
    """Builds the institutional-grade dashboard payload."""

    def __init__(
        self,
        transactions: TransactionRepo,
        envelopes: EnvelopeRepo,
        subscriptions: SubscriptionRepo,
        installments: InstallmentRepo,
        accounts: AccountRepo,
    ) -> None:
        self._transactions = transactions
        self._envelopes = envelopes
        self._subscriptions = subscriptions
        self._installments = installments
        self._accounts = accounts

    async def execute(
        self,
        user_id: str,
        target_month: Optional[str] = None,  # "YYYY-MM"; defaults to current month
    ) -> DashboardV2Output:
        now = datetime.utcnow()
        month = target_month or now.strftime("%Y-%m")
        month_dt = datetime.strptime(month, "%Y-%m")

        # ── Load 6 months of transactions (historical) ─────────────────────────
        hist_start = month_dt - relativedelta(months=5)
        # Extend end_date to catch future pending transactions for the 30-day commitment window
        future_limit = now + timedelta(days=30)
        month_end = month_dt + relativedelta(months=1) - timedelta(seconds=1)
        hist_end = max(month_end, future_limit)

        all_txns = await self._transactions.list_by_user(
            user_id=user_id,
            start_date=hist_start,
            end_date=hist_end,
            limit=2000,
        )

        # ── Monthly aggregates ─────────────────────────────────────────────────
        monthly_income: dict[str, Decimal] = defaultdict(Decimal)
        monthly_expenses: dict[str, Decimal] = defaultdict(Decimal)
        for t in all_txns:
            mk = t.date.strftime("%Y-%m")
            if t.transaction_type == TransactionType.CREDIT:
                monthly_income[mk] += t.amount
            else:
                monthly_expenses[mk] += t.amount

        # ── Current month sums ─────────────────────────────────────────────────
        curr_income = float(monthly_income.get(month, Decimal("0")))
        curr_expenses = float(monthly_expenses.get(month, Decimal("0")))
        savings_rate = ((curr_income - curr_expenses) / curr_income * 100) if curr_income > 0 else 0.0

        # ── Historical averages (last 5 months, excluding this month) ──────────
        hist_months = [
            (month_dt - relativedelta(months=i)).strftime("%Y-%m")
            for i in range(1, 6)
        ]
        avg_income = float(sum(monthly_income.get(m, Decimal("0")) for m in hist_months) / 5)
        avg_expenses = float(sum(monthly_expenses.get(m, Decimal("0")) for m in hist_months) / 5)
        avg_savings = ((avg_income - avg_expenses) / avg_income * 100) if avg_income > 0 else 0.0

        # ── Envelopes for current month ────────────────────────────────────────
        envelope_models = await self._envelopes.list_by_user_month(user_id=user_id, month=month)
        ready_to_assign_val = 0.0
        for env in envelope_models:
            if env.name == "Pronto para Atribuir":
                ready_to_assign_val = float(env.available)
                break

        envelope_health = [
            EnvelopeHealth(
                id=e.id,
                name=e.name,
                icon=e.icon,
                color=e.color,
                allocated=float(e.allocated),
                spent=float(e.spent),
                available=float(e.available),
                utilization_pct=round(e.utilization_pct, 1),
                is_overspent=e.is_overspent,
                is_system=e.is_system,
            )
            for e in envelope_models
        ]

        # ── Total Net Worth (Assets - CC Debts) ────────────────────────────────
        user_accounts = await self._accounts.list_by_user(user_id=user_id)
        total_assets = Decimal("0.00")
        total_debts = Decimal("0.00")
        for a in user_accounts:
            if a.account_type.value == "CREDIT_CARD":
                # We assume CC balance is positive debt (outstanding balance)
                total_debts += abs(Decimal(str(a.balance)))
            else:
                total_assets += Decimal(str(a.balance))
        
        curr_net_worth = float(total_assets - total_debts)

        # ── Cash flow projection (3 months future) ────────────────────────────
        # Use avg of last 3 months as projection base
        recent_3 = [(month_dt - relativedelta(months=i)).strftime("%Y-%m") for i in range(1, 4)]
        proj_income_base = float(sum(monthly_income.get(m, Decimal("0")) for m in recent_3) / 3)
        proj_expense_base = float(sum(monthly_expenses.get(m, Decimal("0")) for m in recent_3) / 3)

        # Add installment commitments to projected expenses
        active_groups = await self._installments.list_active_by_user(user_id=user_id)
        installment_commits: dict[str, Decimal] = defaultdict(Decimal)
        for grp in active_groups:
            for seq in range(grp.installment_count):
                due = grp.start_date + relativedelta(months=seq)
                mk = due.strftime("%Y-%m")
                installment_commits[mk] += grp.installment_amount

        cash_flow: list[CashFlowDataPoint] = []
        # Past 5 months (actual)
        for i in range(5, 0, -1):
            m = (month_dt - relativedelta(months=i)).strftime("%Y-%m")
            inc = float(monthly_income.get(m, Decimal("0")))
            exp = float(monthly_expenses.get(m, Decimal("0")))
            cash_flow.append(CashFlowDataPoint(
                month=m, income=inc, expenses=exp,
                balance=inc - exp, is_projected=False,
            ))
        # This month (actual)
        cash_flow.append(CashFlowDataPoint(
            month=month, income=curr_income, expenses=curr_expenses,
            balance=curr_income - curr_expenses, is_projected=False,
        ))
        # Next 3 months (projected)
        for i in range(1, 4):
            m = (month_dt + relativedelta(months=i)).strftime("%Y-%m")
            proj_exp = proj_expense_base + float(installment_commits.get(m, Decimal("0")))
            cash_flow.append(CashFlowDataPoint(
                month=m, income=proj_income_base, expenses=proj_exp,
                balance=proj_income_base - proj_exp, is_projected=True,
            ))

        # ── Upcoming commitments ───────────────────────────────────────────────
        upcoming_subs = await self._subscriptions.list_due(
            user_id=user_id,
            before=now + timedelta(days=30),
        )
        upcoming: list[UpcomingCommitment] = [
            UpcomingCommitment(
                id=s.id,
                label=s.name,
                amount=float(s.amount),
                due_date=s.next_billing_date.strftime("%Y-%m-%d"),
                commitment_type="SUBSCRIPTION",
                is_overdue=s.is_overdue,
            )
            for s in upcoming_subs
        ]

        # Add upcoming installments
        for grp in active_groups:
            for seq in range(1, grp.installment_count + 1):
                due = grp.start_date + relativedelta(months=seq - 1)
                if now <= due <= now + timedelta(days=30):
                    upcoming.append(UpcomingCommitment(
                        id=f"{grp.id}-{seq}",
                        label=f"{grp.description} ({seq}/{grp.installment_count})",
                        amount=float(grp.installment_amount),
                        due_date=due.strftime("%Y-%m-%d"),
                        commitment_type="INSTALLMENT",
                        is_overdue=due < now,
                    ))

        # Add PENDING standalone transactions in the next 30 days
        pending_txns = [
            t for t in all_txns 
            if t.status == TransactionStatus.PENDING 
            and t.role == TransactionRole.STANDALONE
            and t.date <= now + timedelta(days=30)
        ]
        for t in pending_txns:
            upcoming.append(UpcomingCommitment(
                id=t.id,
                label=t.description,
                amount=float(t.amount),
                due_date=t.date.strftime("%Y-%m-%d"),
                commitment_type="TRANSACTION",
                is_overdue=t.date < now,
            ))

        upcoming.sort(key=lambda x: x.due_date)

        # ── Recent transactions (only past/present) ───────────────────────────
        recent = sorted(
            [t for t in all_txns if t.date <= now],
            key=lambda t: t.date,
            reverse=True
        )[:10]

        # ── KPI cards with benchmark context ──────────────────────────────────
        def _vs_pct(curr: float, avg: float) -> float:
            if avg == 0:
                return 0.0
            return round((curr - avg) / abs(avg) * 100, 1)

        return DashboardV2Output(
            ready_to_assign=KPICard(
                label="Pronto para Atribuir",
                value=ready_to_assign_val,
                formatted=_fmt_brl(ready_to_assign_val),
                vs_avg_pct=0.0,
                trend="STABLE",
                alert=ready_to_assign_val > 0,
                alert_message="Você tem fundos não alocados! Atribua-os às categorias." if ready_to_assign_val > 0 else "",
            ),
            net_worth=KPICard(
                label="Saldo Líquido",
                value=curr_net_worth,
                formatted=_fmt_brl(curr_net_worth),
                vs_avg_pct=0.0,  # Historical net worth tracking needed for vs_avg
                trend="STABLE",
                alert=curr_net_worth < 0,
                alert_message="Seu saldo total está negativo!" if curr_net_worth < 0 else "",
            ),
            savings_rate=KPICard(
                label="Taxa de Poupança",
                value=savings_rate,
                formatted=f"{savings_rate:.1f}%",
                vs_avg_pct=_vs_pct(savings_rate, avg_savings),
                trend=_trend(savings_rate, avg_savings),
                alert=savings_rate < 10,
                alert_message="Taxa de poupança abaixo de 10% — revise seus gastos." if savings_rate < 10 else "",
            ),
            total_income=KPICard(
                label="Receitas", value=curr_income,
                formatted=_fmt_brl(curr_income),
                vs_avg_pct=_vs_pct(curr_income, avg_income),
                trend=_trend(curr_income, avg_income),
            ),
            total_expenses=KPICard(
                label="Despesas", value=curr_expenses,
                formatted=_fmt_brl(curr_expenses),
                vs_avg_pct=_vs_pct(curr_expenses, avg_expenses),
                trend=_trend(curr_expenses, avg_expenses),
                alert=curr_expenses > curr_income,
            ),
            cash_flow_projection=cash_flow,
            envelope_health=envelope_health,
            credit_card_states=[],   # Populated by credit card router with account data
            upcoming_commitments=upcoming,
            recent_transactions=recent,
            period_month=month,
            generated_at=now.isoformat(),
        )
