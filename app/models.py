# app/models.py

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
