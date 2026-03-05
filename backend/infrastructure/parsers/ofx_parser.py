"""
Infrastructure: OFX Parser Adapter

Wraps `ofxtools` to parse OFX/QFX bank statement files into domain Transaction entities.
Designed as an injectable adapter (implements the OFXParser Protocol).

Supports OFX v1 (SGML) and OFX v2 (XML) formats used by Brazilian banks.
"""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import Optional

from domain.entities.transaction import Transaction, TransactionType, TransactionStatus

# Auto-categorization rules for Brazilian transactions
CATEGORY_RULES: dict[str, list[str]] = {
    "Alimentação": ["restaurante", "lanchonete", "ifood", "rappi", "padaria", "supermercado", "mercado", "atacadão", "carrefour", "pão de açúcar"],
    "Transporte": ["uber", "99", "posto", "combustivel", "shell", "petrobras", "metrô", "ônibus", "estacionamento"],
    "Saúde": ["farmácia", "drogaria", "hospital", "clínica", "médico", "laboratorio", "unimed", "amil", "plano de saúde"],
    "Educação": ["escola", "faculdade", "universidade", "curso", "udemy", "alura", "mensalidade"],
    "Lazer": ["cinema", "netflix", "spotify", "amazon prime", "disney", "teatro", "shows", "ingressos"],
    "Serviços": ["luz", "energia", "água", "gás", "internet", "telefone", "celular", "vivo", "claro", "tim"],
    "Moradia": ["aluguel", "condomínio", "iptu", "seguro residencial"],
    "Roupas": ["renner", "riachuelo", "zara", "c&a", "hm", "lojas"],
}


def _auto_categorize(description: str) -> str:
    """Simple keyword-based categorization. Returns 'Outros' if no match."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Outros"


def _map_transaction_type(ofx_type: str) -> TransactionType:
    """Map OFX transaction types to domain enum."""
    credit_types = {"CREDIT", "DEP", "INT", "DIV", "DIRECTDEP", "XFER"}
    if ofx_type.upper() in credit_types:
        return TransactionType.CREDIT
    return TransactionType.DEBIT


class OFXParserAdapter:
    """
    Parses OFX/QFX files into domain Transaction entities.

    Usage:
        parser = OFXParserAdapter()
        transactions = parser.parse(file_bytes, account_id="acc-1", user_id="usr-1")
    """

    def parse(
        self,
        file_bytes: bytes,
        account_id: str,
        user_id: str,
    ) -> list[Transaction]:
        """Parse OFX bytes and return a list of domain Transaction entities."""
        try:
            from ofxtools.parser import OFXTree
            parser = OFXTree()
            parser.parse(io.BytesIO(file_bytes))
            ofx = parser.convert()
            return self._extract_transactions(ofx, account_id, user_id)
        except Exception as e:
            # Fallback: try SGML (OFX v1) parsing
            try:
                return self._parse_sgml_fallback(file_bytes, account_id, user_id)
            except Exception:
                raise ValueError(f"Failed to parse OFX file: {e}")

    def _extract_transactions(self, ofx, account_id: str, user_id: str) -> list[Transaction]:
        """Extract transactions from parsed OFX object."""
        transactions = []

        # Navigate OFX structure: statement → transactions
        statements = getattr(ofx, "statements", [])
        for statement in statements:
            for stmttrn in getattr(statement, "transactions", []):
                txn = self._map_stmttrn(stmttrn, account_id, user_id)
                if txn:
                    transactions.append(txn)

        return transactions

    def _map_stmttrn(self, stmttrn, account_id: str, user_id: str) -> Optional[Transaction]:
        """Convert an OFX STMTTRN element to a domain Transaction."""
        try:
            amount = Decimal(str(stmttrn.trnamt))
            txn_type = _map_transaction_type(str(stmttrn.trntype))

            # OFX stores negative for debits; normalize to absolute value
            abs_amount = abs(amount)

            description = str(getattr(stmttrn, "name", "") or getattr(stmttrn, "memo", "") or "")
            memo = str(getattr(stmttrn, "memo", "") or "")
            fit_id = str(getattr(stmttrn, "fitid", "") or "")
            payee_name = str(getattr(stmttrn, "payee", "") or "")

            # Parse date (OFX uses datetime)
            dtposted = stmttrn.dtposted
            if hasattr(dtposted, "replace"):
                txn_date = dtposted.replace(tzinfo=None)
            else:
                txn_date = datetime.utcnow()

            return Transaction(
                user_id=user_id,
                account_id=account_id,
                amount=abs_amount,
                currency="BRL",
                description=description,
                category=_auto_categorize(description),
                date=txn_date,
                transaction_type=txn_type,
                status=TransactionStatus.POSTED,
                memo=memo if memo != description else None,
                fit_id=fit_id or None,
                payee=payee_name or None,
            )
        except Exception:
            return None

    def _parse_sgml_fallback(self, file_bytes: bytes, account_id: str, user_id: str) -> list[Transaction]:
        """
        Fallback text-based parser for OFX v1 (SGML format) used by older Brazilian banks.
        Parses key-value pairs from raw text.
        """
        import re
        text = file_bytes.decode("latin-1", errors="replace")
        transactions = []

        # Find all STMTTRN blocks
        blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, re.DOTALL)

        for block in blocks:
            def get_field(tag: str) -> str:
                match = re.search(rf"<{tag}>(.*?)(?:<|\n)", block, re.IGNORECASE)
                return match.group(1).strip() if match else ""

            try:
                amount_str = get_field("TRNAMT").replace(",", ".")
                amount = Decimal(amount_str)
                txn_type_str = get_field("TRNTYPE")
                txn_type = _map_transaction_type(txn_type_str)
                abs_amount = abs(amount)

                date_str = get_field("DTPOSTED")[:8]  # YYYYMMDD
                txn_date = datetime.strptime(date_str, "%Y%m%d") if date_str else datetime.utcnow()

                description = get_field("MEMO") or get_field("NAME") or ""
                fit_id = get_field("FITID") or None

                transactions.append(Transaction(
                    user_id=user_id,
                    account_id=account_id,
                    amount=abs_amount,
                    currency="BRL",
                    description=description,
                    category=_auto_categorize(description),
                    date=txn_date,
                    transaction_type=txn_type,
                    status=TransactionStatus.POSTED,
                    fit_id=fit_id,
                ))
            except Exception:
                continue

        return transactions
