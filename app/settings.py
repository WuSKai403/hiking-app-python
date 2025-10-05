# app/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

# 推薦使用 pydantic-settings 庫，如果您的 pydantic 版本需要單獨安裝
# uv pip install pydantic-settings


class Settings(BaseSettings):
    # 設置來源：會自動尋找專案根目錄下的 .env 檔案
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 核心服務密鑰
    GEMINI_API_KEY: str  # 必填，無預設值
    CWA_API_KEY: str  # 必填

    # 資料庫連線
    MONGO_URI: str
    DATABASE_NAME: str = "hiking_db"  # 可選，設定預設值

    # 應用程式設定
    APP_NAME: str = "Hiking Weather Guide MVP"
    APP_VERSION: str = "0.1.0"

    LOG_LEVEL: str = "DEBUG"  # 可選，設定預設值
    API_ENV: str = "development"  # 可選，設定預設值，可用於區分開發、測試、正式環境


settings = Settings()
