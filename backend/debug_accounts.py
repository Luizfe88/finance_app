import asyncio
import os
from decimal import Decimal
from sqlalchemy.future import select
from infrastructure.db.database import AsyncSessionLocal
from infrastructure.db.models import AccountModel, UserModel

async def debug_accounts():
    async with AsyncSessionLocal() as session:
        # Check users
        users_result = await session.execute(select(UserModel))
        users = users_result.scalars().all()
        print("Users:")
        for u in users:
            print(f"  ID: {u.id}, Name: {u.name}, Email: {u.email}")
            
            # Check accounts for this user
            acc_result = await session.execute(select(AccountModel).where(AccountModel.user_id == u.id))
            accounts = acc_result.scalars().all()
            total_assets = Decimal("0")
            total_debt = Decimal("0")
            for a in accounts:
                print(f"    Account: {a.bank_name}, Type: {a.account_type}, Balance: {a.balance}, Limit: {a.credit_limit}")
                if a.account_type.value == "CREDIT_CARD":
                    total_debt += abs(a.balance)
                else:
                    total_assets += a.balance
            print(f"    --- Total Assets: {total_assets}, Total Debt: {total_debt}, Net: {total_assets - total_debt}")

if __name__ == "__main__":
    asyncio.run(debug_accounts())
