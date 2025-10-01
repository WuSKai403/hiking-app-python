# main.py (更新版本)
from fastapi import FastAPI
from app.database import connect_to_mongo, close_mongo_connection, db_client
from app.models import RecommendationRequest, RecommendationResponse
from app.services.ai_service import get_ai_recommendation  # 導入 AI 服務

app = FastAPI(title="Hiking Weather Guide MVP")

# 設置連線事件
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)


@app.get("/")
async def root():
    # 測試連線是否成功
    if db_client.db:
        return {"status": "MongoDB Connected", "service": "ready"}
    return {"status": "MongoDB Failed", "service": "error"}


# 核心 API 端點：整合數據並返回 AI 建議
@app.post("/api/recommendation", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest):
    # ----------------------------------------------------
    # 步驟 1: 資料庫快取檢查 (依據架構圖 B -> D)
    # ----------------------------------------------------
    # TODO: 實際的邏輯應該是：
    # 1. 查詢 MongoDB (db_client.db.safety_cache) 是否有 {trail_id} 且時間未過期的結果。
    # 2. 如果有，直接返回 (result.data_source = "Cache")

    # 假設我們現在強制走 AI 判讀流程 (MVP 第一版)
    # if cached_result:
    #    return cached_result

    # ----------------------------------------------------
    # 步驟 2: 呼叫外部資料源 (依據架構圖 B -> C1/C2)
    # ----------------------------------------------------
    # TODO: 替換為實際的 CWA API 和爬蟲服務呼叫
    # CWA_data = await call_cwa_api(request.trail_id)
    # reviews = await scrape_hiking_reviews(request.trail_id)

    # MVP 模擬數據
    mock_weather_data = "預報顯示：下午 1 點後有陣雨，夜間氣溫驟降至 10 度，風速 5 級。"
    mock_review_data = (
        "近期評論 (2025/09/06): 很好的一條路線。 (2025/04/16): 車位充足，步道平緩良好。"
    )

    # ----------------------------------------------------
    # 步驟 3: 呼叫 AI 判斷核心 (依據架構圖 B -> E)
    # ----------------------------------------------------
    ai_result = await get_ai_recommendation(
        request, mock_weather_data, mock_review_data
    )

    # ----------------------------------------------------
    # 步驟 4: 儲存結果回資料庫 (依據架構圖 E -> D)
    # ----------------------------------------------------
    # TODO: 儲存 ai_result 到 MongoDB 中，作為下次請求的快取
    # await db_client.db.safety_cache.insert_one(ai_result.model_dump())

    return ai_result
