import httpx
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, Optional
import re


def safe_find_text(
    soup: BeautifulSoup, selector: str, attribute: Optional[str] = None
) -> Optional[str]:
    """安全地尋找元素並取得其文字或屬性，避免 NoneType 錯誤"""
    element = soup.select_one(selector)
    if element:
        if attribute:
            return element.get(attribute)
        return element.text.strip()
    return None


def find_data_by_dt(soup: BeautifulSoup, dt_text: str) -> Optional[str]:
    """在 dl > div > dt/dd 結構中，根據 dt 的文字內容尋找對應的 dd 文字"""
    dt_tag = soup.find("dt", string=re.compile(dt_text))
    if dt_tag and isinstance(dt_tag, Tag):
        dd_tag = dt_tag.find_next_sibling("dd")
        if dd_tag and isinstance(dd_tag, Tag):
            return dd_tag.text.strip()
    return None


async def scrape_trail_details(trail_id: int) -> Optional[Dict[str, Any]]:
    """
    抓取並解析步道的完整資料。
    """
    url = f"https://hiking.biji.co/index.php?q=trail&act=detail&id={trail_id}"
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=False
        ) as client:
            response = await client.get(url, timeout=15)

            # 檢查是否被重新導向 (301, 302) 或頁面不存在 (404)
            if response.status_code in [301, 302, 404]:
                print(
                    f"Trail ID {trail_id} 不存在或已被重新導向 (Status: {response.status_code})。"
                )
                return None

            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # 優先從您提供的 hidden input 獲取標題，更穩定
            name = safe_find_text(soup, "input#route_data", "data-title")
            if not name:
                # 如果找不到，再使用 h1 標籤作為備用
                name = safe_find_text(soup, "h1.text-3xl.font-bold")

            description = safe_find_text(soup, "meta[name=description]", "content")
            gpx_url = safe_find_text(soup, "a.btn-gpx-download", "href")

            # 從您提供的 dl 結構中提取資料
            location = find_data_by_dt(soup, "所在縣市")
            trail_type = find_data_by_dt(soup, "步道類型")
            pavement = find_data_by_dt(soup, "路面狀況")
            distance_str = find_data_by_dt(soup, "里程")
            duration = find_data_by_dt(soup, "所需時間")
            altitude = find_data_by_dt(soup, "海拔高度")
            altitude_diff_str = find_data_by_dt(soup, "高度落差")
            difficulty = find_data_by_dt(soup, "難易度")

            distance = None
            if distance_str:
                match = re.search(r"[\d\.]+", distance_str)
                if match:
                    distance = float(match.group())

            altitude_difference = None
            if altitude_diff_str:
                match = re.search(r"[\d\.]+", altitude_diff_str)
                if match:
                    altitude_difference = int(match.group())

            details = {
                "name": name,
                "description": description,
                "location": location,
                "trail_type": trail_type,
                "pavement": pavement,
                "distance": distance,
                "duration": duration,
                "altitude": altitude,
                "altitude_difference": altitude_difference,
                "difficulty": difficulty,
                "gpx_url": f"https://hiking.biji.co{gpx_url}" if gpx_url else None,
            }
            return details

    except httpx.HTTPStatusError as e:
        print(
            f"抓取步道資料失敗 (HTTP Error): {e.response.status_code} for trail_id={trail_id}"
        )
        return None
    except Exception as e:
        print(f"抓取步道資料時發生預期外的錯誤: {e} for trail_id={trail_id}")
        return None


async def get_total_review_pages(trail_id: int) -> int:
    """
    透過解析步道主頁面，取得山友評論的總頁數。
    """
    url = f"https://hiking.biji.co/index.php?q=trail&act=detail&id={trail_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            total_page_span = soup.find("span", id="total_page")
            if total_page_span and total_page_span.text.strip().isdigit():
                return int(total_page_span.text.strip())
            else:
                return 0
    except httpx.HTTPStatusError as e:
        print(
            f"抓取總頁數失敗 (HTTP Error): {e.response.status_code} for trail_id={trail_id}"
        )
        return 0
    except Exception as e:
        print(f"抓取總頁數時發生預期外的錯誤: {e} for trail_id={trail_id}")
        return 0
