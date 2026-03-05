"""
FastAPI Router: Accounts
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.database import get_session
from infrastructure.db.models import AccountModel
from domain.entities.account import Account, AccountType
from interfaces.api.schemas.account_schemas import AccountOut, AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["Accounts"])
from interfaces.api.dependencies.auth import get_current_user_id


def _model_to_out(m: AccountModel) -> AccountOut:
    return AccountOut(
        id=m.id,
        user_id=m.user_id,
        bank_name=m.bank_name,
        bank_code=m.bank_code,
        masked_account_number=m.masked_account_number,
        account_type=str(m.account_type),
        balance=float(m.balance or 0),
        currency=m.currency,
        is_active=m.is_active,
        invoice_due_day=m.invoice_due_day,
        invoice_closing_day=m.invoice_closing_day,
        credit_limit=float(m.credit_limit) if m.credit_limit is not None else None,
        created_at=m.created_at,
    )


@router.get("", response_model=list[AccountOut], summary="List accounts")
async def list_accounts(user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    stmt = select(AccountModel).where(AccountModel.user_id == user_id, AccountModel.is_active == True)
    result = await session.execute(stmt)
    return [_model_to_out(m) for m in result.scalars().all()]


@router.post("", response_model=AccountOut, status_code=201, summary="Create account")
async def create_account(body: AccountCreate, user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)):
    import uuid
    from datetime import datetime
    print(f"Creating account for user {user_id}: {body.bank_name}")
    model = AccountModel(
        id=str(uuid.uuid4()),
        user_id=user_id,
        bank_name=body.bank_name,
        bank_code=body.bank_code,
        masked_account_number=body.masked_account_number,
        account_type=body.account_type,
        balance=Decimal(str(body.balance)),
        currency=body.currency,
        is_active=True,
        invoice_due_day=body.invoice_due_day,
        invoice_closing_day=body.invoice_closing_day,
        credit_limit=Decimal(str(body.credit_limit)) if body.credit_limit is not None else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    print("Adding model to session...")
    session.add(model)
    print("Committing session...")
    await session.commit()
    print("Commit successful. Refreshing...")
    await session.refresh(model)
    print("Refresh successful. Returning.")
    return _model_to_out(model)


@router.delete("/{account_id}", status_code=204, summary="Delete account")
async def delete_account(account_id: str, user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)):
    model = await session.get(AccountModel, account_id)
    if not model or model.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    model.is_active = False
    await session.commit()


@router.patch("/{account_id}", response_model=AccountOut, summary="Update account")
async def update_account(
    account_id: str,
    body: AccountUpdate,
    user_id: str = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_session)
):
    model = await session.get(AccountModel, account_id)
    if not model or model.user_id != user_id:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == 'balance':
            setattr(model, key, Decimal(str(value)))
        else:
            setattr(model, key, value)
            
    from datetime import datetime
    model.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(model)
    return _model_to_out(model)

