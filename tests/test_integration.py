# tests/test_integration.py
import pytest
from app.settings import settings
from app.models import RecommendationRequest, RecommendationResponse
from app.services.ai_service import get_ai_recommendation
from app.tasks import scrape_and_save_trail
from scraper_cron_job import update_reviews_for_trail
from app.database_service import TRAIL_COLLECTION

# 確定 API Keys 是否存在
pytestmark = pytest.mark.skipif(
    not settings.GEMINI_API_KEY or not settings.CWA_API_KEY,
    reason="需要在 .env 文件中設定 GEMINI_API_KEY 和 CWA_API_KEY 才能執行整合測試。",
)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_real_gemini_connection():
    # ... (此測試保持不變)
    test_request = RecommendationRequest(
        trail_id="Testing-001", user_path_desc="測試連線與 JSON 格式，請簡單回答。"
    )
    weather_data = "CWA 預報：天氣晴朗，風速 2 級，無雨。"
    review_data = "近期評論：路徑乾燥良好。"
    result: RecommendationResponse = await get_ai_recommendation(
        request=test_request, weather_data=weather_data, review_data=review_data
    )
    assert isinstance(result, RecommendationResponse)
    assert 1 <= result.safety_score <= 5
    assert result.data_source == "Gemini Real-time"


# --- Scraper Integration Tests ---


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scrape_and_save_trail_flow(test_db, monkeypatch):
    """整合測試：驗證從爬取到儲存，以及增量更新評論的完整流程。"""
    # 1. 設定環境變數，指向測試集合
    monkeypatch.setenv("TRAIL_COLLECTION_NAME", f"{TRAIL_COLLECTION}_test")
    import importlib
    from app import database_service

    importlib.reload(database_service)

    trail_id_to_test = 108

    # --- 階段一：首次爬取 ---
    await scrape_and_save_trail(trail_id_to_test)

    # 驗證首次爬取結果
    saved_data = await test_db["trails"].find_one({"_id": trail_id_to_test})
    assert saved_data is not None
    assert "硬漢嶺" in saved_data["name"]
    original_reviews_count = len(saved_data["reviews"])
    assert original_reviews_count > 0
    print(f"\n首次爬取完成，評論數: {original_reviews_count}")

    # --- 階段二：模擬舊狀態並執行增量更新 ---
    # 手動移除一則評論，模擬資料庫中的舊狀態
    review_to_remove = saved_data["reviews"][0]
    await test_db["trails"].update_one(
        {"_id": trail_id_to_test},
        {"$pull": {"reviews": {"content": review_to_remove["content"]}}},
    )

    # 執行只更新評論的函式
    await update_reviews_for_trail(trail_id_to_test)

    # 驗證增量更新結果
    updated_data = await test_db["trails"].find_one({"_id": trail_id_to_test})
    final_reviews_count = len(updated_data["reviews"])
    print(f"增量更新完成，最終評論數: {final_reviews_count}")

    assert final_reviews_count == original_reviews_count

    # --- 清理 ---
    monkeypatch.delenv("TRAIL_COLLECTION_NAME")
    importlib.reload(database_service)


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scrape_invalid_id(test_db, monkeypatch):
    """整合測試：驗證爬取一個無效 ID 時，會將其正確記錄為 is_valid: false。"""
    # 1. 設定環境變數
    monkeypatch.setenv("TRAIL_COLLECTION_NAME", f"{TRAIL_COLLECTION}_test")
    import importlib
    from app import database_service

    importlib.reload(database_service)

    invalid_trail_id = 3000

    # 2. 執行
    await scrape_and_save_trail(invalid_trail_id)

    # 3. 驗證
    # 驗證 trails 集合中存在這筆資料，但 is_valid 為 false
    trail_data = await test_db["trails"].find_one({"_id": invalid_trail_id})
    assert trail_data is not None
    assert trail_data["is_valid"] is False
    assert "reviews" not in trail_data  # 不應該有評論

    # --- 清理 ---
    monkeypatch.delenv("TRAIL_COLLECTION_NAME")
    importlib.reload(database_service)
