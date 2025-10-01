#

# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient
from app.settings import settings


class Database:
    client: AsyncIOMotorClient = None
    db = None


db_client = Database()


async def connect_to_mongo():
    """連接 MongoDB"""
    print("Connecting to MongoDB...")
    db_client.client = AsyncIOMotorClient(settings.MONGO_URI)
    db_client.db = db_client.client[settings.DATABASE_NAME]
    try:
        # 嘗試 ping 測試連線
        await db_client.client.admin.command("ping")
        print("Successfully connected to MongoDB!")
    except Exception as e:
        print(f"Failed to connect to MongoDB: {e}")


async def close_mongo_connection():
    """關閉 MongoDB 連線"""
    print("Closing MongoDB connection...")
    if db_client.client:
        db_client.client.close()
    print("MongoDB connection closed.")
