# === 階段 1: 構建階段 - 安裝依賴 ===
# 使用 Python 3.11 Slim-buster 作為基礎映像，確保穩定與輕量
FROM python:3.12-slim as builder

# 設置工作目錄
WORKDIR /app

# 複製依賴文件
COPY pyproject.toml pyproject.toml
COPY uv.lock uv.lock

# 複製應用程式原始碼，以便 `uv sync` 可以找到本地套件
COPY main.py main.py
COPY app/ app/

# 安裝 uv
RUN pip install uv

# 安裝依賴
# --no-dev 排除開發依賴
RUN uv sync --locked --no-dev
# 複製其他可能用到的配置或腳本，例如：
# COPY config.ini config.ini


# === 階段 2: 運行階段 - 部署到 Cloud Run (極度輕量化) ===
# 再次使用 Python Slim 映像，但這次只複製運行時所需的內容
FROM python:3.12-slim

# 設置工作目錄
WORKDIR /app

# 【關鍵修正】uv 會在 /app/.venv 中建立虛擬環境，我們需要從那裡複製套件
# 複製已安裝的套件
COPY --from=builder /app/.venv/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 複製應用程式原始碼
COPY --from=builder /app /app

# 暴露服務端口
# Cloud Run 預設要求應用程式監聽 $PORT 環境變數，但這裡先設置一個常見的預設值
ENV PORT 8080
EXPOSE 8080


# 啟動服務命令
# 我們使用 gunicorn 搭配 uvicorn worker 來提高生產環境的效能和穩定性
# -b 0.0.0.0:$(PORT) 確保監聽所有網絡接口，且使用 Cloud Run 提供的 PORT 變數
# -w 4: 設置 4 個 worker (可依 CPU 核心數調整)
# -k uvicorn.workers.UvicornWorker: 使用 Uvicorn worker
# main:app: 指向您的 FastAPI 應用實例 (main.py 裡的 app = FastAPI())
# 使用 python -m gunicorn 的方式啟動，以避免符號連結問題
CMD ["python", "-m", "gunicorn", "main:app", "--bind", "0.0.0.0:8080", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker"]

# 替代 CMD (如果 gunicorn/uvicorn worker 設置太複雜，可以採用簡單的 uvicorn 啟動)
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
