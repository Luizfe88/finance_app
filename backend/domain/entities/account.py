"""
Domain Entity: Account (v2 — Institutional Grade)

Extended with:
  - credit_limit: for credit card accounts
  - card_payment_envelope_id: links to the "Pagamento Cartão" BudgetEnvelope
    so the ZBB reserve engine knows where to move reserved funds
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class AccountType(str, Enum):
    CHECKING = "CHECKING"       # Conta corrente
    SAVINGS = "SAVINGS"         # Conta poupança
    CREDIT_CARD = "CREDIT_CARD" # Cartão de crédito
    INVESTMENT = "INVESTMENT"   # Investimento


@dataclass
class Account:
    """
    Financial account entity (v2).

    masked_account_number: stores only the last 4 digits or a token
    (e.g., "****1234") — never the full number, for LGPD compliance.

    credit_limit: Only meaningful for CREDIT_CARD accounts.
    card_payment_envelope_id: Points to the BudgetEnvelope named
      "Pagamento Cartão de Crédito" for this specific card.
      Used by the ZBB reserve engine to route funded purchases.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    bank_name: str = ""
    bank_code: Optional[str] = None     # ISPB / COMPE code (e.g., "341" for Itaú)
    masked_account_number: str = "****"
    account_type: AccountType = AccountType.CHECKING
    balance: Decimal = Decimal("0.00")
    currency: str = "BRL"
    is_active: bool = True

    # --- Credit Card specific (v2) ---
    credit_limit: Optional[Decimal] = None        # Total credit limit (e.g., R$5000)
    card_payment_envelope_id: Optional[str] = None # BudgetEnvelope for CC payments

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def is_credit_card(self) -> bool:
        return self.account_type == AccountType.CREDIT_CARD

    @property
    def available_credit(self) -> Optional[Decimal]:
        """
        For credit cards: credit limit minus outstanding balance.
        Returns None for non-credit-card accounts.
        """
        if not self.is_credit_card or self.credit_limit is None:
            return None
        return self.credit_limit - abs(self.balance)

    @property
    def credit_utilization_pct(self) -> Optional[float]:
        """Credit utilization ratio (0–100+). None for non-CC accounts."""
        if not self.is_credit_card or not self.credit_limit:
            return None
        return float(abs(self.balance) / self.credit_limit * 100)

    def update_balance(self, new_balance: Decimal) -> None:
        self.balance = new_balance
        self.updated_at = datetime.utcnow()

    def deactivate(self) -> None:
        """Soft-delete account (LGPD: allows data retention for compliance period)."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"Account(bank={self.bank_name!r}, "
            f"type={self.account_type.value}, "
            f"masked={self.masked_account_number!r}, "
            f"balance={self.balance})"
        )
