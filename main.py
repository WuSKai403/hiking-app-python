# main.py
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_to_mongo, close_mongo_connection
from app.models import (
    RecommendationRequest,
    RecommendationResponse,
    TrailDocument,
)
from app.services.ai_service import get_ai_recommendation
from app.services.data_fetcher import get_cwa_data_for_ai, get_hiking_reviews
from app import database_service
from app.tasks import scrape_and_save_trail
from app.logger import logger
import asyncio

app = FastAPI(title="Hiking Weather Guide MVP")

# 設置 CORS
origins = [
    "https://hiking2025-front.pages.dev",  # 前端網域
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5173",  # Vite 預設開發端口
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # 允許所有 HTTP 方法
    allow_headers=["*"],  # 允許所有 HTTP 標頭
)

# 設置連線事件
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)


@app.get("/")
async def root():
    # 簡單的首頁
    return {"message": "Hiking2025 API is running."}


# --- Core API Endpoint ---


@app.post("/api/recommendation", response_model=RecommendationResponse)
async def get_recommendation(request: RecommendationRequest):
    logger.info(f"Received recommendation request for trail_id: {request.trail_id}")

    # 步驟 1: 呼叫 CWA API
    CWA_data = await get_cwa_data_for_ai(request.trail_id)

    # 步驟 2: 從資料庫獲取格式化後的評論字串
    reviews = await get_hiking_reviews(int(request.trail_id))

    # MVP 模擬數據
    # mock_weather_data = "預報顯示：下午 1 點後有陣雨，夜間氣溫驟降至 10 度，風速 5 級。"
    # mock_review_data = (
    #     "近期評論 (2025/09/06): 很好的一條路線。 (2025/04/16): 車位充足，步道平緩良好。"
    # )

    # ----------------------------------------------------
    # 步驟 3: 呼叫 AI 判斷核心
    # ----------------------------------------------------
    ai_result = await get_ai_recommendation(request, CWA_data, reviews)

    # ----------------------------------------------------
    # 步驟 4: 儲存 AI 結果快取
    # ----------------------------------------------------
    # TODO: 儲存 ai_result 到 MongoDB 中，作為下次請求的快取
    # await db_client.db.safety_cache.insert_one(ai_result.model_dump())

    logger.info(
        f"Successfully generated recommendation for trail_id: {request.trail_id}"
    )
    logger.debug(f"AI Result: {ai_result}")
    return ai_result


# --- Trail Data Management APIs ---


@app.post("/api/trails/scrape/{trail_id}", status_code=202)
async def scrape_trail_endpoint(trail_id: int, background_tasks: BackgroundTasks):
    """
    觸發單一筆步道資料的背景爬取任務。
    """
    background_tasks.add_task(scrape_and_save_trail, trail_id)
    return {"message": f"已開始背景爬取步道 ID: {trail_id}"}


@app.post("/api/trails/scrape-range", status_code=202)
async def scrape_trail_range_endpoint(
    start_id: int, end_id: int, background_tasks: BackgroundTasks
):
    """
    觸發一個範圍的步道資料背景爬取任務。
    """
    if start_id > end_id:
        raise HTTPException(status_code=400, detail="start_id 不能大於 end_id")

    async def scrape_range():
        for trail_id in range(start_id, end_id + 1):
            await scrape_and_save_trail(trail_id)
            await asyncio.sleep(1)  # 避免請求過於頻繁

    background_tasks.add_task(scrape_range)
    return {"message": f"已開始背景爬取步道 ID 從 {start_id} 到 {end_id}"}


@app.get("/api/trails/{trail_id}", response_model=TrailDocument)
async def get_trail_endpoint(trail_id: int):
    """
    從資料庫中獲取單一筆步道資料。
    """
    trail = await database_service.get_trail_by_id(trail_id)
    if not trail:
        raise HTTPException(status_code=404, detail=f"找不到步道 ID: {trail_id}")
    return trail
