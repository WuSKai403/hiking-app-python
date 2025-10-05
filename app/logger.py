import logging
import sys
import os

# 1. 從環境變數讀取日誌級別，預設為 INFO
log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)

# 2. 建立一個 logger
logger = logging.getLogger("hiking_guide_logger")
logger.setLevel(log_level)

# 3. 建立一個 handler，用於將日誌訊息輸出到標準輸出 (stdout)
# Cloud Run 會自動收集 stdout 和 stderr 的輸出
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(log_level)

# 4. 定義日誌格式
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# 5. 將 handler 加入到 logger 中
# 避免重複加入 handler
if not logger.handlers:
    logger.addHandler(handler)
