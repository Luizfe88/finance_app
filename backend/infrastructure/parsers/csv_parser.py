"""
Infrastructure: CSV Parser Adapter

Parses bank statement CSV files into domain Transaction entities.
Supports flexible column mapping for different bank formats (Nubank, Itaú, Bradesco, etc.).
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from domain.entities.transaction import Transaction, TransactionType, TransactionStatus


# Preset column mappings for common Brazilian banks
PRESET_COLUMN_MAPS: dict[str, dict[str, str]] = {
    "nubank": {
        "date": "date",
        "description": "title",
        "amount": "amount",
    },
    "itau": {
        "date": "Data",
        "description": "Histórico",
        "amount": "Valor",
    },
    "bradesco": {
        "date": "Data",
        "description": "Histórico",
        "amount": "Crédito/Débito",
    },
    "santander": {
        "date": "Data",
        "description": "Descrição",
        "amount": "Valor",
    },
    "generic": {
        "date": "date",
        "description": "description",
        "amount": "amount",
    },
}


def _parse_amount(raw: str) -> tuple[Decimal, TransactionType]:
    """
    Parse amount string to Decimal. Handles Brazilian formatting:
    - "1.234,56" → 1234.56
    - "-500,00" → 500.00 DEBIT
    - "R$ 1.234,56" → 1234.56 CREDIT
    """
    raw = raw.strip().replace("R$", "").replace(" ", "")
    is_negative = raw.startswith("-") or raw.startswith("(")
    raw = raw.lstrip("-+(").rstrip(")")
    # Convert Brazilian decimal format (1.234,56 → 1234.56)
    raw = raw.replace(".", "").replace(",", ".")
    try:
        amount = abs(Decimal(raw))
    except InvalidOperation:
        amount = Decimal("0.00")

    txn_type = TransactionType.DEBIT if is_negative else TransactionType.CREDIT
    return amount, txn_type


def _parse_date(raw: str) -> datetime:
    """Try common Brazilian date formats."""
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d.%m.%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return datetime.utcnow()


class CSVParserAdapter:
    """
    Parses CSV bank statements into domain Transaction entities.
    Uses flexible column mapping to support multiple bank formats.
    """

    def parse(
        self,
        file_bytes: bytes,
        account_id: str,
        user_id: str,
        column_mapping: Optional[dict[str, str]] = None,
    ) -> list[Transaction]:
        """
        Parse CSV bytes.

        column_mapping: maps logical fields to CSV column names.
          Keys: "date", "description", "amount"
          Values: actual CSV column headers
          Example: {"date": "Data", "description": "Histórico", "amount": "Valor"}
        """
        mapping = column_mapping or PRESET_COLUMN_MAPS["generic"]

        # Try UTF-8 first, then latin-1 (common in Brazilian banks)
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        transactions = []

        date_col = mapping.get("date", "date")
        desc_col = mapping.get("description", "description")
        amount_col = mapping.get("amount", "amount")

        for row in reader:
            # Skip empty rows
            if not any(row.values()):
                continue
            try:
                raw_date = row.get(date_col, "").strip()
                raw_desc = row.get(desc_col, "").strip()
                raw_amount = row.get(amount_col, "0").strip()

                if not raw_date or not raw_amount:
                    continue

                txn_date = _parse_date(raw_date)
                amount, txn_type = _parse_amount(raw_amount)

                from infrastructure.parsers.ofx_parser import _auto_categorize
                transactions.append(Transaction(
                    user_id=user_id,
                    account_id=account_id,
                    amount=amount,
                    currency="BRL",
                    description=raw_desc,
                    category=_auto_categorize(raw_desc),
                    date=txn_date,
                    transaction_type=txn_type,
                    status=TransactionStatus.POSTED,
                ))
            except Exception:
                continue

        return transactions
