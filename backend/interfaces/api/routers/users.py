"""
API Router: Users (Dev Mode Switcher)
"""
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel

from infrastructure.db.database import get_session
from infrastructure.db.models import UserModel

router = APIRouter(prefix="/users", tags=["Users"])

class UserOut(BaseModel):
    id: str
    email: str
    name: str

class UserCreate(BaseModel):
    email: str
    name: str

@router.get("", response_model=List[UserOut])
async def list_users(session: AsyncSession = Depends(get_session)):
    """List all users for the switcher."""
    stmt = select(UserModel)
    result = await session.execute(stmt)
    return [UserOut(id=u.id, email=u.email, name=u.name) for u in result.scalars().all()]

@router.post("", response_model=UserOut)
async def create_user(body: UserCreate, session: AsyncSession = Depends(get_session)):
    """Create a new user (no password required in dev mode)."""
    new_user = UserModel(
        id=str(uuid.uuid4()),
        email=body.email,
        name=body.name,
        hashed_password="DEV_MODE_BYPASS"
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return UserOut(id=new_user.id, email=new_user.email, name=new_user.name)
