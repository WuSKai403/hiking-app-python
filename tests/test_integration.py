# tests/test_integration.py
import pytest
import os
from app.models import RecommendationRequest, RecommendationResponse
from app.services.ai_service import get_ai_recommendation

# 檢查環境變數 CWA/GEMINI_API_KEY 是否存在
# 如果不存在，這個測試會被跳過 (這是 Integration Test 的標準做法)
pytestmark = pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") or not os.getenv("CWA_API_KEY"),
    reason="需要設定 GEMINI_API_KEY 和 CWA_API_KEY 環境變數才能執行真正的整合測試。",
)


@pytest.mark.asyncio
@pytest.mark.integration  # 給這個測試一個專屬標記
async def test_real_gemini_connection():
    """
    這個測試會實際呼叫 Gemini API，驗證連線和輸出格式。
    """

    # 建立一個模擬的輸入數據，確保 AI 能獲得足夠的上下文
    test_request = RecommendationRequest(
        trail_id="Testing-001",
        user_path_desc="測試連線與 JSON 格式，請簡單回答。",
    )

    # 由於我們沒有在 service 層 mock 任何東西，這裡會發起真實連線
    # 這裡只測試 service 層，不走 FastAPI 路由，以避免 httpx 的 ASGI 轉換問題
    weather_data = "CWA 預報：天氣晴朗，風速 2 級，無雨。"
    review_data = "近期評論：路徑乾燥良好。"

    # 直接調用 service 函數
    result: RecommendationResponse = await get_ai_recommendation(
        request=test_request, weather_data=weather_data, review_data=review_data
    )

    # 驗證 AI 輸出的結構和內容
    assert isinstance(result, RecommendationResponse)
    assert 1 <= result.safety_score <= 5
    assert "JSON" not in result.reasoning  # 確保不是 AI 直接回傳 JSON
    assert result.data_source == "Gemini Real-time"
