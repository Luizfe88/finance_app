"""
Use Case: ImportCSVUseCase

Imports transactions from a CSV file with flexible column mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from domain.entities.transaction import Transaction
from application.protocols.transaction_repository import TransactionRepository


class CSVParser(Protocol):
    """Adapter interface for CSV parsing."""
    def parse(
        self,
        file_bytes: bytes,
        account_id: str,
        user_id: str,
        column_mapping: Optional[dict[str, str]] = None,
    ) -> list[Transaction]:
        ...


@dataclass
class ImportCSVInput:
    file_bytes: bytes
    account_id: str
    user_id: str
    column_mapping: Optional[dict[str, str]] = None   # {"date": "Data", "amount": "Valor", ...}


@dataclass
class ImportCSVOutput:
    imported_count: int
    skipped_count: int
    transactions: list[Transaction]
    errors: list[str]   # Rows that failed to parse


class ImportCSVUseCase:
    """Use Case: Import transactions from a CSV file."""

    def __init__(
        self,
        repository: TransactionRepository,
        parser: CSVParser,
    ) -> None:
        self._repository = repository
        self._parser = parser

    async def execute(self, input_data: ImportCSVInput) -> ImportCSVOutput:
        try:
            transactions = self._parser.parse(
                file_bytes=input_data.file_bytes,
                account_id=input_data.account_id,
                user_id=input_data.user_id,
                column_mapping=input_data.column_mapping,
            )
        except Exception as e:
            return ImportCSVOutput(
                imported_count=0,
                skipped_count=0,
                transactions=[],
                errors=[str(e)],
            )

        if transactions:
            saved = await self._repository.save_many(transactions)
        else:
            saved = []

        return ImportCSVOutput(
            imported_count=len(saved),
            skipped_count=0,
            transactions=saved,
            errors=[],
        )
