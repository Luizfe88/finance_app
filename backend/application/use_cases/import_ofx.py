"""
Use Case: ImportOFXUseCase

Orchestrates the OFX import flow:
1. Receive raw OFX file bytes
2. Parse via infrastructure parser (injected)
3. Deduplicate using fit_id
4. Persist via repository (injected)

No dependency on frameworks — just domain entities and protocols.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from domain.entities.transaction import Transaction
from application.protocols.transaction_repository import TransactionRepository


class OFXParser(Protocol):
    """Adapter interface for OFX parsing — injected from infrastructure layer."""
    def parse(self, file_bytes: bytes, account_id: str, user_id: str) -> list[Transaction]:
        ...


@dataclass
class ImportOFXInput:
    file_bytes: bytes
    account_id: str
    user_id: str


@dataclass
class ImportOFXOutput:
    imported_count: int
    skipped_count: int    # Duplicates skipped via fit_id
    transactions: list[Transaction]


class ImportOFXUseCase:
    """
    Use Case: Import transactions from an OFX bank statement file.

    Dependencies are injected (DIP), enabling easy testing with mocks.
    """

    def __init__(
        self,
        repository: TransactionRepository,
        parser: OFXParser,
    ) -> None:
        self._repository = repository
        self._parser = parser

    async def execute(self, input_data: ImportOFXInput) -> ImportOFXOutput:
        # 1. Parse OFX file into domain transactions
        transactions = self._parser.parse(
            file_bytes=input_data.file_bytes,
            account_id=input_data.account_id,
            user_id=input_data.user_id,
        )

        # 2. Deduplicate: check which fit_ids already exist
        new_transactions: list[Transaction] = []
        skipped = 0

        for txn in transactions:
            if txn.fit_id:
                existing = await self._repository.find_by_fit_id(
                    fit_id=txn.fit_id,
                    user_id=input_data.user_id,
                )
                if existing is not None:
                    skipped += 1
                    continue
            new_transactions.append(txn)

        # 3. Persist new transactions in bulk
        if new_transactions:
            saved = await self._repository.save_many(new_transactions)
        else:
            saved = []

        return ImportOFXOutput(
            imported_count=len(saved),
            skipped_count=skipped,
            transactions=saved,
        )
