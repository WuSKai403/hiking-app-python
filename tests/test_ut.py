# tests/test_api.py (修正後的版本)
import pytest
from httpx import AsyncClient
from app.models import RecommendationRequest, RecommendationResponse


# 測試根目錄，確認服務和 DB 連線狀態
@pytest.mark.asyncio
async def test_root_status_check(async_client: AsyncClient):
    # 此測試應只檢查本地連線狀態，不會觸發外部網路
    response = await async_client.get("/")
    assert response.status_code == 200
    assert "MongoDB" in response.json().get("status")
    assert response.json().get("service") in ["ready", "error"]


# 測試核心 AI 推薦端點，必須模擬 Gemini API 呼叫
@pytest.mark.asyncio
async def test_post_recommendation_success(async_client: AsyncClient, mocker):
    # 1. 定義一個我們期望 AI 服務返回的模擬結果
    mock_ai_response = RecommendationResponse(
        safety_score=4,
        recommendation="天氣尚可，請注意單人輕裝帶來的風險。",
        reasoning="預報顯示下午有雨，但路況評論良好。安全評分中等偏上。",
        data_source="Mocked AI Response",  # 標記為 Mocked
    )

    # 2. 使用 mocker.patch 模擬 (Mock) 外部呼叫
    # 我們模擬的是 services/ai_service.py 中的 get_ai_recommendation 函數
    mocker.patch(
        "main.get_ai_recommendation",
        # return_value 必須是一個 Coroutine 物件 (因為原函數是 async)
        return_value=mock_ai_response,
    )

    # 3. 執行 API 測試
    test_request_data = RecommendationRequest(
        trail_id="HEB001",
        user_path_desc="新手，下午 2 點出發，單人輕裝。",
    )

    response = await async_client.post(
        "/api/recommendation", json=test_request_data.model_dump()
    )

    # 4. 確認結果 (現在是來自 Mocked 數據)
    assert response.status_code == 200
    response_json = response.json()

    # 檢查是否收到了我們模擬的結果
    assert response_json["safety_score"] == 4
    assert response_json["data_source"] == "Mocked AI Response"
