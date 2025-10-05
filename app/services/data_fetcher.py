# app/services/data_fetcher.py

import httpx
from app.settings import settings
import random
from bs4 import BeautifulSoup
from app.services.cwa_transformer import (
    transform_observation_data,
    transform_rainfall_data,
)
from typing import Dict


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


# 定義爬蟲的 Base URL 和最大頁數
BASE_REVIEW_URL = "https://hiking.biji.co/trail/ajax/load_reviews"
MAX_PAGE = 16
# MVP 階段只取 ID 108 測試
TRAIL_ID_MOCK = 108


async def get_hiking_reviews(trail_id: str) -> str:
    """
    呼叫健行筆記 API，隨機擷取一頁評論，並解析出評論內容。
    """
    # 步驟 1: 隨機選擇頁數 (1 到 MAX_PAGE)
    # 根據您的需求，MVP 階段只針對 ID 108 進行測試
    page_to_fetch = random.randint(1, MAX_PAGE)

    # 在 MVP 階段，強制使用 TRAIL_ID_MOCK
    current_trail_id = TRAIL_ID_MOCK

    url = f"{BASE_REVIEW_URL}?id={current_trail_id}&page={page_to_fetch}"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # 由於這是 AJAX API，我們直接模擬瀏覽器請求
            response = await client.get(
                url, headers={"X-Requested-With": "XMLHttpRequest"}
            )
            response.raise_for_status()

            # 健行筆記的評論 API 返回 JSON
            data = response.json()

            if data.get("status") != "success":
                return f"近期山友評論（{trail_id}）：無評論資料或 API 錯誤。"

            # 步驟 2: 提取 HTML 字串並解析
            html_view = data["data"]["view"]

            # BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_view, "html.parser")

            # 步驟 3: 提取日期和文本，並格式化
            formatted_reviews = []

            # 提取 li 項目，以便取得評論日期 (time tag)
            list_items = soup.find_all("li", class_="flex")

            for item in list_items:
                # 獲取時間 (日期)
                time_tag = item.find("time", class_="text-sm")
                review_date = time_tag.get("datetime") if time_tag else "日期不詳"

                # 獲取評論文本
                review_p = item.find("p", class_="leading-relaxed")
                review_text = review_p.get_text(strip=True) if review_p else ""

                # if review_text:
                #     # 解碼 Unicode 16 進位字元 (e.g. \u5f88\u597d -> 很好)
                #     decoded_text = bytes(review_text, "latin1").decode("unicode_escape")

                formatted_reviews.append(f"[{review_date}] {review_text}")
                print(f"Extracted Review: [{review_date}] {review_text}")

            if not formatted_reviews:
                return f"近期山友評論（{current_trail_id}）：該頁（{page_to_fetch}）無有效評論。"

            # 將所有評論用換行符號合併成一個字串
            review_string = "\n".join(formatted_reviews)

            return f"近期山友評論（健行筆記 ID {current_trail_id}, 隨機頁 {page_to_fetch}）：\n---\n{review_string}\n---"

    except httpx.HTTPStatusError as e:
        print(f"評論 API 請求失敗: HTTP 錯誤 {e.response.status_code}")
        return f"評論 API 連線失敗或無資料: {e.response.status_code}"
    except Exception as e:
        print(f"評論 API 呼叫發生例外: {e}")
        return f"評論 API 擷取例外: {e}"


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
