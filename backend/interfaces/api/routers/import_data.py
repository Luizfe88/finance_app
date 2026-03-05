"""
FastAPI Router: Data Import

Handles OFX and CSV file uploads.
Uses multipart/form-data for binary file uploads.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.transaction_repository import SQLAlchemyTransactionRepository
from infrastructure.parsers.ofx_parser import OFXParserAdapter
from infrastructure.parsers.csv_parser import CSVParserAdapter, PRESET_COLUMN_MAPS
from application.use_cases.import_ofx import ImportOFXUseCase, ImportOFXInput
from application.use_cases.import_csv import ImportCSVUseCase, ImportCSVInput
from interfaces.api.schemas.transaction_schemas import ImportResultOut

router = APIRouter(prefix="/import", tags=["Import"])

from interfaces.api.dependencies.auth import get_current_user_id
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/ofx", response_model=ImportResultOut, summary="Import OFX/QFX bank statement")
async def import_ofx(
    file: UploadFile = File(..., description="OFX or QFX file from your bank"),
    account_id: str = Form(..., description="Target account ID"),
    session: AsyncSession = Depends(get_session),
):
    """
    Import transactions from an OFX/QFX bank statement file.

    - Supports OFX v1 (SGML) and OFX v2 (XML)
    - Automatically deduplicates using OFX fit_id
    - Auto-categorizes transactions (Portuguese keywords)
    """
    # Validate file type
    if file.content_type not in (
        "application/x-ofx", "application/octet-stream", "text/plain", None
    ):
        filename = file.filename or ""
        if not (filename.endswith(".ofx") or filename.endswith(".qfx")):
            raise HTTPException(status_code=400, detail="File must be .ofx or .qfx")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    repo = SQLAlchemyTransactionRepository(session)
    parser = OFXParserAdapter()
    use_case = ImportOFXUseCase(repository=repo, parser=parser)

    try:
        result = await use_case.execute(ImportOFXInput(
            file_bytes=file_bytes,
            account_id=account_id,
            user_id=user_id,
        ))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return ImportResultOut(
        imported_count=result.imported_count,
        skipped_count=result.skipped_count,
        message=f"Importadas {result.imported_count} transações ({result.skipped_count} duplicatas ignoradas).",
    )


@router.post("/csv", response_model=ImportResultOut, summary="Import CSV bank statement")
async def import_csv(
    file: UploadFile = File(..., description="CSV file exported from your bank"),
    account_id: str = Form(..., description="Target account ID"),
    bank_preset: Optional[str] = Form(None, description="Bank preset: nubank, itau, bradesco, santander"),
    session: AsyncSession = Depends(get_session),
):
    """
    Import transactions from a CSV bank statement.

    Supports presets for common Brazilian banks: `nubank`, `itau`, `bradesco`, `santander`.
    """
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Determine column mapping
    column_mapping = None
    if bank_preset and bank_preset.lower() in PRESET_COLUMN_MAPS:
        column_mapping = PRESET_COLUMN_MAPS[bank_preset.lower()]

    repo = SQLAlchemyTransactionRepository(session)
    parser = CSVParserAdapter()
    use_case = ImportCSVUseCase(repository=repo, parser=parser)

    result = await use_case.execute(ImportCSVInput(
        file_bytes=file_bytes,
        account_id=account_id,
        user_id=user_id,
        column_mapping=column_mapping,
    ))

    if result.errors:
        raise HTTPException(status_code=422, detail=result.errors[0])

    return ImportResultOut(
        imported_count=result.imported_count,
        skipped_count=result.skipped_count,
        message=f"Importadas {result.imported_count} transações com sucesso.",
    )
