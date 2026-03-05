import asyncio
from decimal import Decimal
from sqlalchemy.future import select
from infrastructure.db.database import AsyncSessionLocal
from infrastructure.db.models import AccountModel

async def fix_felipe_accounts():
    async with AsyncSessionLocal() as session:
        # User Felipe ID from debug: 04b6e800-af57-47a6-b71e-957f28471379
        user_id = "04b6e800-af57-47a6-b71e-957f28471379"
        
        acc_result = await session.execute(
            select(AccountModel).where(
                AccountModel.user_id == user_id,
                AccountModel.account_type == "CREDIT_CARD"
            )
        )
        accounts = acc_result.scalars().all()
        
        for a in accounts:
            if a.balance > 0 and (a.credit_limit is None or a.credit_limit == 0):
                print(f"Fixing {a.bank_name}: Moving {a.balance} from balance to credit_limit")
                a.credit_limit = a.balance
                a.balance = Decimal("0.00")
        
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(fix_felipe_accounts())
