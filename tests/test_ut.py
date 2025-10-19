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
    assert response.json() == {"message": "Hiking2025 API is running."}


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
    # 模擬在 `get_recommendation` 函數中所有會觸發外部 I/O 或需要 int(trail_id) 的函數
    mocker.patch("main.get_cwa_data_for_ai", return_value="Mocked CWA Data")
    mocker.patch("main.get_hiking_reviews", return_value="Mocked Review Data")
    mocker.patch("main.get_ai_recommendation", return_value=mock_ai_response)

    # 3. 執行 API 測試
    test_request_data = RecommendationRequest(
        trail_id="108",
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


# @pytest.mark.asyncio
# async def test_get_hiking_reviews(async_client: AsyncClient):
#     # 測試獲取健行評論的 function test_get_hiking_reviews
#     trail_id = "108"  # 使用 MVP 階段的測試 ID
#     reviews = await get_hiking_reviews(trail_id)
#     print("Fetched Reviews:", reviews)
#     assert isinstance(reviews, str)
#     assert len(reviews) > 0  # 確保有返回一些評論內容


# # get_cwa_data_for_ai 測試function是否能正常使用
# @pytest.mark.asyncio
# async def test_get_cwa_data_for_ai(async_client: AsyncClient):
#     trail_id = "108"  # 使用 MVP 階段的測試 ID
#     cwa_data = await get_cwa_data_for_ai(trail_id)
#     print("Fetched CWA Data:", cwa_data)
#     assert isinstance(cwa_data, str)
#     assert len(cwa_data) > 0  # 確保有返回一些氣象內容


# # /api/recommendation 的整合測試
# # 這個測試會實際呼叫 Gemini API 和 CWA API
# # 因此需要設定環境變數 GEMINI_API_KEY 和 CWA_API_KEY
# @pytest.mark.asyncio
# @pytest.mark.integration  # 給這個測試一個專屬標記
# async def test_post_recommendation_integration(async_client: AsyncClient):
#     # 建立一個模擬的輸入數據，確保 AI 能獲得足夠的上下文
#     test_request = RecommendationRequest(
#         trail_id="Testing-001",
#         user_path_desc="測試連線與 JSON 格式，請簡單回答。",
#     )

#     response = await async_client.post(
#         "/api/recommendation", json=test_request.model_dump()
#     )

#     assert response.status_code == 200
#     response_json = response.json()
#     print("Integration Test Response:", response_json)
#     # 驗證 AI 輸出的結構和內容
#     assert "safety_score" in response_json
#     assert 1 <= response_json["safety_score"] <= 5
#     assert "recommendation" in response_json
#     assert "reasoning" in response_json
#     assert "data_source" in response_json
#     assert response_json["data_source"] == "Gemini Real-time"
