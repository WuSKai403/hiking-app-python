# tests/conftest.py
import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from app.database import connect_to_mongo, close_mongo_connection, db_client
from app.database_service import TRAIL_COLLECTION

# 確保您的 main 模組是可匯入的
from main import app


# 使用 pytest-asyncio 的事件循環 fixture
@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db():
    """
    Fixture to handle test database connection and cleanup.
    Yields a dictionary of test collections.
    """
    # 連線到資料庫
    await connect_to_mongo()

    collections = {
        "trails": db_client.db[f"{TRAIL_COLLECTION}_test"],
        "invalid_ids": db_client.db["invalid_trail_ids_test"],
    }

    # 確保測試集合是乾淨的
    await collections["trails"].delete_many({})
    await collections["invalid_ids"].delete_many({})

    yield collections

    # 測試結束後再次清理
    await collections["trails"].delete_many({})
    await collections["invalid_ids"].delete_many({})
    await close_mongo_connection()


@pytest_asyncio.fixture(scope="function")
async def async_client():
    """Fixture to create a FastAPI test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_test_client:
        yield async_test_client
