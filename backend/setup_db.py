import asyncio
from infrastructure.db.database import create_all_tables
from infrastructure.db.models import TransactionModel, AccountModel, UserModel  # Import models to register them with Base

async def setup():
    print("Creating database tables...")
    await create_all_tables()
    print("Database setup complete! File: finance_app.db")

if __name__ == "__main__":
    asyncio.run(setup())
