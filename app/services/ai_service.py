# app/services/ai_service.py

from google import genai
from google.genai import types
from app.settings import settings
from app.models import RecommendationRequest, RecommendationResponse
from app.logger import logger

# 初始化 Gemini 客戶端
# 它會自動從 settings.py (繼承自 .env 或環境變數) 載入 GEMINI_API_KEY
client = genai.Client(api_key=settings.GEMINI_API_KEY)


def build_prompt(
    request: RecommendationRequest, weather_data: str, review_data: str
) -> str:
    """
    將所有數據整合為一個結構化 Prompt 給 Gemini。
    """
    prompt = f"""
    你是台灣專業登山顧問 AI，請根據以下資訊，為初級登山者提供「健行路徑安全評分」與「建議」。
    請務必以 JSON 格式輸出結果，並遵循提供的 JSON Schema。

    使用者請求：
    - 路徑 ID: {request.trail_id}
    - 額外描述: {request.user_path_desc}

    即時氣象資料 (CWA API):
    ---
    {weather_data}
    ---

    近期路徑評論 (爬蟲結果):
    ---
    {review_data}
    ---

    綜合你的專業知識，請為路徑評定 1 到 5 的安全分數 (1 極危險, 5 非常安全)，並給予簡潔建議與理由。
    """
    return prompt


async def get_ai_recommendation(
    request: RecommendationRequest, weather_data: str, review_data: str
) -> RecommendationResponse:
    """
    呼叫 Gemini API 進行 AI 判斷並返回結構化結果。
    """

    system_instruction = "你是一個登山安全專家，你的任務是基於提供的數據，為初級登山者生成結構化 JSON 安全建議。"

    # 建立 Prompt
    prompt = build_prompt(request, weather_data, review_data)

    # 設置結構化輸出 (JSON Schema)
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=RecommendationResponse,
    )

    try:
        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash",  # 選擇快速且高效的 flash 模型
            contents=prompt,
            config=config,
        )

        # 當使用 response_schema 時，genai 函式庫會自動解析 JSON。
        # 結果會是一個 Pydantic 模型實例，而不是 JSON 字串。
        # 我們可以直接從 response 中提取它。
        # 注意：這裡的寫法是基於 google-genai v0.5+ 的行為
        if not response.candidates:
            raise ValueError("Gemini API did not return any candidates.")

        # 直接從回應中獲取 Pydantic 模型
        # 函式庫會將解析後的物件放在 function_call.args 中
        # 或是直接作為 part 本身 (取決於具體模型和版本)
        # 為了穩健起見，我們先檢查 part 的結構
        part = response.candidates[0].content.parts[0]

        # 假設 genai 將其解析為 RecommendationResponse 的實例並放在 function_call 中
        # 實際路徑可能需要根據 debug 調整，但這是最常見的模式
        # 為了簡化，我們先假設 genai 直接回傳了可驗證的 dict
        # 讓我們直接使用 response.text，但加上詳細的日誌
        logger.debug(f"Raw Gemini response text: {response.text}")
        result = RecommendationResponse.model_validate_json(response.text)

        result.data_source = "Gemini Real-time"
        logger.info(
            f"Successfully parsed AI Recommendation for trail_id: {request.trail_id}"
        )
        return result

    except Exception as e:
        # 加上更詳細的錯誤日誌，包含 response 內容
        logger.error(
            f"Gemini API call or parsing failed for trail_id: {request.trail_id}. Error: {e}",
            exc_info=True,
        )
        # 嘗試記錄下原始 response (如果有的話)
        if "response" in locals() and hasattr(response, "text"):
            logger.error(f"Raw response content on error: {response.text}")
        # 返回一個錯誤的預設值或拋出 HTTP 異常
        return RecommendationResponse(
            safety_score=1,
            recommendation="AI 服務異常！",
            reasoning=f"AI 服務連線失敗或回應錯誤。 ({e})",
            data_source="Service Error",
        )
