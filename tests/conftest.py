# tests/conftest.py (使用 anyio 的簡潔版本)
import pytest
from httpx import AsyncClient, ASGITransport

# 確保您的 main 模組是可匯入的
from main import app


@pytest.fixture
async def async_client():
    """Fixture to create a FastAPI test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as async_test_client:
        yield async_test_client
