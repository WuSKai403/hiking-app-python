# app/services/data_fetcher.py

import httpx
from app.settings import settings
import asyncio
from bs4 import BeautifulSoup
from app.services.cwa_transformer import (
    transform_observation_data,
    transform_rainfall_data,
)
from app.services.trail_scraper import get_total_review_pages
from typing import Dict, List
from app import database_service
from app.models import ReviewModel
from datetime import datetime
import re


async def get_cwa_api(url: str, location_id: str) -> str:
    """
    呼叫 CWA API 取得指定山徑的最新氣象資料。
    """

    # 步驟 1: 設定 API 參數
    params = {
        "Authorization": settings.CWA_API_KEY,
        "locationName": location_id,
        "format": "JSON",
        # ... 其他參數: 限制筆數、需要的欄位等
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=5)
            response.raise_for_status()  # 檢查 HTTP 錯誤

            data = response.json()
            # 步驟 3: 解析 JSON，擷取關鍵資訊，並格式化為 AI 易懂的字串
            return data

    except httpx.HTTPStatusError as e:
        print(f"CWA API 請求失敗: HTTP 錯誤 {e.response.status_code}")
        return f"CWA 資料連線失敗或無資料: {e.response.status_code}"
    except Exception as e:
        print(f"CWA API 呼叫發生例外: {e}")
        return f"CWA 資料擷取例外: {e}"


BASE_REVIEW_URL = "https://hiking.biji.co/trail/ajax/load_reviews"


async def fetch_review_page(client: httpx.AsyncClient, trail_id: int, page: int) -> str:
    """非同步抓取單一頁面的評論 HTML"""
    url = f"{BASE_REVIEW_URL}?id={trail_id}&page={page}"
    try:
        response = await client.get(url, headers={"X-Requested-With": "XMLHttpRequest"})
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success":
            return data["data"]["view"]
        return ""
    except httpx.HTTPStatusError as e:
        print(f"評論 API 請求失敗 (Page {page}): HTTP 錯誤 {e.response.status_code}")
        return ""
    except Exception as e:
        print(f"評論 API 呼叫發生例外 (Page {page}): {e}")
        return ""


def parse_reviews_from_html(html_content: str) -> List[ReviewModel]:
    """從 HTML 內容中解析出 ReviewModel 物件列表"""
    soup = BeautifulSoup(html_content, "html.parser")
    reviews = []
    list_items = soup.find_all("li", class_="flex")

    for item in list_items:
        user_link = item.find("a", href=lambda href: href and "q=member" in href)
        if not user_link:
            continue

        # 從 a 標籤的 href 中解析 user_id
        user_id_match = re.search(r"member=(\d+)", user_link["href"])
        user_id = user_id_match.group(1) if user_id_match else "unknown"

        # 獲取使用者名稱
        username = user_link.text.strip()

        # 獲取時間 (日期)
        time_tag = item.find("time", class_="text-sm")
        review_date_str = time_tag.get("datetime") if time_tag else None
        review_date = (
            datetime.fromisoformat(review_date_str) if review_date_str else None
        )

        # 獲取評論文本
        review_p = item.find("p", class_="leading-relaxed")
        content = review_p.get_text(strip=True) if review_p else ""

        if user_id != "unknown" and content:
            reviews.append(
                ReviewModel(
                    user_id=user_id,
                    username=username,
                    review_date=review_date,
                    content=content,
                )
            )
    return reviews


async def get_all_reviews_for_trail(trail_id: int) -> List[ReviewModel]:
    """
    呼叫健行筆記 API，擷取並解析指定步道的所有評論。
    """
    total_pages = await get_total_review_pages(trail_id)

    if total_pages == 0:
        return []

    async with httpx.AsyncClient(timeout=10) as client:
        # 建立所有頁面的抓取任務
        tasks = [
            fetch_review_page(client, trail_id, page)
            for page in range(1, total_pages + 1)
        ]
        # 並發執行所有任務
        html_results = await asyncio.gather(*tasks)

    # 將所有 HTML 片段合併成一個
    full_html = "".join(html_results)

    if not full_html:
        return []

    # 一次性解析所有 HTML 並回傳 ReviewModel 列表
    return parse_reviews_from_html(full_html)


async def get_hiking_reviews(trail_id: int) -> str:
    """
    從資料庫獲取指定步道的評論，並格式化為單一字串。
    """
    trail_data = await database_service.get_trail_data_from_db(trail_id)

    if not trail_data.reviews:
        return "無相關評論。"

    reviews_str_list = [
        f"[{r.review_date.strftime('%Y-%m-%d') if r.review_date else '日期不詳'}] {r.content}"
        for r in trail_data.reviews
    ]
    return "\n".join(reviews_str_list)


# 假設您有一個函式可以將 trail_id 轉換為一組 CWA 測站 ID
def get_station_ids_by_trail(trail_id: str) -> Dict[str, str]:
    # TODO: 查表邏輯，MVP 階段可先固定一組
    return {
        "O-A0001-001": "C0AK30",  # 氣象站 ID
        "O-A0002-001": "C1I230",  # 雨量站 ID
    }


async def get_cwa_data_for_ai(trail_id: str) -> str:
    """
    同時從多個 CWA API 獲取數據，並將其轉換為 AI 摘要字串。
    """
    station_map = get_station_ids_by_trail(trail_id)

    # 專門用於累積所有 CWA 資訊的列表
    all_cwa_summaries = []

    # --- 氣象觀測 (O-A0001-001) ---
    weather_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001"
    # ... (呼叫 API 取得 weather_json_data)
    weather_json_data = await get_cwa_api(weather_url, station_map["O-A0001-001"])

    # 檢查 API 回傳結果：如果是字串，表示是錯誤訊息，直接使用
    if isinstance(weather_json_data, str):
        weather_summary = weather_json_data
    else:
        # 否則，呼叫轉換器
        weather_summary = transform_observation_data(
            weather_json_data, station_map["O-A0001-001"]
        )
    all_cwa_summaries.append(weather_summary)

    # --- 雨量觀測 (O-A0002-001) ---
    rainfall_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
    # ... (呼叫 API 取得 rainfall_json_data)
    rainfall_json_data = await get_cwa_api(rainfall_url, station_map["O-A0002-001"])

    # 同樣的錯誤處理邏輯
    if isinstance(rainfall_json_data, str):
        rainfall_summary = rainfall_json_data
    else:
        # 呼叫轉換器
        rainfall_summary = transform_rainfall_data(
            rainfall_json_data, station_map["O-A0002-001"]
        )
    all_cwa_summaries.append(rainfall_summary)

    # 最終傳給 AI 的結果
    return "\n\n".join(all_cwa_summaries)
