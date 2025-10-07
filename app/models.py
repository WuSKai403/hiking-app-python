# app/models.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# 接收使用者輸入的請求模型
class RecommendationRequest(BaseModel):
    """
    使用者提交的健行路徑資訊。
    """

    # 這是架構圖中路徑ID的輸入，用於爬蟲或資料庫查詢。
    trail_id: str = Field(..., description="健行路徑的唯一 ID (例如：健行筆記 ID)。")
    # 這是使用者輸入的簡要描述，提供 AI 判斷額外的即時情境。
    user_path_desc: str = Field(
        ...,
        description="使用者提供的路徑簡要描述或當下情境 (例如：下午出發、單人輕裝)。",
    )


# AI 輸出結果的結構化模型 (強調 JSON Schema)
class RecommendationResponse(BaseModel):
    """
    AI 核心輸出的結構化判斷結果。
    """

    safety_score: int = Field(
        ..., description="安全評分 (1: 極危險, 5: 非常安全)。", ge=1, le=5
    )
    recommendation: str = Field(
        ..., description="簡潔的結論 (例如：建議攜帶雨具, 今日不宜登頂)。"
    )
    reasoning: str = Field(..., description="AI 綜合當前天氣和近期評論判斷的詳細理由。")
    data_source: str = Field(
        ..., description="數據來源 (例如：'Cache', 'Gemini Real-time')"
    )


# 爬蟲或 CWA API 抓取的原始數據模型 (可選，用於內部傳遞)
# class WeatherData(BaseModel): ...
# class ReviewData(BaseModel): ...

# --- MongoDB Document Models ---


class ReviewModel(BaseModel):
    """
    代表單一評論的巢狀文檔模型。
    """

    user_id: str = Field(..., description="評論者的唯一 ID")
    username: str = Field(..., description="評論者的名稱")
    review_date: Optional[datetime] = Field(None, description="評論日期")
    content: str = Field(..., description="評論內容")

    def __hash__(self):
        # 讓 ReviewModel 可以被放入 set 中以進行快速比對
        return hash((self.user_id, self.review_date, self.content))

    def __eq__(self, other):
        # 定義兩個 ReviewModel 相等的條件
        if not isinstance(other, ReviewModel):
            return NotImplemented
        return (
            self.user_id == other.user_id
            and self.review_date == other.review_date
            and self.content == other.content
        )


class TrailDocument(BaseModel):
    """
    代表儲存在 MongoDB 中 'trails' 集合的文檔模型。
    """

    id: int = Field(..., alias="_id", description="健行筆記 ID，作為 MongoDB 的主鍵")
    name: Optional[str] = Field(None, description="步道名稱")
    description: Optional[str] = Field(None, description="步道描述")
    location: Optional[str] = Field(None, description="所在縣市")
    difficulty: Optional[str] = Field(None, description="難度")

    # 新增的詳細資訊欄位
    trail_type: Optional[str] = Field(None, description="步道類型 (例如：郊山步道)")
    distance: Optional[float] = Field(None, description="步道里程 (公里)")
    altitude: Optional[str] = Field(None, description="海拔高度 (公尺)")
    altitude_difference: Optional[int] = Field(None, description="高度落差 (公尺)")
    duration: Optional[str] = Field(None, description="預計所需時間")
    pavement: Optional[str] = Field(None, description="路面狀況")
    gpx_url: Optional[str] = Field(None, description="GPX 檔案的下載連結")

    last_scraped_at: datetime = Field(..., description="最後爬取時間")
    reviews: List[ReviewModel] = Field([], description="山友評論列表")
    is_valid: bool = Field(True, description="此步道 ID 是否有效 (爬取失敗則為 False)")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "_id": 108,
                "name": "硬漢嶺步道(觀音山)",
                "description": "昔稱「觀音古道」，隨著陡峭蜿蜒石階拾級而上...",
                "location": "新北市",
                "difficulty": "低",
                "last_scraped_at": "2025-10-06T12:00:00Z",
                "reviews": [
                    {"review_date": "2025-09-06T00:00:00Z", "content": "很棒的一條路線"}
                ],
            }
        }
