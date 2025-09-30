#

# app/database.py
from motor.motor_asyncio import AsyncIOMotorClient

# 請替換成您從 Atlas 複製的 URI
# 建議使用環境變數，但在 MVP 測試階段可先硬編碼
MONGO_URI = "mongodb+srv://hikingstudiotw_db_user:9LvDhi.u_wsZ3P4@clusterhiking0.0psvv3y.mongodb.net/?retryWrites=true&w=majority&appName=ClusterHiking0"
DATABASE_NAME = "hiking_db"  # 設定資料庫名稱


class Database:
    client: AsyncIOMotorClient = None
    db = None


db_client = Database()


async def connect_to_mongo():
    """連接 MongoDB"""
    print("Connecting to MongoDB...")
    db_client.client = AsyncIOMotorClient(MONGO_URI)
    db_client.db = db_client.client[DATABASE_NAME]
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
