# main.py
from fastapi import FastAPI
from app.database import connect_to_mongo, close_mongo_connection, db_client

app = FastAPI(title="Hiking Weather Guide MVP")

# 設置連線事件
app.add_event_handler("startup", connect_to_mongo)
app.add_event_handler("shutdown", close_mongo_connection)


@app.get("/")
async def root():
    # 測試連線是否成功
    if db_client.db:
        return {"status": "MongoDB Connected", "service": "ready"}
    return {"status": "MongoDB Failed", "service": "error"}


# 預留 Day 2 的 API 端點
@app.post("/api/recommendation")
async def get_recommendation(trail_id: str, user_path_desc: str):
    return {"message": "Processing will start on Day 2"}


# 執行指令: uvicorn main:app --reload
# 但在 Cloud Run 上執行時會使用 gunicorn 或類似服務器，此處僅供本機測試
